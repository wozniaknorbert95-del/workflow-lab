#!/usr/bin/env python3
"""Nous conductor daemon. Watches handoff, writes live JSON, calls Cloud API.

Not the tick. Tick only copies hermes-conductor-live.json into ops-status.json.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hermes_conductor.loop import run_once


def main() -> int:
    interval = float(os.environ.get("HERMES_CONDUCTOR_POLL_SEC") or "3")
    fail_first = str(os.environ.get("CONDUCTOR_FAIL_FIRST") or "").strip() in ("1", "true", "yes")
    once = "--once" in sys.argv
    while True:
        try:
            result = run_once(fail_first=fail_first)
        except Exception as exc:
            print(f"conductor error {type(exc).__name__}", flush=True)
            if once:
                return 2
            time.sleep(max(1.0, interval))
            continue
        state = result.get("state") or "idle"
        refuse = ""
        live = result.get("live") if isinstance(result.get("live"), dict) else {}
        if isinstance(live, dict):
            refuse = str(live.get("refuse") or "")
        agent = (live.get("agent") or {}) if isinstance(live, dict) else {}
        agent_id = str(agent.get("agent_id") or "")[:36]
        url = bool(agent.get("run_url"))
        create_ms = result.get("create_ms")
        if create_ms is None and isinstance(live, dict):
            create_ms = live.get("create_ms")
        http = result.get("http")
        if http is None and isinstance(live, dict):
            http = live.get("http")
        parts = [f"conductor {state}"]
        if refuse:
            parts.append(f"refuse={refuse}")
        if agent_id:
            parts.append(f"agent={agent_id}")
        if http is not None:
            parts.append(f"http={http}")
        if create_ms is not None:
            parts.append(f"create_ms={create_ms}")
        parts.append(f"url={url}")
        print(" ".join(parts), flush=True)
        if once:
            return 0 if result.get("ok") or state == "idle" else 2
        time.sleep(max(1.0, interval))


if __name__ == "__main__":
    raise SystemExit(main())
