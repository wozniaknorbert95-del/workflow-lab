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
OPS_RUN_ALL = os.environ.get("OPS_RUN_ALL", "0").strip() in ("1", "true", "TRUE", "yes")

# Full schema from takiego.txt — unknown fields stay null (never fake $0.00).
TELEMETRY_FIELDS = (
    "issue",
    "agent",
    "model",
    "input_tokens",
    "output_tokens",
    "duration",
    "cost",
    "tests",
    "retries",
    "pr",
    "result",
    "kind",
    "repo",
)


def redact(text: str) -> str:
    return SECRET_RX.sub("[REDACTED]", text)


def append_event(event: dict[str, Any], path: Path | None = None) -> None:
    target = path or LEDGER
    target.parent.mkdir(parents=True, exist_ok=True)
    row: dict[str, Any] = {k: None for k in TELEMETRY_FIELDS}
    row.update({k: v for k, v in event.items() if k in TELEMETRY_FIELDS or k == "at"})
    row.setdefault("at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    # Never coerce missing cost/tokens to 0.
    for money in ("input_tokens", "output_tokens", "cost", "duration", "tests", "retries"):
        if money in event and event[money] is None:
            row[money] = None
    line = redact(json.dumps(row, ensure_ascii=False))
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def today_stats(path: Path | None = None, day: str | None = None) -> dict[str, Any]:
    target = path or LEDGER
    day = day or time.strftime("%Y-%m-%d", time.gmtime())
    runs = merged = failed = waiting = 0
    tokens_sum = 0
    cost_sum = 0.0
    has_tokens = False
    has_cost = False
    if not target.is_file():
        return {
            "runs": 0,
            "merged": 0,
            "failed": 0,
            "waiting": 0,
            "tokens": None,
            "cost": None,
        }
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
        # Cap counts agent starts only — pause/mode/ack must not burn OPS_MAX_RUNS_PER_DAY.
        if kind in ("run_next", "started"):
            runs += 1
        if kind in ("merged", "merge_ok"):
            merged += 1
        elif kind in ("failed", "fail", "error"):
            failed += 1
        elif kind in ("run_next", "started", "paused"):
            waiting += 1
        inn = row.get("input_tokens")
        out = row.get("output_tokens")
        if isinstance(inn, (int, float)) or isinstance(out, (int, float)):
            has_tokens = True
            tokens_sum += int(inn or 0) + int(out or 0)
        cost = row.get("cost")
        if isinstance(cost, (int, float)):
            has_cost = True
            cost_sum += float(cost)
    return {
        "runs": runs,
        "merged": merged,
        "failed": failed,
        "waiting": waiting,
        "tokens": tokens_sum if has_tokens else None,
        "cost": round(cost_sum, 4) if has_cost else None,
    }


def over_daily_cap(path: Path | None = None) -> bool:
    return int(today_stats(path).get("runs") or 0) >= OPS_MAX_RUNS_PER_DAY


def run_all_enabled() -> bool:
    return OPS_RUN_ALL
