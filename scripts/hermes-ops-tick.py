#!/usr/bin/env python3
"""VPS timer: poll Linear+GitHub, write /ops/status cache. Never deploy."""
from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--mode", default="MANUAL", choices=("MANUAL", "AUTOPILOT"))
    args = parser.parse_args()
    if has_workflow_dispatch_deploy():
        print("FAIL: orchestrator grew workflow_dispatch deploy", file=sys.stderr)
        return 2
    issues = []
    if args.fixture:
        issues = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        if isinstance(issues, dict):
            issues = issues.get("issues") or []
    else:
        issues = LinearOps().list_queue()
    engine = Engine(mode=args.mode)
    cmd = consume_cmd()
    if cmd and cmd.get("action") == "pause":
        engine.pause()
    elif cmd and cmd.get("action") == "stop":
        engine.stop()
    elif cmd and cmd.get("action") == "run_next":
        wanted = str(cmd.get("issue_id") or "")
        match = next((i for i in issues if str(i.get("id")) == wanted), None)
        if match:
            engine.mode = "MANUAL"
            engine.run_next(match)
    elif args.mode == "AUTOPILOT":
        engine.engine_state = "RUNNING"
        engine.tick(issues)
    payload = engine.status_payload(issues)
    out = Path(args.status_out) if args.status_out else None
    write_status(payload, out)
    print(json.dumps({"ok": True, "wrote": True, "engine": payload.get("engine")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
