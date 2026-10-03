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
        extra = f" refuse={refuse}" if refuse else ""
        url = ((live.get("agent") or {}) if isinstance(live, dict) else {}).get("run_url") or ""
        print(f"conductor {state}{extra} url={bool(url)}", flush=True)
        if once:
            return 0 if result.get("ok") or state == "idle" else 2
        time.sleep(max(1.0, interval))


if __name__ == "__main__":
    raise SystemExit(main())
