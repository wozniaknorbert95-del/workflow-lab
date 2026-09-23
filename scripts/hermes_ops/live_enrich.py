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
    cursor_meta: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build Live panel payload. fixture= for tests; else optional GitHub read."""
    if not issue and not lock:
        return None
    issue = issue or {}
    lock = lock or {}
    issue_id = str(issue.get("id") or lock.get("issue_id") or "")
    # Prefer lock.repo (equals Linear target; D-NO-DSAAS-FALLBACK).
    repo = str(lock.get("repo") or issue.get("repo") or "workflow-lab")
    # Real PR only (lock.pr); never treat tracking github_issue as a PR.
    pr = int(issue.get("github_number") or lock.get("pr") or 0)
    github_issue = int(lock.get("github_issue") or 0)
    if cursor_meta and cursor_meta.get("issue_number") and not github_issue:
        github_issue = int(cursor_meta.get("issue_number") or 0)
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
            # Carry proof fields from GitHub read (E5).
            evaluated["_github"] = payload.get("github") or {}
            evaluated["_checks_raw"] = payload.get("checks") or {}
        except Exception as exc:
            evaluated = {
                "step": 2,
                "status": "UNKNOWN",
                "steps": [],
                "issue_id": issue_id,
                "reason": type(exc).__name__,
            }
    else:
        # Offline / tracking issue only — S2 after a real @cursor comment (2xx).
        wake_state = str((cursor_meta or {}).get("wake_state") or lock.get("wake_state") or "")
        commented = bool((cursor_meta or {}).get("commented") is True) or wake_state in (
            "commented",
            "already",
        )
        cursor_ok = commented and bool(github_issue or (cursor_meta or {}).get("issue_number"))
        evaluated = {
            "step": 2 if issue_id else 0,
            "status": "UNKNOWN" if not issue_id else "PASS",
            "steps": [
                {"step": 1, "status": "PASS" if issue_id else "UNKNOWN", "evidence": [{"kind": "linear_issue", "id": issue_id}], "reason": ""},
                {
                    "step": 2,
                    "status": "PASS" if cursor_ok else "UNKNOWN",
                    "evidence": [{"kind": "cursor_trigger", "github_issue": github_issue or None, "repo": repo}],
                    "reason": "",
                },
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
    gh = evaluated.get("_github") if isinstance(evaluated.get("_github"), dict) else {}
    pr_url = str(gh.get("pr_url") or "")
    ci_url = str(gh.get("ci_url") or "")
    agent = gh.get("agent") if isinstance(gh.get("agent"), dict) else {}
    diff = gh.get("diff") if isinstance(gh.get("diff"), dict) else None
    recent = gh.get("recent") if isinstance(gh.get("recent"), list) else []
    # Only treat github_number as PR when PR URL exists (else it's the tracking issue).
    # Fixtures keep legacy pr_number for unit tests.
    if fixture is not None:
        pr_number = pr or None
        for s in steps:
            for ev in s.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("kind") == "pr" and ev.get("url") and not pr_url:
                    pr_url = str(ev["url"])
    else:
        for s in steps:
            for ev in s.get("evidence") or []:
                if isinstance(ev, dict) and ev.get("kind") == "pr" and ev.get("url") and not pr_url:
                    pr_url = str(ev["url"])
        pr_number = pr if pr_url else None
    # Fail-closed agent: only real https run_url (never invent).
    run_url = str(agent.get("run_url") or "").strip()
    if run_url and not (run_url.startswith("http://") or run_url.startswith("https://")):
        run_url = ""
    agent_out = {
        "provider": str(agent.get("provider") or ("cursor-cloud" if run_url else "")),
        "run_url": run_url,
        "model": str(agent.get("model") or ""),
        "run_id": str(agent.get("run_id") or ""),
    }
    comment_url = str(
        (cursor_meta or {}).get("comment_url") or lock.get("cursor_comment_url") or ""
    ).strip()
    if comment_url and not (comment_url.startswith("http://") or comment_url.startswith("https://")):
        comment_url = ""
    wake_state = str((cursor_meta or {}).get("wake_state") or lock.get("wake_state") or "")
    if cursor_meta and cursor_meta.get("ok") and cursor_meta.get("commented") is True and not run_url:
        note = f"@cursor on {repo}#{github_issue or pr}"
        if cursor_meta.get("created"):
            note += " (created)"
        if comment_url:
            note += f" {comment_url}"
        elif cursor_meta.get("html_url"):
            note += f" {cursor_meta.get('html_url')}"
        recent = list(recent) + [
            {
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "text": note,
            }
        ]
    gh_issue_url = ""
    if cursor_meta and str(cursor_meta.get("html_url") or "").startswith("https://github.com/"):
        gh_issue_url = str(cursor_meta.get("html_url") or "")
        if "#issuecomment-" in gh_issue_url and not comment_url:
            comment_url = gh_issue_url
            gh_issue_url = gh_issue_url.split("#", 1)[0]
    elif github_issue and repo:
        gh_issue_url = f"https://github.com/wozniaknorbert95-del/{repo}/issues/{github_issue}"
    return {
        "issue": issue_id,
        "title": issue.get("title") or lock.get("title") or "",
        "repo": repo,
        "worker": worker,
        "action": "@cursor" if worker == "cursor" else worker,
        "step": evaluated.get("step"),
        "status": evaluated.get("status") or "UNKNOWN",
        "steps": steps,
        "progress": progress,
        "checks": checks,
        "pr_number": pr_number,
        "pr_url": pr_url or None,
        "ci_url": ci_url or None,
        "agent": agent_out,
        "diff": diff,
        "recent": recent or None,
        "duration_sec": duration,
        "input_tokens": None,
        "output_tokens": None,
        "cost": None,
        "github_issue": github_issue or None,
        "github_issue_url": gh_issue_url or None,
        "cursor_comment_url": comment_url or None,
        "wake_state": wake_state or None,
    }


def build_approval(
    lanes: dict[str, list],
    live: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """HITL local cards + CI-green waiting (status only — never Merge button)."""
    cards: list[dict[str, Any]] = []
    local_items = list(lanes.get("local") or [])
    hitl_cap = 3
    for item in local_items[:hitl_cap]:
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
    extra = len(local_items) - hitl_cap
    if extra > 0:
        cards.append(
            {
                "kind": "hitl_more",
                "id": "",
                "title": f"+{extra} na laptopie",
                "message": "Reszta HITL — nie na telefonie.",
                "actions": ["pause", "stop"],
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
