#!/usr/bin/env python3
"""Unit tests for Nous conductor — Cloud API caller, not the tick."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hermes_conductor.cloud import CloudClient, _parse_body, busy_or_error
from hermes_conductor.loop import step
from hermes_ops.conductor_adapter import merge_conductor_into_live


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
        if url.rstrip("/").endswith("/runs") or "/runs?" in url:
            return {
                "ok": True,
                "code": 200,
                "body": {
                    "agent": {"id": "bc-same", "url": "https://cursor.com/agents/bc-same"},
                    "run": {"id": "run-2"},
                },
            }
        if "/stream" in url:
            raise RuntimeError("stream boom")
        if "/cancel" in url or "/archive" in url or "/unarchive" in url:
            return {"ok": True, "code": 200, "body": {}}
        if method == "GET" and "agents" in url:
            return {"ok": True, "code": 200, "body": {"agents": []}}
        return {"ok": False, "code": 404, "body": {"error": url}}

    # T1: create OK even when stream would throw (early live, no stream on create).
    created = step(
        handoff=handoff,
        live=None,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_ok),
        fail_first=True,
    )
    live1 = created.get("live") or {}
    agent1 = live1.get("agent") or {}
    if created.get("state") != "created":
        errors.append(f"T1 create expect created, got {created}")
    if agent1.get("run_url") != "https://cursor.com/agents/bc-same":
        errors.append(f"T1 create must set https run_url, got {agent1}")
    if agent1.get("agent_id") != "bc-same":
        errors.append(f"T1 agent_id must be bc-same, got {agent1}")
    if agent1.get("run_id") != "run-1":
        errors.append(f"T1 run_id must be run-1 (not conflated), got {agent1}")
    if (live1.get("conductor") or {}).get("ac", [{}])[0].get("verdict") != "FAIL":
        errors.append(f"T1 fail_first must FAIL AC, got {live1.get('conductor')}")
    if any("/stream" in u for _, u in calls):
        errors.append("T1 create must not call stream before live write")

    # T4: same cmd + AC FAIL → followup_run once
    calls.clear()
    follow = step(
        handoff=handoff,
        live=live1,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_ok),
    )
    live2 = follow.get("live") or {}
    agent2 = live2.get("agent") or {}
    if follow.get("state") != "followup":
        errors.append(f"T4 FAIL AC must follow-up, got {follow}")
    if agent2.get("agent_id") != "bc-same":
        errors.append(f"T4 must keep agent_id, got {agent2}")
    if agent2.get("run_id") != "run-2":
        errors.append(f"T4 run_id must update to run-2, got {agent2}")
    if (live2.get("conductor") or {}).get("followups_used") != 1:
        errors.append(f"T4 followups_used expect 1, got {live2.get('conductor')}")
    follow_posts = [u for m, u in calls if m == "POST" and u.rstrip("/").endswith("/runs")]
    if len(follow_posts) != 1:
        errors.append(f"T4 expect exactly 1 followup_run, got {calls}")

    # T3: new cmd_id → create, not followup
    calls.clear()
    create_count = {"n": 0}

    def fetch_new_cmd(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        calls.append((method, url))
        if method == "POST" and url.rstrip("/").endswith("/agents"):
            create_count["n"] += 1
            return {
                "ok": True,
                "code": 200,
                "body": {
                    "agent": {"id": "bc-new", "url": "https://cursor.com/agents/bc-new"},
                    "run": {"id": "run-n"},
                },
            }
        if "/archive" in url:
            return {"ok": True, "code": 200, "body": {}}
        if url.rstrip("/").endswith("/runs"):
            errors.append("T3 must not followup_run on new cmd")
            return {"ok": False, "code": 409, "body": {"error": "agent_busy"}}
        if method == "GET":
            return {"ok": True, "code": 200, "body": {"agents": []}}
        return {"ok": True, "code": 200, "body": {}}

    switched = step(
        handoff={**handoff, "cmd_id": "newcmd", "issue_id": "QUI-YY"},
        live=live2,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_new_cmd),
    )
    if switched.get("state") != "created":
        errors.append(f"T3 new cmd must create, got {switched}")
    if create_count["n"] != 1:
        errors.append(f"T3 create called {create_count['n']} times")
    if (switched.get("live") or {}).get("agent", {}).get("agent_id") != "bc-new":
        errors.append(f"T3 new agent, got {switched.get('live')}")

    # T2: create timeout → refuse conductor_timeout, create 1×
    calls.clear()
    create_n = {"n": 0}

    def fetch_timeout(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        calls.append((method, url))
        if method == "POST" and url.rstrip("/").endswith("/agents"):
            create_n["n"] += 1
            return {"ok": False, "code": 0, "body": {"error": "timeout:x", "timeout": True}}
        if method == "GET":
            return {"ok": True, "code": 200, "body": {"agents": []}}
        if "/archive" in url:
            return {"ok": True, "code": 200, "body": {}}
        return {"ok": False, "code": 500, "body": {"error": "x"}}

    timed = step(
        handoff={**handoff, "cmd_id": "t2cmd"},
        live=None,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_timeout),
    )
    if (timed.get("live") or {}).get("refuse") != "conductor_timeout":
        errors.append(f"T2 expect conductor_timeout, got {timed}")
    if create_n["n"] != 1:
        errors.append(f"T2 create must be 1×, got {create_n['n']}")

    # T7: recovery after timeout when list has one agent
    def fetch_recover(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        if method == "POST" and url.rstrip("/").endswith("/agents"):
            return {"ok": False, "code": 0, "body": {"error": "timed out", "timeout": True}}
        if method == "GET":
            return {
                "ok": True,
                "code": 200,
                "body": {
                    "agents": [
                        {
                            "id": "bc-rec",
                            "name": "QUI-ZZ conductor",
                            "url": "https://cursor.com/agents/bc-rec",
                            "latestRunId": "run-r",
                            "createdAt": "2026-10-16T00:00:00Z",
                        }
                    ]
                },
            }
        return {"ok": True, "code": 200, "body": {}}

    recovered = step(
        handoff={**handoff, "cmd_id": "t7cmd"},
        live=None,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_recover),
    )
    if recovered.get("state") != "created":
        errors.append(f"T7 recovery must created, got {recovered}")
    if (recovered.get("live") or {}).get("agent", {}).get("run_url") != "https://cursor.com/agents/bc-rec":
        errors.append(f"T7 recovery URL, got {recovered.get('live')}")

    # T6: 401 → cursor_api_auth
    if busy_or_error({"ok": False, "code": 401, "body": {"error": "unauthorized"}}) != "cursor_api_auth":
        errors.append("T6 401 must be cursor_api_auth")
    if busy_or_error({"ok": False, "code": 403, "body": {"error": "forbidden"}}) != "cursor_api_auth":
        errors.append("T6 403 must be cursor_api_auth")

    # T10: empty cmd_id must not create (anti spam)
    spam_calls: list[tuple[str, str]] = []

    def fetch_spam(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        spam_calls.append((method, url))
        return {"ok": True, "code": 200, "body": {}}

    no_cmd = step(
        handoff={**handoff, "cmd_id": ""},
        live=None,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_spam),
    )
    if (no_cmd.get("live") or {}).get("refuse") != "missing_cmd_id":
        errors.append(f"T10 empty cmd_id must refuse missing_cmd_id, got {no_cmd}")
    if any(u.rstrip("/").endswith("/agents") and m == "POST" for m, u in spam_calls):
        errors.append(f"T10 empty cmd_id must not POST create, calls={spam_calls}")
    keep = step(
        handoff={**handoff, "cmd_id": ""},
        live=live1,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_spam),
    )
    if keep.get("state") != "unchanged" or keep.get("wrote"):
        errors.append(f"T10 empty cmd_id + existing URL must unchanged, got {keep}")

    # T5: halt clears run_url
    halt_calls: list[str] = []

    def fetch_halt(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        halt_calls.append(url)
        return {"ok": True, "code": 200, "body": {}}

    halted = step(
        handoff=handoff,
        live=live2,
        ops={"status": "PAUSED", "reason": "queued_pause"},
        key="secret",
        client=CloudClient("secret", fetch=fetch_halt),
    )
    if halted.get("state") != "halted":
        errors.append(f"T5 Pause must halt, got {halted}")
    if (halted.get("live") or {}).get("agent", {}).get("run_url"):
        errors.append(f"T5 halt must clear run_url, got {halted.get('live')}")
    if not any("/archive" in u for u in halt_calls):
        errors.append(f"T5 Take over must archive, calls={halt_calls}")
    again = step(
        handoff=handoff,
        live=halted.get("live"),
        ops={"status": "PAUSED", "reason": "queued_pause"},
        key="secret",
        client=CloudClient("secret", fetch=fetch_halt),
    )
    if again.get("wrote"):
        errors.append(f"T5 halted same cmd must not rewrite, got {again}")

    # T8: adapter halt/foreign purge ghost URL
    live_ops = {
        "issue": "QUI-AA",
        "agent": {"run_url": "https://cursor.com/agents/old", "run_id": "x"},
        "steps": [{"step": 2, "status": "UNKNOWN"}],
    }
    merged_halt = merge_conductor_into_live(
        live_ops,
        {"issue": "QUI-AA", "halted": True, "agent": {"run_url": "https://cursor.com/agents/old"}},
    )
    if (merged_halt or {}).get("agent", {}).get("run_url"):
        errors.append(f"T8 halt must purge URL, got {merged_halt}")
    foreign = merge_conductor_into_live(
        {"issue": "QUI-AA", "agent": {"run_url": "https://cursor.com/agents/old"}},
        {"issue": "QUI-BB", "agent": {"run_url": "https://cursor.com/agents/new", "agent_id": "bc-n"}},
    )
    if (foreign or {}).get("agent", {}).get("run_url"):
        errors.append(f"T8 foreign issue must purge URL, got {foreign}")

    # T9: path defaults share ACADEMY_DATA_DIR
    import os
    from hermes_ops import conductor_adapter as ca
    from hermes_ops.orchestrator import Engine

    with __import__("tempfile").TemporaryDirectory() as tmp:
        os.environ["ACADEMY_DATA_DIR"] = tmp
        # re-read module paths by constructing Engine
        eng = Engine(
            state_path=Path(tmp) / "state.json",
            lock_path=Path(tmp) / "lock.json",
            ledger=Path(tmp) / "ledger.jsonl",
        )
        st, hd = eng._conductor_paths()
        if st.name != "hermes-conductor-live.json" or hd.name != "hermes-conductor-handoff.json":
            errors.append(f"T9 path names, got {st} {hd}")
        if st.parent != Path(tmp) or hd.parent != Path(tmp):
            errors.append(f"T9 defaults must use ACADEMY_DATA_DIR, got {st} {hd}")
        os.environ.pop("ACADEMY_DATA_DIR", None)

    tick = (ROOT / "scripts" / "hermes-ops-tick.py").read_text(encoding="utf-8")
    adapter = (ROOT / "scripts" / "hermes_ops" / "conductor_adapter.py").read_text(encoding="utf-8")
    orch = (ROOT / "scripts" / "hermes_ops" / "orchestrator.py").read_text(encoding="utf-8")
    for label, src in (("tick", tick), ("adapter", adapter), ("orchestrator", orch)):
        if "api.cursor.com" in src:
            errors.append(f"{label} must not call Cursor HTTP API")

    cloud_src = (ROOT / "scripts" / "hermes_conductor" / "cloud.py").read_text(encoding="utf-8")
    if "def followup(" in cloud_src and "def followup_run" in cloud_src:
        # dead followup removed — only followup_run allowed
        if "def followup(self" in cloud_src:
            errors.append("dead CloudClient.followup must be removed")

    if errors:
        print("FAIL:")
        for item in errors:
            print(" -", item)
        return 1
    print("PASS: hermes_conductor T1-T9 (early live, timeout, create-on-issue, followup, halt, auth, recover, adapter)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
