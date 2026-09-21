#!/usr/bin/env python3
"""VPS timer: poll Linear+GitHub, write /ops/status cache. Never deploy."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hermes_ops.linear import LinearOps  # noqa: E402
from hermes_ops.orchestrator import Engine, consume_cmd  # noqa: E402
from hermes_ops.policy import has_workflow_dispatch_deploy  # noqa: E402
from hermes_ops.status_cache import write_status  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", help="JSON list of Linear issues (offline)")
    parser.add_argument("--status-out", help="Cache path for akademia vault")
    parser.add_argument("--mode", default=os.environ.get("OPS_MODE", "MANUAL"), choices=("MANUAL", "AUTOPILOT"))
    args = parser.parse_args()
    if has_workflow_dispatch_deploy():
        print("FAIL: orchestrator grew workflow_dispatch deploy", file=sys.stderr)
        return 2
    ledger = Path(os.environ.get("HERMES_OPS_LEDGER", str(ROOT / "data" / "hermes-ops-ledger.jsonl")))
    state = Path(os.environ.get("HERMES_OPS_STATE", str(ROOT / "data" / "hermes-ops-state.json")))
    engine = Engine(mode=args.mode, ledger=ledger, state_path=state)
    engine.load_state()
    ops = LinearOps()
    issues = []
    if args.fixture:
        issues = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        if isinstance(issues, dict):
            issues = issues.get("issues") or []
    else:
        issues = ops.list_queue()
    reason = "vps_timer"
    if ops.last_error:
        engine.engine_state = "UNKNOWN"
        reason = ops.last_error
    cmd = consume_cmd()
    if cmd and cmd.get("action") == "pause":
        engine.pause()
        reason = "paused"
    elif cmd and cmd.get("action") == "stop":
        engine.stop()
        reason = "stopped"
    elif cmd and cmd.get("action") in ("autopilot", "manual"):
        engine.mode = "AUTOPILOT" if cmd.get("action") == "autopilot" else "MANUAL"
        if engine.mode == "MANUAL" and engine.engine_state == "RUNNING":
            engine.engine_state = "PAUSED"
        engine.save_state()
        reason = f"mode_{engine.mode.lower()}"
    elif cmd and cmd.get("action") in ("run_next", "retry"):
        wanted = str(cmd.get("issue_id") or "")
        if cmd.get("action") == "retry" and not wanted:
            lock = engine._lock()
            wanted = str(lock.get("issue_id") or "")
        match = engine.pick_next(issues, wanted)
        if match:
            engine.mode = "MANUAL"
            result = engine.run_next(match)
            reason = str(result.get("error") or "run_next")
            if not result.get("ok") and result.get("code") in (403, 409, 429, 401):
                engine.engine_state = engine.engine_state or "PAUSED"
        else:
            reason = "empty_manual_queue"
    elif engine.mode == "AUTOPILOT" and engine.engine_state != "STOPPED" and not ops.last_error:
        engine.engine_state = "RUNNING"
        engine.tick(issues)
        engine.save_state()
    payload = engine.status_payload(issues)
    payload["reason"] = reason
    if ops.last_error:
        payload["engine"] = "UNKNOWN"
        payload["status"] = "UNKNOWN"
    out = Path(args.status_out) if args.status_out else None
    write_status(payload, out)
    print(json.dumps({"ok": True, "wrote": True, "engine": payload.get("engine"), "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
