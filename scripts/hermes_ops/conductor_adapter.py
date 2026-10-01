"""Nous → ops-status adapter. Tick copies fields; never starts a Cloud session.

Python here is a status bridge: read Nous JSON, sanitize, merge into live.
The conductor (Nous) is the only process allowed to talk to Cursor Cloud.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

STATUS_PATH = Path(
    os.environ.get("HERMES_CONDUCTOR_STATUS", "data/hermes-conductor-live.json")
)
HANDOFF_PATH = Path(
    os.environ.get("HERMES_CONDUCTOR_HANDOFF", "data/hermes-conductor-handoff.json")
)
WORK_MODES = ("buduj", "testuj", "ulepszaj")
DEFAULT_TTL_SEC = 900
_URL_DENY = ("token=", "access_token", "authorization", "@", "api_key", "apikey", "secret=")


def sanitize_work_mode(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in WORK_MODES else "buduj"


def https_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 500 or " " in text:
        return ""
    low = text.lower()
    if not low.startswith("https://"):
        return ""
    if any(bad in low for bad in _URL_DENY):
        return ""
    return text


def _verdict(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text if text in ("PASS", "FAIL", "UNKNOWN") else "UNKNOWN"


def sanitize_tests(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw[:40]:
        if not isinstance(item, dict):
            continue
        cmd = str(item.get("cmd") or item.get("command") or "")[:200]
        excerpt = str(item.get("excerpt") or item.get("output") or "")[:400]
        out.append(
            {
                "cmd": cmd,
                "excerpt": excerpt,
                "verdict": _verdict(item.get("verdict") or item.get("status")),
            }
        )
    return out


def sanitize_conductor(raw: Any, *, work_mode: str = "buduj") -> dict[str, Any]:
    blob = raw if isinstance(raw, dict) else {}
    followups = blob.get("followups")
    try:
        n = int(followups) if followups is not None else 0
    except (TypeError, ValueError):
        n = 0
    if n < 0:
        n = 0
    mode = sanitize_work_mode(blob.get("mode") or work_mode)
    return {
        "role": str(blob.get("role") or "nous")[:40],
        "model": str(blob.get("model") or "")[:80],
        "followups": n,
        "mode": mode,
        "report_pl": str(blob.get("report_pl") or "")[:800],
    }


def load_conductor_status(path: Path | None = None) -> dict[str, Any] | None:
    target = path or STATUS_PATH
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def refuse_of(blob: dict[str, Any] | None, issue_id: str = "") -> str:
    if not isinstance(blob, dict):
        return ""
    why = str(blob.get("refuse") or blob.get("error") or "").strip()
    if not why:
        return ""
    blob_issue = str(blob.get("issue") or blob.get("issue_id") or "").strip()
    wanted = str(issue_id or "").strip()
    if not wanted:
        return ""
    if blob_issue and blob_issue != wanted:
        return ""
    return why[:80]


def write_handoff(
    issue: dict[str, Any],
    *,
    work_mode: str = "buduj",
    cmd_id: str = "",
    path: Path | None = None,
) -> Path:
    target = path or HANDOFF_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "issue_id": str(issue.get("id") or issue.get("identifier") or ""),
        "title": str(issue.get("title") or "")[:200],
        "repo": str(issue.get("repo") or "workflow-lab"),
        "labels": list(issue.get("labels") or []),
        "work_mode": sanitize_work_mode(work_mode),
        "cmd_id": str(cmd_id or ""),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)
    return target


def merge_conductor_into_live(
    live: dict[str, Any] | None,
    blob: dict[str, Any] | None,
    *,
    work_mode: str = "buduj",
) -> dict[str, Any] | None:
    """Copy Nous fields into live. Empty blob still marks action=conduct."""
    if not isinstance(live, dict):
        return live
    out = dict(live)
    out["action"] = "conduct"
    src = blob if isinstance(blob, dict) else {}
    agent_src = src.get("agent") if isinstance(src.get("agent"), dict) else {}
    existing = out.get("agent") if isinstance(out.get("agent"), dict) else {}
    run_url = https_url(agent_src.get("run_url") or agent_src.get("url") or existing.get("run_url"))
    run_id = str(agent_src.get("run_id") or existing.get("run_id") or "")[:80]
    model = str(agent_src.get("model") or existing.get("model") or "")[:80]
    out["agent"] = {
        "provider": str(agent_src.get("provider") or existing.get("provider") or ("cursor-cloud" if run_url else "")),
        "run_url": run_url,
        "model": model,
        "run_id": run_id,
    }
    tests = sanitize_tests(src.get("tests"))
    if tests:
        out["tests"] = tests
    elif "tests" not in out:
        out["tests"] = []
    cond_src = src.get("conductor") if isinstance(src.get("conductor"), dict) else src
    out["conductor"] = sanitize_conductor(cond_src, work_mode=work_mode)
    if run_url:
        steps = list(out.get("steps") or [])
        for step in steps:
            if not isinstance(step, dict) or int(step.get("step") or 0) != 2:
                continue
            step["status"] = "PASS"
            step["reason"] = ""
            step["evidence"] = [
                {"kind": "cursor_cloud_api", "run_url": run_url, "run_id": run_id or None}
            ]
        if steps:
            out["steps"] = steps
    return out


def ttl_sec() -> int:
    try:
        n = int(os.environ.get("OPS_CONDUCTOR_TTL_SEC", str(DEFAULT_TTL_SEC)))
    except (TypeError, ValueError):
        n = DEFAULT_TTL_SEC
    return n if n > 0 else DEFAULT_TTL_SEC


def timeout_reason(
    *,
    engine_state: str,
    lock: dict[str, Any] | None,
    live: dict[str, Any] | None,
    now: float | None = None,
) -> str:
    """Fail-closed: RUNNING slot without https run_url past TTL → conductor_timeout."""
    if str(engine_state or "").upper() != "RUNNING":
        return ""
    lock = lock if isinstance(lock, dict) else {}
    live = live if isinstance(live, dict) else {}
    agent = live.get("agent") if isinstance(live.get("agent"), dict) else {}
    if https_url(agent.get("run_url")):
        return ""
    started = float(lock.get("started") or 0)
    if not started:
        return ""
    age = (time.time() if now is None else float(now)) - started
    if age > ttl_sec():
        return "conductor_timeout"
    return ""
