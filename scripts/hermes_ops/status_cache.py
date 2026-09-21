"""Status cache for akademia GET /ops/status. Phone never calls api.github.com."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .telemetry import today_stats

STATUS_PATH = Path(os.environ.get("HERMES_OPS_STATUS", "data/ops-status.json"))


def build_status(
    *,
    mode: str = "MANUAL",
    engine: str = "PAUSED",
    lanes: dict[str, list] | None = None,
    live: dict[str, Any] | None = None,
    reason: str = "cache",
    ledger: Path | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    status = engine or "UNKNOWN"
    if engine in (None, "", "UNKNOWN"):
        status = "UNKNOWN"
    if str(status).upper() == "GREEN" and str(engine).upper() in ("UNKNOWN", "PAUSED", ""):
        status = engine or "UNKNOWN"
    return {
        "ok": True,
        "mode": mode,
        "engine": engine or "UNKNOWN",
        "step": (live or {}).get("step"),
        "status": status or "UNKNOWN",
        "lanes": lanes or {"autopilot": [], "manual": [], "local": []},
        "live": live,
        "today": today_stats(ledger),
        "reason": reason,
        "updated_at": updated_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def write_status(payload: dict[str, Any], path: Path | None = None) -> Path:
    target = path or STATUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)
    return target
