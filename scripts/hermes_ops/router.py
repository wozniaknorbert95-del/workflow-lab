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
        }
        lanes[lane].append(row)
    return lanes


def load_fixture(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("issues") or [])
    return list(data)
