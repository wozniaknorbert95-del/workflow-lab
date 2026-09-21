"""S0 Linear → S2 @cursor → S3 PR → S4 checks → S6 merge. No S-deploy."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from . import policy
from .github import GitHubOps
from .router import LANE_AUTOPILOT, LANE_LOCAL, classify_issue, split_lanes
from .status_cache import build_status, write_status
from .telemetry import OPS_MAX_CONCURRENT, append_event, over_daily_cap, today_stats

LOCK_PATH = Path(os.environ.get("HERMES_OPS_LOCK", "data/hermes-ops-lock.json"))
CMD_PATH = Path(os.environ.get("HERMES_OPS_CMD", "data/ops-cmd.json"))
TTL_MIN = int(os.environ.get("OPS_TTL_MIN", "15"))


class ConcurrentError(RuntimeError):
    def __init__(self, msg: str = "busy") -> None:
        super().__init__(msg)
        self.code = 409


class Engine:
    def __init__(
        self,
        github: GitHubOps | None = None,
        mode: str = "MANUAL",
        lock_path: Path | None = None,
        ledger: Path | None = None,
    ) -> None:
        self.github = github or GitHubOps()
        self.mode = mode
        self.engine_state = "PAUSED"
        self.lock_path = lock_path or LOCK_PATH
        self.ledger = ledger
        self.live: dict[str, Any] | None = None

    def _lock(self) -> dict[str, Any]:
        if not self.lock_path.is_file():
            return {}
        try:
            return json.loads(self.lock_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_lock(self, data: dict[str, Any]) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.lock_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.lock_path)

    def _clear_lock(self) -> None:
        if self.lock_path.exists():
            self.lock_path.unlink()

    def busy(self) -> bool:
        lock = self._lock()
        if not lock:
            return False
        started = float(lock.get("started") or 0)
        if started and (time.time() - started) > TTL_MIN * 60:
            self.engine_state = "PAUSED"
            self._clear_lock()
            return False
        return True

    def pause(self) -> dict[str, Any]:
        self.engine_state = "PAUSED"
        append_event({"kind": "paused"}, self.ledger)
        return {"ok": True, "engine": self.engine_state}

    def stop(self) -> dict[str, Any]:
        self.engine_state = "STOPPED"
        self._clear_lock()
        append_event({"kind": "stopped"}, self.ledger)
        return {"ok": True, "engine": self.engine_state}

    def run_next(self, issue: dict[str, Any]) -> dict[str, Any]:
        if policy.allow_deploy("run_next")[0]:
            return {"ok": False, "code": 403, "error": policy.DEPLOY_DENIED}
        if "deploy" in json.dumps(issue).lower():
            return {"ok": False, "code": 403, "error": policy.DEPLOY_DENIED}
        lane = classify_issue(issue, mode=self.mode)
        if lane == LANE_LOCAL:
            return {"ok": False, "code": 403, "error": policy.LOCAL_ONLY}
        ok, code, reason = policy.allow_cursor_comment(issue, mode=self.mode)
        if not ok:
            return {"ok": False, "code": code, "error": reason}
        if self.busy() or OPS_MAX_CONCURRENT != 1:
            if self.busy():
                current = str(self._lock().get("issue_id") or "")
                wanted = str(issue.get("id") or "")
                if current and wanted and current == wanted:
                    return {"ok": False, "code": 409, "error": "idempotent"}
                return {"ok": False, "code": 409, "error": "concurrent"}
        if over_daily_cap(self.ledger):
            return {"ok": False, "code": 429, "error": "daily_cap"}
        issue_id = str(issue.get("id") or "")
        self._write_lock({"issue_id": issue_id, "started": time.time(), "repo": issue.get("repo")})
        self.engine_state = "RUNNING"
        self.live = {"step": 2, "issue": issue_id, "action": "@cursor"}
        repo = str(issue.get("repo") or "workflow-lab")
        number = int(issue.get("github_number") or 0)
        commented = {"ok": True, "skipped": True}
        if number:
            commented = self.github.comment_cursor(repo, number)
        append_event(
            {"kind": "run_next", "issue": issue_id, "repo": repo, "result": "started"},
            self.ledger,
        )
        return {"ok": True, "queued": issue_id, "github": commented}

    def maybe_merge(self, repo: str, pull_number: int, checks_green: bool, issue: dict[str, Any] | None = None) -> dict[str, Any]:
        if not checks_green:
            return {"ok": False, "code": 409, "error": "ci_not_green"}
        result = self.github.merge_pull(repo, pull_number, checks_green, issue)
        kind = "merged" if result.get("ok") else "failed"
        append_event({"kind": kind, "repo": repo, "pr": pull_number}, self.ledger)
        if result.get("ok"):
            self._clear_lock()
            self.live = None
            if self.mode != "AUTOPILOT":
                self.engine_state = "PAUSED"
        return result

    def tick(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        lanes = split_lanes(issues, mode=self.mode)
        if self.engine_state in ("PAUSED", "STOPPED"):
            return {"ok": True, "skipped": self.engine_state, "lanes": lanes}
        if self.mode != "AUTOPILOT":
            return {"ok": True, "skipped": "MANUAL", "lanes": lanes}
        if self.busy():
            return {"ok": True, "skipped": "busy", "lanes": lanes}
        queue = lanes[LANE_AUTOPILOT]
        if not queue:
            return {"ok": True, "skipped": "empty", "lanes": lanes}
        picked = None
        for raw in issues:
            if str(raw.get("id") or raw.get("identifier")) == str(queue[0]["id"]):
                picked = raw
                break
        if not picked:
            picked = {"id": queue[0]["id"], "labels": ["agent"], "repo": queue[0].get("repo") or "workflow-lab"}
        return self.run_next(picked)

    def status_payload(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        lanes = split_lanes(issues, mode=self.mode)
        engine = self.engine_state or "UNKNOWN"
        return build_status(
            mode=self.mode,
            engine=engine,
            lanes=lanes,
            live=self.live,
            reason="vps_timer",
            ledger=self.ledger,
        )


def consume_cmd(path: Path | None = None) -> dict[str, Any] | None:
    target = path or CMD_PATH
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None
    target.unlink(missing_ok=True)
    return data if isinstance(data, dict) else None
