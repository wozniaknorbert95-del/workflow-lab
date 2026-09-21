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
from hermes_ops.policy import ALLOWED_MODES, has_workflow_dispatch_deploy  # noqa: E402
from hermes_ops.status_cache import write_status  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", help="JSON list of Linear issues (offline)")
    parser.add_argument("--status-out", help="Cache path for akademia vault")
    parser.add_argument(
        "--mode",
        default=os.environ.get("OPS_MODE", "MANUAL"),
        choices=ALLOWED_MODES,
    )
    parser.add_argument("--phone-fixture", help="phone-loop fixture name for live S1–S6 tests")
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
        raw = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        issues = raw.get("issues") if isinstance(raw, dict) else raw
        issues = list(issues or [])
    else:
        issues = ops.list_queue()
    reason = "vps_timer"
    if ops.last_error:
        engine.engine_state = "UNKNOWN"
        reason = ops.last_error

    phone_fx = None
    if args.phone_fixture:
        from hermes_ops.live_enrich import _load_phone_loop

        phone_fx = _load_phone_loop().load_fixture(args.phone_fixture)

    cmd = consume_cmd()
    if cmd and cmd.get("action") == "pause":
        engine.pause()
        reason = "paused"
    elif cmd and cmd.get("action") == "stop":
        engine.stop()
        reason = "stopped"
    elif cmd and cmd.get("action") == "take_over":
        wanted = str(cmd.get("issue_id") or "")
        match = engine.pick_next(issues, wanted) if wanted else None
        engine.take_over(match)
        reason = "take_over"
    elif cmd and cmd.get("action") in ("autopilot", "manual", "supervised", "set_mode"):
        mode_map = {
            "autopilot": "AUTOPILOT",
            "manual": "MANUAL",
            "supervised": "SUPERVISED",
        }
        if cmd.get("action") == "set_mode":
            target = str(cmd.get("mode") or "MANUAL").upper()
        else:
            target = mode_map.get(str(cmd.get("action")), "MANUAL")
        engine.set_mode(target)
        reason = f"mode_{engine.mode.lower()}"
    elif cmd and cmd.get("action") == "run_all":
        result = engine.run_all(issues)
        reason = str(result.get("error") or "run_all")
    elif cmd and cmd.get("action") in ("run_next", "retry", "start"):
        wanted = str(cmd.get("issue_id") or "")
        if cmd.get("action") == "retry" and not wanted:
            lock = engine._lock()
            wanted = str(lock.get("issue_id") or "")
        match = engine.pick_next(issues, wanted)
        if match:
            if engine.mode == "MANUAL" or cmd.get("action") in ("run_next", "retry", "start"):
                if engine.mode in ("AUTOPILOT", "SUPERVISED") and cmd.get("action") == "start":
                    engine.engine_state = "RUNNING"
                result = engine.run_next(match, fixture=phone_fx)
                reason = str(result.get("error") or "run_next")
                if not result.get("ok") and result.get("code") in (403, 409, 429, 401):
                    engine.engine_state = engine.engine_state or "PAUSED"
        else:
            reason = "empty_manual_queue"
    elif engine.mode in ("AUTOPILOT", "SUPERVISED") and engine.engine_state == "RUNNING" and not ops.last_error:
        engine.tick(issues)
        engine.save_state()

    if engine.busy() or engine.live:
        engine.refresh_live(issues, fixture=phone_fx)

    payload = engine.status_payload(issues)
    payload["reason"] = reason
    if ops.last_error:
        payload["engine"] = "UNKNOWN"
        payload["status"] = "UNKNOWN"
    out = Path(args.status_out) if args.status_out else None
    write_status(payload, out)
    print(
        json.dumps(
            {"ok": True, "wrote": True, "engine": payload.get("engine"), "mode": payload.get("mode"), "reason": reason},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
