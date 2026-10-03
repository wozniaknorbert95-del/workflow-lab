"""Atomic JSON IO for handoff / live status. No secrets in files."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

WORK_MODES = ("buduj", "testuj", "ulepszaj")


def _path(name: str, default: str) -> Path:
    return Path(os.environ.get(name) or default)


def handoff_path() -> Path:
    return _path("HERMES_CONDUCTOR_HANDOFF", "data/hermes-conductor-handoff.json")


def status_path() -> Path:
    return _path("HERMES_CONDUCTOR_STATUS", "data/hermes-conductor-live.json")


def ops_status_path() -> Path:
    return _path("HERMES_OPS_STATUS", "data/ops-status.json")


def max_followups() -> int:
    try:
        n = int(os.environ.get("OPS_CONDUCTOR_MAX_FOLLOWUPS") or "3")
    except (TypeError, ValueError):
        n = 3
    return n if n > 0 else 3


# Import-time aliases for tests / older callers. Prefer the functions above.
HANDOFF = handoff_path()
STATUS = status_path()
OPS_STATUS = ops_status_path()
MAX_FOLLOWUPS = max_followups()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def work_mode(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in WORK_MODES else "buduj"


def cursor_key() -> str:
    return str(os.environ.get("CURSOR_API_KEY") or "").strip()


def repo_url(repo: str) -> str:
    name = str(repo or "workflow-lab").strip() or "workflow-lab"
    if name.startswith("https://"):
        return name
    owner = str(os.environ.get("CONDUCTOR_GITHUB_OWNER") or "wozniaknorbert95-del").strip()
    return f"https://github.com/{owner}/{name}"


def halt_requested(ops: dict[str, Any] | None) -> bool:
    """Halt only on operator Stop/Pause/Take over — not idle PAUSED."""
    if not isinstance(ops, dict):
        return False
    engine = str(ops.get("engine") or ops.get("status") or "").upper()
    reason = str(ops.get("reason") or "").lower()
    if engine == "STOPPED":
        return True
    if engine == "PAUSED" and any(n in reason for n in ("queued_pause", "queued_stop", "queued_take", "take_over")):
        return True
    if any(n in reason for n in ("queued_pause", "queued_stop", "queued_take_over")):
        return True
    return False
