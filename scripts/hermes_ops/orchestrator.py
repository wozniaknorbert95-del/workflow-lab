"""S0 Linear → S2 @cursor → S3 PR → S4 checks → S6 merge. No S-deploy."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from . import policy
from .github import GitHubOps
from .live_enrich import build_approval, enrich_live
from .router import (
    LANE_AUTOPILOT,
    LANE_LOCAL,
    LANE_MANUAL,
    active_agents_from,
    attach_lane_progress,
    classify_issue,
    split_lanes,
)
from .status_cache import build_status
from .telemetry import OPS_MAX_CONCURRENT, append_event, over_daily_cap, run_all_enabled

LOCK_PATH = Path(os.environ.get("HERMES_OPS_LOCK", "data/hermes-ops-lock.json"))
CMD_PATH = Path(os.environ.get("HERMES_OPS_CMD", "data/ops-cmd.json"))
STATE_PATH = Path(os.environ.get("HERMES_OPS_STATE", "data/hermes-ops-state.json"))
TTL_MIN = int(os.environ.get("OPS_TTL_MIN", "15"))
READ_TOKEN = os.environ.get("GITHUB_ENGINEER_TOKEN") or os.environ.get("GITHUB_OPS_WRITE", "")


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
        state_path: Path | None = None,
        github_read_token: str | None = None,
    ) -> None:
        self.github = github or GitHubOps()
        self.mode = mode if mode in policy.ALLOWED_MODES else "MANUAL"
        self.engine_state = "PAUSED"
        self.lock_path = lock_path or LOCK_PATH
        self.state_path = state_path or Path(os.environ.get("HERMES_OPS_STATE", str(STATE_PATH)))
        self.ledger = ledger
        self.live: dict[str, Any] | None = None
        self.github_read_token = (github_read_token if github_read_token is not None else READ_TOKEN).strip()
        self.worker = policy.default_worker()

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
        # Pause/Stop means the slot is free — leftover lock must not refuse Start.
        if self.engine_state in ("PAUSED", "STOPPED"):
            return False
        lock = self._lock()
        if not lock:
            return False
        started = float(lock.get("started") or 0)
        if started and (time.time() - started) > TTL_MIN * 60:
            self.engine_state = "PAUSED"
            self._clear_lock()
            append_event(
                {"kind": "stale_lock", "result": "cleared", "agent": self.worker},
                self.ledger,
            )
            self.save_state()
            return False
        return True

    def load_state(self) -> None:
        if not self.state_path.is_file():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return
        mode = str(data.get("mode") or "").upper()
        if mode in policy.ALLOWED_MODES:
            self.mode = mode
        engine = str(data.get("engine") or "").upper()
        if engine in ("PAUSED", "STOPPED", "RUNNING", "UNKNOWN"):
            self.engine_state = engine
        live = data.get("live")
        if isinstance(live, dict):
            self.live = live

    def save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": self.mode,
            "engine": self.engine_state,
            "live": self.live,
        }
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    def pick_next(self, issues: list[dict[str, Any]], issue_id: str = "") -> dict[str, Any] | None:
        wanted = str(issue_id or "")
        if wanted:
            for issue in issues:
                if str(issue.get("id") or issue.get("identifier") or "") == wanted:
                    return issue
            return None
        lanes = split_lanes(issues, mode=self.mode if self.mode != "SUPERVISED" else "AUTOPILOT")
        if self.mode == "MANUAL":
            queue = lanes[LANE_MANUAL]
        else:
            queue = lanes[LANE_AUTOPILOT]
        if not queue:
            return None
        target = str(queue[0].get("id") or "")
        for issue in issues:
            if str(issue.get("id") or issue.get("identifier") or "") == target:
                return issue
        return None

    def pause(self) -> dict[str, Any]:
        self.engine_state = "PAUSED"
        self._clear_lock()
        append_event({"kind": "paused", "result": "paused", "agent": self.worker}, self.ledger)
        self.save_state()
        return {"ok": True, "engine": self.engine_state}

    def stop(self) -> dict[str, Any]:
        self.engine_state = "STOPPED"
        self._clear_lock()
        append_event({"kind": "stopped", "result": "stopped", "agent": self.worker}, self.ledger)
        self.save_state()
        return {"ok": True, "engine": self.engine_state}

    def take_over(self, issue: dict[str, Any] | None = None) -> dict[str, Any]:
        """Pause + mark live issue as local (zero @cursor)."""
        self.pause()
        issue_id = str((issue or {}).get("id") or (self.live or {}).get("issue") or self._lock().get("issue_id") or "")
        self._clear_lock()
        self.live = {
            "issue": issue_id,
            "action": "take_over",
            "worker": self.worker,
            "status": "PAUSED",
            "step": None,
            "message": "Take over — zrób na laptopie. Zero @cursor.",
        }
        append_event(
            {
                "kind": "take_over",
                "issue": issue_id,
                "agent": self.worker,
                "result": "local",
            },
            self.ledger,
        )
        self.save_state()
        return {"ok": True, "engine": "PAUSED", "issue": issue_id, "lane": LANE_LOCAL}

    def set_mode(self, mode: str) -> dict[str, Any]:
        mode = str(mode or "").upper()
        if mode not in policy.ALLOWED_MODES:
            return {"ok": False, "code": 400, "error": "bad_mode"}
        self.mode = mode
        if mode == "MANUAL" and self.engine_state == "RUNNING":
            self.engine_state = "PAUSED"
        if mode in ("AUTOPILOT", "SUPERVISED") and self.engine_state == "PAUSED":
            pass  # Dowódca taps Start / Run next to go RUNNING
        self.save_state()
        append_event({"kind": "mode", "result": mode, "agent": self.worker}, self.ledger)
        return {"ok": True, "mode": self.mode}

    def run_next(self, issue: dict[str, Any], *, fixture: dict[str, Any] | None = None) -> dict[str, Any]:
        if policy.allow_deploy("run_next")[0]:
            return {"ok": False, "code": 403, "error": policy.DEPLOY_DENIED}
        if "deploy" in json.dumps(issue).lower():
            return {"ok": False, "code": 403, "error": policy.DEPLOY_DENIED}
        route_mode = "AUTOPILOT" if self.mode == "SUPERVISED" else self.mode
        lane = classify_issue(issue, mode=route_mode)
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
        started = time.time()
        repo = str(issue.get("repo") or "workflow-lab")
        # Pending lock only — RUNNING is illegal until @cursor comment is 2xx.
        self._write_lock(
            {
                "issue_id": issue_id,
                "started": started,
                "repo": repo,
                "pr": issue.get("github_number"),
                "wake_state": "pending",
            }
        )
        # E4: Linear issues usually lack github_number — create/find GH issue + @cursor.
        trigger = self.github.ensure_cursor_trigger(repo, issue)
        commented_ok = bool(trigger.get("ok") and trigger.get("commented") is True)
        number = int(trigger.get("issue_number") or 0)
        if not commented_ok or number <= 0:
            self.pause()
            return {
                "ok": False,
                "code": int(trigger.get("code") or 401),
                "error": str(trigger.get("error") or "cursor_wake_failed"),
            }
        # Prefer the repo that actually received @cursor (may fall back to workflow-lab).
        used_repo = str(trigger.get("repo") or repo)
        # Newly created tracking issues are NOT PRs — do not feed them into PR enrich.
        created_issue = bool(trigger.get("created"))
        existing_pr = int(issue.get("github_number") or 0) if not created_issue else 0
        self.engine_state = "RUNNING"
        # Lock: github_issue = tracking issue; pr = real PR only (0 until agent opens one).
        self._write_lock(
            {
                "issue_id": issue_id,
                "started": started,
                "repo": used_repo,
                "pr": existing_pr or None,
                "github_issue": number,
                "cursor_comment_url": trigger.get("comment_url") or "",
                "wake_state": str(trigger.get("wake_state") or "commented"),
                "cursor_triggered": True,
            }
        )
        commented = {
            "ok": True,
            "issue_number": number,
            "created": trigger.get("created"),
            "repo": used_repo,
            "comment_url": trigger.get("comment_url") or "",
            "wake_state": trigger.get("wake_state"),
        }
        enrich_issue = {**issue, "repo": used_repo}
        if existing_pr > 0:
            enrich_issue["github_number"] = existing_pr
        else:
            enrich_issue.pop("github_number", None)
        self.live = enrich_live(
            issue=enrich_issue,
            lock=self._lock(),
            worker=self.worker,
            token=self.github_read_token,
            fixture=fixture,
            started=started,
            cursor_meta=trigger,
        )
        append_event(
            {
                "kind": "run_next",
                "issue": issue_id,
                "agent": self.worker,
                "model": None,
                "repo": used_repo,
                "pr": existing_pr or None,
                "github_issue": number or None,
                "result": "started",
                "input_tokens": None,
                "output_tokens": None,
                "cost": None,
                "duration": None,
                "tests": None,
                "retries": 0,
            },
            self.ledger,
        )
        self.save_state()
        return {"ok": True, "queued": issue_id, "github": commented, "cursor": trigger}

    def run_all(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        ok, code, reason = policy.allow_run_all(run_all_enabled())
        if not ok:
            return {"ok": False, "code": code, "error": reason}
        if over_daily_cap(self.ledger):
            return {"ok": False, "code": 429, "error": "daily_cap"}
        route_mode = "AUTOPILOT" if self.mode in ("AUTOPILOT", "SUPERVISED") else "MANUAL"
        lanes = split_lanes(issues, mode=route_mode)
        queue = lanes[LANE_AUTOPILOT] if route_mode == "AUTOPILOT" else lanes[LANE_MANUAL]
        if not queue:
            return {"ok": False, "code": 404, "error": "empty_queue"}
        # Still one concurrent — queue first only; rest wait next ticks.
        picked = self.pick_next(issues, str(queue[0].get("id") or ""))
        if not picked:
            return {"ok": False, "code": 404, "error": "empty_queue"}
        result = self.run_next(picked)
        result["run_all_queued"] = len(queue)
        return result

    def maybe_merge(
        self, repo: str, pull_number: int, checks_green: bool, issue: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if not checks_green:
            return {"ok": False, "code": 409, "error": "ci_not_green"}
        result = self.github.merge_pull(repo, pull_number, checks_green, issue)
        kind = "merged" if result.get("ok") else "failed"
        append_event(
            {
                "kind": kind,
                "repo": repo,
                "pr": pull_number,
                "issue": (issue or {}).get("id"),
                "agent": self.worker,
                "result": kind,
                "input_tokens": None,
                "output_tokens": None,
                "cost": None,
            },
            self.ledger,
        )
        if result.get("ok"):
            self._clear_lock()
            self.live = None
            if self.mode == "MANUAL":
                self.engine_state = "PAUSED"
            self.save_state()
        return result

    def tick(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        route_mode = "AUTOPILOT" if self.mode in ("AUTOPILOT", "SUPERVISED") else self.mode
        lanes = split_lanes(issues, mode=route_mode)
        if self.engine_state in ("PAUSED", "STOPPED"):
            return {"ok": True, "skipped": self.engine_state, "lanes": lanes}
        if self.mode == "MANUAL":
            return {"ok": True, "skipped": "MANUAL", "lanes": lanes}
        if self.busy():
            return {"ok": True, "skipped": "busy", "lanes": lanes}
        # busy() on TTL expiry sets PAUSED and returns False (slot free for phone Start).
        # Re-check: Autopilot must NOT run_next again — that re-woke QUI-88 every 15 min
        # and burned OPS_MAX_RUNS_PER_DAY (2026-09-23: 32× run_next, 0 merges).
        if self.engine_state in ("PAUSED", "STOPPED"):
            return {"ok": True, "skipped": "stale_lock", "lanes": lanes}
        # SUPERVISED: never auto-start HITL (already local). Autopilot queue only.
        queue = lanes[LANE_AUTOPILOT]
        if not queue:
            return {"ok": True, "skipped": "empty", "lanes": lanes}
        picked = None
        for raw in issues:
            if str(raw.get("id") or raw.get("identifier")) == str(queue[0]["id"]):
                picked = raw
                break
        if not picked:
            picked = {
                "id": queue[0]["id"],
                "labels": ["agent"],
                "repo": queue[0].get("repo") or "workflow-lab",
            }
        return self.run_next(picked)

    def refresh_live(self, issues: list[dict[str, Any]], *, fixture: dict[str, Any] | None = None) -> None:
        lock = self._lock()
        issue_id = str(lock.get("issue_id") or (self.live or {}).get("issue") or "")
        if not issue_id:
            return
        match = next(
            (i for i in issues if str(i.get("id") or i.get("identifier") or "") == issue_id),
            {"id": issue_id, "repo": lock.get("repo"), "github_number": lock.get("pr") or 0},
        )
        # Keep lock.repo (may differ from Linear target after create fallback).
        if lock.get("repo"):
            match = {**match, "repo": lock.get("repo")}
        if lock.get("pr"):
            match = {**match, "github_number": lock.get("pr")}
        elif "github_number" in match and not lock.get("pr"):
            match = {**match}
            match.pop("github_number", None)
        self.live = enrich_live(
            issue=match,
            lock=lock,
            worker=self.worker,
            token=self.github_read_token,
            fixture=fixture,
            started=float(lock.get("started") or 0) or None,
            cursor_meta={"ok": True, "issue_number": lock.get("github_issue"), "repo": lock.get("repo")}
            if lock.get("cursor_triggered")
            else None,
        )

    def status_payload(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        route_mode = "AUTOPILOT" if self.mode == "SUPERVISED" else self.mode
        lanes = split_lanes(issues, mode=route_mode if self.mode != "MANUAL" else "MANUAL")
        if self.mode == "MANUAL":
            lanes = split_lanes(issues, mode="MANUAL")
        elif self.mode == "SUPERVISED":
            lanes = split_lanes(issues, mode="AUTOPILOT")
        engine = self.engine_state or "UNKNOWN"
        next_issue = None
        if self.mode == "MANUAL" and lanes.get(LANE_MANUAL):
            next_issue = lanes[LANE_MANUAL][0]
        elif lanes.get(LANE_AUTOPILOT):
            next_issue = lanes[LANE_AUTOPILOT][0]
        approval = build_approval(lanes, self.live)
        lanes = attach_lane_progress(lanes, self.live)
        agents = active_agents_from(self.live, self._lock(), self.worker)
        payload = build_status(
            mode=self.mode,
            engine=engine,
            lanes=lanes,
            live=self.live,
            reason="vps_timer",
            ledger=self.ledger,
            next_issue=next_issue,
            approval=approval,
            worker=self.worker,
            run_all=run_all_enabled(),
            active_agents=agents,
        )
        # Waiting = HITL/local queue size (operator signal), not only ledger.
        today = dict(payload.get("today") or {})
        today["waiting"] = max(int(today.get("waiting") or 0), len(lanes.get(LANE_LOCAL) or []))
        payload["today"] = today
        return payload


def consume_cmd(path: Path | None = None) -> dict[str, Any] | None:
    target = path or CMD_PATH
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    target.unlink(missing_ok=True)
    return data if isinstance(data, dict) else None
