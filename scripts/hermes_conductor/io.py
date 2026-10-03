"""Atomic JSON IO for handoff / live status. No secrets in files."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

HANDOFF = Path(os.environ.get("HERMES_CONDUCTOR_HANDOFF", "data/hermes-conductor-handoff.json"))
STATUS = Path(os.environ.get("HERMES_CONDUCTOR_STATUS", "data/hermes-conductor-live.json"))
OPS_STATUS = Path(os.environ.get("HERMES_OPS_STATUS", "data/ops-status.json"))
MAX_FOLLOWUPS = int(os.environ.get("OPS_CONDUCTOR_MAX_FOLLOWUPS", "3") or "3")
WORK_MODES = ("buduj", "testuj", "ulepszaj")


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
    if not isinstance(ops, dict):
        return False
    engine = str(ops.get("engine") or ops.get("status") or "").upper()
    return engine in ("PAUSED", "STOPPED")
