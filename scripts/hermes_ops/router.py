"""Linear label router — three lanes, no third taxonomy."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .policy import _labels

LANE_AUTOPILOT = "autopilot"
LANE_MANUAL = "manual"
LANE_LOCAL = "local"


def classify_issue(issue: dict[str, Any], mode: str = "AUTOPILOT") -> str:
    labels = _labels(issue)
    status = str(issue.get("status") or issue.get("state") or "").lower()
    if "hitl:approval-required" in labels:
        return LANE_LOCAL
    if "blocked" in labels or "blocked:external" in labels:
        return LANE_LOCAL
    if "agent" not in labels:
        return LANE_LOCAL
    if status in ("human review", "security gate"):
        return LANE_LOCAL
    if mode == "MANUAL":
        return LANE_MANUAL
    return LANE_AUTOPILOT


def split_lanes(issues: list[dict[str, Any]], mode: str = "AUTOPILOT") -> dict[str, list[dict[str, Any]]]:
    lanes: dict[str, list[dict[str, Any]]] = {
        LANE_AUTOPILOT: [],
        LANE_MANUAL: [],
        LANE_LOCAL: [],
    }
    for issue in issues:
        lane = classify_issue(issue, mode=mode)
        row = {
            "id": issue.get("id") or issue.get("identifier"),
            "title": issue.get("title") or "",
            "repo": issue.get("repo") or "",
            "url": issue.get("url") or "",
            "lane": lane,
            "labels": sorted(_labels(issue)),
            "status": issue.get("status") or "",
        }
        lanes[lane].append(row)
    return lanes


def attach_lane_progress(
    lanes: dict[str, list[dict[str, Any]]],
    live: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Copy live S n/6 progress onto the matching queue card."""
    if not live or not live.get("issue"):
        return lanes
    live_id = str(live.get("issue") or "")
    progress = live.get("progress")
    out: dict[str, list[dict[str, Any]]] = {}
    for name, items in lanes.items():
        cloned: list[dict[str, Any]] = []
        for item in items:
            row = dict(item)
            if str(row.get("id") or "") == live_id and progress:
                row["progress"] = progress
                row["step"] = live.get("step")
            cloned.append(row)
        out[name] = cloned
    return out


def active_agents_from(
    live: dict[str, Any] | None,
    lock: dict[str, Any] | None,
    worker: str = "cursor",
) -> list[dict[str, Any]]:
    """WIP strip: currently running Cursor (max 1 by policy)."""
    agents: list[dict[str, Any]] = []
    issue_id = str((live or {}).get("issue") or (lock or {}).get("issue_id") or "")
    if not issue_id:
        return agents
    if (live or {}).get("action") == "take_over":
        return agents
    agents.append(
        {
            "id": issue_id,
            "title": (live or {}).get("title") or "",
            "worker": (live or {}).get("worker") or worker,
            "step": (live or {}).get("step"),
            "status": (live or {}).get("status") or "RUNNING",
            "progress": (live or {}).get("progress"),
            "repo": (live or {}).get("repo") or (lock or {}).get("repo") or "",
        }
    )
    return agents


def load_fixture(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("issues") or [])
    return list(data)
