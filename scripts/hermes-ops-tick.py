#!/usr/bin/env python3
"""VPS timer: poll Linear+GitHub, write /ops/status cache. Never deploy.

QUI-70: always echo ack{cmd_id,at} when consuming ops-cmd.json; write refuse-*
on denial so phone shows REFUSED instead of fake RUNNING.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hermes_ops.dispatch_ack import (  # noqa: E402
    attach_dispatch,
    make_ack,
    refuse_reason_from_result,
    write_refuse,
)
from hermes_ops.linear import LinearOps  # noqa: E402
from hermes_ops.notify import maybe_supervised_push  # noqa: E402
from hermes_ops.orchestrator import Engine, consume_cmd  # noqa: E402
from hermes_ops.policy import ALLOWED_MODES, has_workflow_dispatch_deploy  # noqa: E402
from hermes_ops.status_cache import write_status  # noqa: E402

WORKER_ACTIONS = ("start", "run_next", "retry", "run_all")


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
    parser.add_argument("--no-push", action="store_true", help="skip SUPERVISED web push")
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
        ops.source = "fixture"
    else:
        issues = ops.list_queue()
    reason = "vps_timer"
    if ops.source == "queue_file":
        reason = "queue_file"
    if ops.last_error:
        engine.engine_state = "UNKNOWN"
        reason = ops.last_error
    elif engine.engine_state == "UNKNOWN" and ops.source in ("queue_file", "linear_api", "fixture", "fetch", "arg"):
        engine.engine_state = "PAUSED"
        engine.save_state()

    phone_fx = None
    if args.phone_fixture:
        from hermes_ops.live_enrich import _load_phone_loop

        phone_fx = _load_phone_loop().load_fixture(args.phone_fixture)

    cmd = consume_cmd()
    ack = make_ack(cmd) if cmd else None
    refuse = None
    last_result: dict | None = None

    def _refuse_from(result: dict | None, fallback: str = "") -> None:
        nonlocal refuse, reason
        why = refuse_reason_from_result(result) or fallback
        if not why or not cmd:
            return
        refuse = write_refuse(cmd, why)
        reason = f"refuse_{why}"

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
        last_result = engine.run_all(issues)
        reason = str(last_result.get("error") or "run_all")
        if not last_result.get("ok"):
            _refuse_from(last_result)
            engine.engine_state = "PAUSED"
            engine.save_state()
    elif cmd and cmd.get("action") in ("run_next", "retry", "start"):
        wanted = str(cmd.get("issue_id") or "")
        if cmd.get("action") == "retry" and not wanted:
            lock = engine._lock()
            wanted = str(lock.get("issue_id") or "")
        match = engine.pick_next(issues, wanted)
        if match:
            if engine.mode == "MANUAL" or cmd.get("action") in ("run_next", "retry", "start"):
                last_result = engine.run_next(match, fixture=phone_fx)
                reason = str(last_result.get("error") or "run_next")
                if not last_result.get("ok"):
                    _refuse_from(last_result)
                    engine.engine_state = "PAUSED"
                    engine._clear_lock()
                    engine.save_state()
        else:
            reason = "empty_manual_queue"
            _refuse_from({"ok": False, "error": "empty_queue"}, "empty_queue")
            engine.engine_state = "PAUSED"
            engine.save_state()
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
        if cmd and str(cmd.get("action") or "") in WORKER_ACTIONS:
            refuse = write_refuse(cmd, f"linear_{ops.last_error}")
    # QUI-70 E3: always attach ack when we consumed a cmd (picked_up / running / refused).
    payload = attach_dispatch(payload, ack=ack, refuse=refuse)
    if not args.no_push and not ops.last_error:
        push_result = maybe_supervised_push(
            mode=engine.mode,
            lanes=payload.get("lanes") or {},
            live=payload.get("live"),
            engine=str(payload.get("engine") or ""),
        )
        payload["push"] = {k: push_result.get(k) for k in ("ok", "skipped", "queued") if k in push_result}
    out = Path(args.status_out) if args.status_out else None
    write_status(payload, out)
    print(
        json.dumps(
            {
                "ok": True,
                "wrote": True,
                "engine": payload.get("engine"),
                "mode": payload.get("mode"),
                "reason": reason,
                "source": ops.source,
                "active_agents": len(payload.get("active_agents") or []),
                "ack": (ack or {}).get("cmd_id"),
                "refuse": (refuse or {}).get("reason"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
