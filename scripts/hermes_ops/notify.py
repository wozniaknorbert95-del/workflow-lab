"""SUPERVISED attention → Web Push via akademia push-send (same VAPID)."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

# akademia data dir on VPS shared with vault; local default under workflow-lab/data.
PENDING_PATH = Path(
    os.environ.get(
        "HERMES_OPS_PUSH_PENDING",
        str(Path(os.environ.get("ACADEMY_DATA_DIR", "/opt/akademia/data")) / "ops-push-pending.json"),
    )
)
STATE_PATH = Path(
    os.environ.get(
        "HERMES_OPS_PUSH_STATE",
        str(Path(os.environ.get("ACADEMY_DATA_DIR", "/opt/akademia/data")) / "ops-push-last.json"),
    )
)
PUSH_SEND = Path(
    os.environ.get(
        "AKADEMIA_PUSH_SEND",
        "/opt/akademia/scripts/push-send.py",
    )
)
COOLDOWN_SEC = int(os.environ.get("OPS_PUSH_COOLDOWN_SEC", "3600"))


def _fingerprint(mode: str, lanes: dict[str, list], live: dict[str, Any] | None) -> str:
    local_ids = sorted(str(i.get("id") or "") for i in (lanes.get("local") or []))
    live_id = str((live or {}).get("issue") or "")
    live_st = str((live or {}).get("status") or "")
    return f"{mode}|{','.join(local_ids)}|{live_id}|{live_st}"


def should_alert(*, mode: str, lanes: dict[str, list], live: dict[str, Any] | None, engine: str) -> bool:
    if str(mode or "").upper() != "SUPERVISED":
        return False
    local = lanes.get("local") or []
    if local:
        return True
    if live and str(live.get("action") or "") == "take_over":
        return True
    checks = (live or {}).get("checks") or {}
    if str(checks.get("overall") or "").upper() == "PASS" and int((live or {}).get("step") or 0) < 6:
        return True
    if str(engine or "").upper() in ("PAUSED", "STOPPED") and live:
        return True
    return False


def build_payload(*, lanes: dict[str, list], live: dict[str, Any] | None) -> dict[str, str]:
    local = lanes.get("local") or []
    if local:
        first = local[0]
        return {
            "title": "Hermes Ops — HITL",
            "body": f"{first.get('id') or 'issue'}: zostaw na laptopie ({len(local)} local)",
            "url": "./OPS.html",
            "tag": "hermes-ops-hitl",
        }
    if live and live.get("issue"):
        return {
            "title": "Hermes Ops — Supervised",
            "body": f"{live.get('issue')} S{live.get('step') or '?'} · {live.get('status') or 'check'}",
            "url": "./OPS.html",
            "tag": "hermes-ops-supervised",
        }
    return {
        "title": "Hermes Ops — Supervised",
        "body": "Sprawdź /ops — pętla czeka na Ciebie.",
        "url": "./OPS.html",
        "tag": "hermes-ops-supervised",
    }


def _cooldown_ok(fp: str) -> bool:
    if not STATE_PATH.is_file():
        return True
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return True
    if str(data.get("fp") or "") != fp:
        return True
    last = float(data.get("at") or 0)
    return (time.time() - last) >= COOLDOWN_SEC


def _mark_sent(fp: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"fp": fp, "at": time.time()}, ensure_ascii=False),
        encoding="utf-8",
    )


def write_pending(payload: dict[str, str], path: Path | None = None) -> Path:
    target = path or PENDING_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)
    return target


def maybe_supervised_push(
    *,
    mode: str,
    lanes: dict[str, list],
    live: dict[str, Any] | None,
    engine: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Write pending + optionally invoke akademia push-send --ops."""
    if not should_alert(mode=mode, lanes=lanes, live=live, engine=engine):
        return {"ok": True, "skipped": "no_alert"}
    fp = _fingerprint(mode, lanes, live)
    if not _cooldown_ok(fp):
        return {"ok": True, "skipped": "cooldown"}
    payload = build_payload(lanes=lanes, live=live)
    write_pending(payload)
    if dry_run:
        return {"ok": True, "dry_run": True, "payload": payload}
    if PUSH_SEND.is_file():
        try:
            subprocess.run(
                [os.environ.get("PYTHON", "python3"), str(PUSH_SEND), "--ops", "--force"],
                check=False,
                timeout=60,
                capture_output=True,
            )
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__, "pending": True}
    _mark_sent(fp)
    return {"ok": True, "queued": True, "payload": payload}
