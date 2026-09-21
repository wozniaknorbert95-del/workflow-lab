"""Policy: merge both repos after green CI. Never deploy. HITL = local only."""
from __future__ import annotations

from typing import Any

ALLOWED_REPOS = ("workflow-lab", "dsaas-platform-main")
LOCAL_ONLY = "LOCAL_ONLY"
DEPLOY_DENIED = "ZASADA_11"


def _labels(issue: dict[str, Any]) -> set[str]:
    raw = issue.get("labels") or []
    out: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            out.add(item)
        elif isinstance(item, dict) and item.get("name"):
            out.add(str(item["name"]))
    return out


def allow_merge(repo: str, checks_green: bool, issue: dict[str, Any] | None = None) -> tuple[bool, int, str]:
    """Squash-merge after required checks. Same trust for lab and platform."""
    if repo not in ALLOWED_REPOS:
        return False, 403, "repo_not_in_policy"
    labels = _labels(issue or {})
    if "hitl:approval-required" in labels or "blocked" in labels or "blocked:external" in labels:
        return False, 403, LOCAL_ONLY
    if not checks_green:
        return False, 409, "ci_not_green"
    return True, 200, "ok"


def allow_cursor_comment(issue: dict[str, Any], mode: str = "AUTOPILOT") -> tuple[bool, int, str]:
    """hitl never gets @cursor. MANUAL Run next still requires agent label."""
    labels = _labels(issue)
    if "hitl:approval-required" in labels:
        return False, 403, LOCAL_ONLY
    if "blocked" in labels or "blocked:external" in labels:
        return False, 403, LOCAL_ONLY
    if "agent" not in labels:
        return False, 403, LOCAL_ONLY
    if mode not in ("MANUAL", "AUTOPILOT"):
        return False, 400, "bad_mode"
    return True, 200, "ok"


def allow_deploy(_action: str | None = None) -> tuple[bool, int, str]:
    return False, 403, DEPLOY_DENIED


def has_workflow_dispatch_deploy() -> bool:
    """Orchestrator must not grow a production dispatch path."""
    return False
