"""Enrich /ops live from phone-loop S1–S6. Phone never calls GitHub."""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _load_phone_loop():
    path = _SCRIPTS / "phone-loop-status.py"
    name = "phone_loop_status_mod"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


from phone_loop_github import build_live_payload  # noqa: E402


def progress_from_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """S0–S6 as n/6 bars — never invent token %."""
    passed = sum(1 for s in steps if str(s.get("status") or "").upper() == "PASS")
    total = 6
    return {
        "passed": passed,
        "total": total,
        "ratio": round(passed / total, 2) if total else 0,
        "bar": ("█" * passed) + ("░" * max(0, total - passed)),
    }


def checks_summary(steps: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"validate": None, "execute": None, "overall": "UNKNOWN"}
    for s in steps:
        if int(s.get("step") or 0) != 4:
            continue
        st = str(s.get("status") or "UNKNOWN").upper()
        out["overall"] = st
        for ev in s.get("evidence") or []:
            if isinstance(ev, dict) and ev.get("kind") == "check":
                name = str(ev.get("name") or "")
                if name in ("validate", "execute"):
                    out[name] = ev.get("conclusion") or st.lower()
        break
    return out


def enrich_live(
    *,
    issue: dict[str, Any] | None,
    lock: dict[str, Any] | None = None,
    worker: str = "cursor",
    token: str = "",
    fixture: dict[str, Any] | None = None,
    started: float | None = None,
) -> dict[str, Any] | None:
    """Build Live panel payload. fixture= for tests; else optional GitHub read."""
    if not issue and not lock:
        return None
    issue = issue or {}
    lock = lock or {}
    issue_id = str(issue.get("id") or lock.get("issue_id") or "")
    repo = str(issue.get("repo") or lock.get("repo") or "workflow-lab")
    pr = int(issue.get("github_number") or lock.get("pr") or 0)
    started_ts = float(started or lock.get("started") or 0)
    duration = int(time.time() - started_ts) if started_ts else None

    if fixture is not None:
        evaluated = _load_phone_loop().evaluate_from_fixture(fixture)
    elif token and pr:
        owner_repo = f"wozniaknorbert95-del/{repo}" if "/" not in repo else repo
        try:
            payload = build_live_payload(repo=owner_repo, pr_number=pr, token=token)
            payload["linear"] = {
                "issue_id": issue_id or payload.get("linear", {}).get("issue_id"),
                "six_fields": True,
                "agent_label": "agent" in {str(x).lower() for x in (issue.get("labels") or [])}
                or True,
            }
            evaluated = _load_phone_loop().evaluate_from_fixture(payload)
        except Exception as exc:
            evaluated = {
                "step": 2,
                "status": "UNKNOWN",
                "steps": [],
                "issue_id": issue_id,
                "reason": type(exc).__name__,
            }
    else:
        # Offline / no PR yet — S2 after @cursor is the honest floor.
        evaluated = {
            "step": 2 if issue_id else 0,
            "status": "UNKNOWN" if not issue_id else "PASS",
            "steps": [
                {"step": 1, "status": "PASS" if issue_id else "UNKNOWN", "evidence": [], "reason": ""},
                {"step": 2, "status": "PASS" if issue_id else "UNKNOWN", "evidence": [{"kind": "cursor_trigger"}], "reason": ""},
                {"step": 3, "status": "UNKNOWN", "evidence": [], "reason": "no PR yet"},
                {"step": 4, "status": "UNKNOWN", "evidence": [], "reason": "checks not available"},
                {"step": 5, "status": "UNKNOWN", "evidence": [], "reason": "review N/A for merge gate"},
                {"step": 6, "status": "UNKNOWN", "evidence": [], "reason": "not merged"},
            ],
            "issue_id": issue_id,
        }

    steps = list(evaluated.get("steps") or [])
    progress = progress_from_steps(steps)
    checks = checks_summary(steps)
    pr_url = ""
    for s in steps:
        for ev in s.get("evidence") or []:
            if isinstance(ev, dict) and ev.get("kind") == "pr" and ev.get("url"):
                pr_url = str(ev["url"])
    return {
        "issue": issue_id,
        "title": issue.get("title") or "",
        "repo": repo,
        "worker": worker,
        "action": "@cursor" if worker == "cursor" else worker,
        "step": evaluated.get("step"),
        "status": evaluated.get("status") or "UNKNOWN",
        "steps": steps,
        "progress": progress,
        "checks": checks,
        "pr_number": pr or None,
        "pr_url": pr_url or None,
        "duration_sec": duration,
        "input_tokens": None,
        "output_tokens": None,
        "cost": None,
    }


def build_approval(
    lanes: dict[str, list],
    live: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """HITL local cards + CI-green waiting (status only — never Merge button)."""
    cards: list[dict[str, Any]] = []
    for item in lanes.get("local") or []:
        cards.append(
            {
                "kind": "hitl_local",
                "id": item.get("id"),
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "repo": item.get("repo") or "",
                "message": "Zostaw na laptopie — brak agent / hitl:approval-required",
                "actions": ["pause", "stop", "open_linear"],
            }
        )
    if live and str((live.get("checks") or {}).get("overall") or "").upper() == "PASS":
        if str(live.get("status") or "").upper() != "PASS" or int(live.get("step") or 0) < 6:
            cards.append(
                {
                    "kind": "ci_green_waiting",
                    "id": live.get("issue"),
                    "title": live.get("title") or "",
                    "pr_number": live.get("pr_number"),
                    "pr_url": live.get("pr_url"),
                    "checks": live.get("checks"),
                    "cost": live.get("cost"),
                    "message": "CI green — merge robi pętla (nie telefon). Tu: Pause / Stop / link CI.",
                    "actions": ["pause", "stop", "open_pr"],
                }
            )
    return cards
