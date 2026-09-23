#!/usr/bin/env python3
"""QUI-70: ack / refuse helpers for phone dispatch (stdlib)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("HERMES_OPS_DATA", os.environ.get("ACADEMY_DATA_DIR", "data")))
# Refuse files live next to ops-status (akademia vault data dir on VPS).
REFUSE_DIR = Path(os.environ.get("HERMES_OPS_STATUS", str(DATA_DIR / "ops-status.json"))).parent


def cmd_id_of(cmd: dict[str, Any] | None) -> str:
    if not isinstance(cmd, dict):
        return ""
    return str(cmd.get("id") or "").strip()


def make_ack(cmd: dict[str, Any] | None) -> dict[str, Any] | None:
    cid = cmd_id_of(cmd)
    if not cid:
        return None
    return {
        "cmd_id": cid,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": str(cmd.get("action") or ""),
    }


def write_refuse(
    cmd: dict[str, Any] | None,
    reason: str,
    *,
    directory: Path | None = None,
) -> dict[str, Any]:
    """Fail-closed refuse blob + refuse-<id>.json for akademia derive_dispatch."""
    cid = cmd_id_of(cmd)
    blob = {
        "cmd_id": cid or None,
        "reason": str(reason or "refused")[:200],
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": str((cmd or {}).get("action") or ""),
        "issue_id": str((cmd or {}).get("issue_id") or ""),
    }
    if not cid:
        return blob
    root = directory or REFUSE_DIR
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"refuse-{cid}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return blob


def refuse_reason_from_result(result: dict[str, Any] | None) -> str | None:
    """Map orchestrator error → refuse reason string (no secrets)."""
    if not isinstance(result, dict) or result.get("ok"):
        return None
    err = str(result.get("error") or result.get("code") or "refused")
    code = result.get("code")
    mapping = {
        "missing_GITHUB_OPS_COMMENT": "missing_GITHUB_OPS_COMMENT",
        "missing GITHUB_OPS_WRITE": "missing_GITHUB_OPS_WRITE",
        "cursor_wake_forbidden": "cursor_wake_forbidden",
        "cursor_wake_failed": "cursor_wake_failed",
        "daily_cap": "cap_OPS_MAX_RUNS_PER_DAY",
        "concurrent": "lock",
        "idempotent": "lock",
        "LOCAL_ONLY": "lock",
        "empty_manual_queue": "empty_queue",
        "empty_queue": "empty_queue",
        "repo_not_in_policy": "repo_not_in_policy",
    }
    for key, reason in mapping.items():
        if key in err:
            return reason
    if code == 401:
        return "missing_GITHUB_OPS_WRITE"
    if code == 429:
        return "cap_OPS_MAX_RUNS_PER_DAY"
    if code == 409:
        return "lock"
    return err.replace(" ", "_")[:80]


def attach_dispatch(
    payload: dict[str, Any],
    *,
    ack: dict[str, Any] | None = None,
    refuse: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = dict(payload)
    if ack:
        out["ack"] = ack
    if refuse:
        out["refuse"] = refuse
    return out
