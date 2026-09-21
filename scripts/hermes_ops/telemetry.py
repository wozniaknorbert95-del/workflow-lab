"""Redacting JSONL ledger. Today stats come from this file, not GitHub live."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

SECRET_RX = re.compile(r"(ghp_|github_pat_|lin_api_|sk-|Bearer\s+\S+)", re.I)

LEDGER = Path(os.environ.get("HERMES_OPS_LEDGER", "data/hermes-ops-ledger.jsonl"))
OPS_MAX_CONCURRENT = int(os.environ.get("OPS_MAX_CONCURRENT", "1"))
OPS_MAX_RUNS_PER_DAY = int(os.environ.get("OPS_MAX_RUNS_PER_DAY", "8"))


def redact(text: str) -> str:
    return SECRET_RX.sub("[REDACTED]", text)


def append_event(event: dict[str, Any], path: Path | None = None) -> None:
    target = path or LEDGER
    target.parent.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event.setdefault("at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    line = redact(json.dumps(event, ensure_ascii=False))
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def today_stats(path: Path | None = None, day: str | None = None) -> dict[str, Any]:
    target = path or LEDGER
    day = day or time.strftime("%Y-%m-%d", time.gmtime())
    runs = merged = failed = 0
    if not target.is_file():
        return {"runs": 0, "merged": 0, "failed": 0, "tokens": None, "cost": None}
    for raw in target.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or not raw.startswith("{"):
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        at = str(row.get("at") or "")
        if not at.startswith(day):
            continue
        kind = str(row.get("kind") or row.get("result") or "")
        runs += 1
        if kind in ("merged", "merge_ok"):
            merged += 1
        elif kind in ("failed", "fail", "error"):
            failed += 1
    return {"runs": runs, "merged": merged, "failed": failed, "tokens": None, "cost": None}


def over_daily_cap(path: Path | None = None) -> bool:
    return int(today_stats(path).get("runs") or 0) >= OPS_MAX_RUNS_PER_DAY
