#!/usr/bin/env python3
"""Unit tests for Nous conductor — Cloud API caller, not the tick."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hermes_conductor.cloud import CloudClient, _parse_body
from hermes_conductor.loop import step


def main() -> int:
    errors: list[str] = []
    handoff = {
        "issue_id": "QUI-ZZ",
        "title": "probe",
        "repo": "workflow-lab",
        "work_mode": "buduj",
        "cmd_id": "abc123",
    }

    sse = _parse_body('event: tool_call\ndata: {"cmd":"pytest","excerpt":"1 passed","verdict":"PASS"}\n\n')
    if not sse.get("events") or sse["events"][0].get("verdict") != "PASS":
        errors.append(f"SSE parse, got {sse}")
    if _parse_body("{not-json") .get("events") is None:
        errors.append("broken JSON must not raise")

    idle = step(handoff=None, live=None, ops=None, key="k")
    if idle.get("state") != "idle" or idle.get("wrote"):
        errors.append(f"empty handoff must idle, got {idle}")

    no_key = step(handoff=handoff, live=None, ops=None, key="")
    if no_key.get("state") != "refuse" or (no_key.get("live") or {}).get("refuse") != "missing_CURSOR_API_KEY":
        errors.append(f"missing key must refuse, got {no_key}")
    if (no_key.get("live") or {}).get("agent", {}).get("run_url"):
        errors.append("missing key must not invent run_url")

    calls: list[tuple[str, str]] = []

    def fetch_ok(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        calls.append((method, url))
        if method == "POST" and url.rstrip("/").endswith("/agents"):
            return {
                "ok": True,
                "code": 200,
                "body": {
                    "agent": {
                        "id": "bc-same",
                        "url": "https://cursor.com/agents/bc-same",
                        "latestRunId": "run-1",
                    },
                    "run": {"id": "run-1"},
                },
            }
        if "/followup" in url or url.rstrip("/").endswith("/runs"):
            return {
                "ok": True,
                "code": 200,
                "body": {
                    "agent": {"id": "bc-same", "url": "https://cursor.com/agents/bc-same"},
                    "run": {"id": "run-2"},
                },
            }
        if "/stream" in url:
            return {
                "ok": True,
                "code": 200,
                "body": {"events": [{"cmd": "pytest", "excerpt": "1 passed", "verdict": "PASS"}]},
            }
        if "/cancel" in url or "/archive" in url:
            return {"ok": True, "code": 200, "body": {}}
        return {"ok": False, "code": 404, "body": {"error": url}}

    created = step(
        handoff=handoff,
        live=None,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_ok),
        fail_first=True,
    )
    live1 = created.get("live") or {}
    if created.get("state") != "created":
        errors.append(f"create expect created, got {created}")
    if (live1.get("agent") or {}).get("run_url") != "https://cursor.com/agents/bc-same":
        errors.append(f"create must set https run_url, got {live1.get('agent')}")
    if (live1.get("conductor") or {}).get("ac", [{}])[0].get("verdict") != "FAIL":
        errors.append(f"fail_first must FAIL AC, got {live1.get('conductor')}")
    if any("/followup" in u or u.endswith("/runs") for _, u in calls if "agents/bc-same" in u):
        errors.append("first create must not follow-up")

    follow = step(
        handoff=handoff,
        live=live1,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_ok),
    )
    live2 = follow.get("live") or {}
    if follow.get("state") != "followup":
        errors.append(f"FAIL AC must follow-up, got {follow}")
    if (live2.get("agent") or {}).get("run_id") != "bc-same":
        errors.append(f"follow-up must keep agentId, got {live2.get('agent')}")
    if (live2.get("conductor") or {}).get("followups_used") != 1:
        errors.append(f"followups_used expect 1, got {live2.get('conductor')}")
    if (live2.get("conductor") or {}).get("ac", [{}])[0].get("verdict") != "PASS":
        errors.append(f"follow-up AC must PASS, got {live2.get('conductor')}")

    calls.clear()

    def fetch_busy(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        calls.append((method, url))
        return {"ok": False, "code": 409, "body": {"error": "agent_busy"}}

    busy = step(
        handoff={**handoff, "cmd_id": "newcmd"},
        live=live2,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_busy),
    )
    if (busy.get("live") or {}).get("refuse") != "cursor_api_busy":
        errors.append(f"409 must refuse cursor_api_busy, got {busy}")

    halt_calls: list[str] = []

    def fetch_halt(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        halt_calls.append(url)
        return {"ok": True, "code": 200, "body": {}}

    halted = step(
        handoff=handoff,
        live=live2,
        ops={"status": "PAUSED"},
        key="secret",
        client=CloudClient("secret", fetch=fetch_halt),
    )
    if halted.get("state") != "halted":
        errors.append(f"Pause must halt, got {halted}")
    if not any("/archive" in u for u in halt_calls):
        errors.append(f"Take over must archive, calls={halt_calls}")
    again = step(
        handoff=handoff,
        live=halted.get("live"),
        ops={"status": "PAUSED"},
        key="secret",
        client=CloudClient("secret", fetch=fetch_halt),
    )
    if again.get("wrote") or any("/runs" in u and "/cancel" not in u for u in halt_calls[2:]):
        errors.append(f"halted same cmd must not follow-up, got {again} {halt_calls}")

    tick = (ROOT / "scripts" / "hermes-ops-tick.py").read_text(encoding="utf-8")
    adapter = (ROOT / "scripts" / "hermes_ops" / "conductor_adapter.py").read_text(encoding="utf-8")
    orch = (ROOT / "scripts" / "hermes_ops" / "orchestrator.py").read_text(encoding="utf-8")
    for label, src in (("tick", tick), ("adapter", adapter), ("orchestrator", orch)):
        if "api.cursor.com" in src:
            errors.append(f"{label} must not call Cursor HTTP API")

    if errors:
        print("FAIL:")
        for item in errors:
            print(" -", item)
        return 1
    print("PASS: hermes_conductor (idle, missing key, create, same agentId follow-up, 409, halt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
