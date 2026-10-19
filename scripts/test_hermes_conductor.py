#!/usr/bin/env python3
"""Unit tests for Nous conductor — Cloud API caller, not the tick."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hermes_conductor.cloud import CloudClient, _parse_body, busy_or_error
from hermes_conductor.loop import _brief, step
from hermes_ops.conductor_adapter import merge_conductor_into_live, write_handoff
from hermes_ops.issue_brief import (
    build_issue_json,
    extract_ac_list,
    extract_dor_excerpts,
    resolve_brief_kind,
)



def _fold(text: str) -> str:
    import unicodedata

    low = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(c for c in low if not unicodedata.combining(c)).replace("ł", "l")


def _preflight_dor_missing(ij: dict[str, Any]) -> list[str]:
    """Mirror of dsaas-platform-main check-linear-contract._missing_dor (2026-10-19)."""
    import re

    text = " ".join(str(ij.get(k, "")) for k in ("title", "body", "description"))
    norm = _fold(text)
    labels = [str(x).lower() for x in ij.get("labels") or []]
    miss: list[str] = []
    if not ij.get("estimate"):
        miss.append("estimate")
    if not ("kryteria akceptacji" in norm or "acceptance" in norm or "- [ ]" in text):
        miss.append("ac")
    if "agent" not in labels:
        miss.append("agent")
    if "severity" not in norm and not any(p in norm for p in ("p0", "p1", "p2", "p3")):
        miss.append("severity")
    if "nc-" not in norm:
        miss.append("nc")
    if "fala" not in norm:
        miss.append("fala")
    if "owner" not in norm and "raci" not in norm:
        miss.append("owner")
    if "zakres srodowiska" not in norm and "zasada 11" not in norm:
        miss.append("zakres")
    rb = re.search(r"(?im)^#+\s*rollback\s*$\n+\s*\S", text) or re.search(r"(?im)rollback\s*:\s*\S", text)
    if not rb:
        miss.append("rollback")
    return miss


def _t13_issue_json() -> list[str]:
    import json
    import tempfile

    errors: list[str] = []
    fx = json.loads((ROOT / "scripts" / "fixtures" / "qui147-issue.json").read_text(encoding="utf-8"))
    issue = {k: fx[k] for k in ("id", "title", "status", "labels", "estimate", "project", "repo", "url")}
    issue["status"] = "Ready"
    ij = build_issue_json(issue, fx["description"])
    if ij.get("v") != 1 or ij.get("id") != "QUI-147":
        errors.append(f"T13 issue_json header, got v={ij.get('v')} id={ij.get('id')}")
    if ij.get("estimate") != 3 or "agent" not in ij.get("labels", []):
        errors.append(f"T13 estimate/labels, got {ij.get('estimate')} {ij.get('labels')}")
    miss = _preflight_dor_missing(ij)
    if miss:
        errors.append(f"T13 QUI-147 ISSUE-JSON must pass platform DoR, missing={miss}")
    desc = ij.get("description") or ""
    if len(desc) > 2500 or "http" in desc or "```" in desc:
        errors.append(f"T13 description must be bounded and sanitized, len={len(desc)}")
    if "Pomiar przed" in desc or "Dziennik" in desc:
        errors.append("T13 description must be a DoR digest, not the raw description")

    # B6a: issue without data → JSON still emitted, preflight would STOP (fail-closed).
    bare = build_issue_json({"id": "qui-999", "title": "bez danych", "labels": []}, "")
    if bare.get("id") != "QUI-999" or bare.get("estimate") is not None or bare.get("description"):
        errors.append(f"T13 bare issue_json must stay empty, got {bare}")
    if "estimate" not in _preflight_dor_missing(bare):
        errors.append("T13 bare issue_json must fail DoR (B6a)")

    with tempfile.TemporaryDirectory() as tmp:
        hd = Path(tmp) / "handoff.json"
        write_handoff({**issue, "description": fx["description"]}, work_mode="testuj", cmd_id="c13", path=hd, fetch_linear=False)
        ho = json.loads(hd.read_text(encoding="utf-8"))
    if "description" in ho:
        errors.append("T13 handoff must not persist raw description")
    if (ho.get("issue_json") or {}).get("id") != "QUI-147":
        errors.append(f"T13 handoff must carry issue_json, got {ho.get('issue_json')}")
    text = _brief(ho)
    if "ISSUE-JSON v1" not in text:
        errors.append("T13 platform brief must carry ISSUE-JSON v1")
    if "--issue-json tmp/issue-QUI-147.json" not in text or "tmp/issue-QUI-147.json" not in text:
        errors.append("T13 brief must give the exact preflight command")
    start = text.find("```json\n")
    end = text.find("\n```", start + 8)
    try:
        parsed = json.loads(text[start + 8 : end])
    except (ValueError, TypeError):
        parsed = {}
    if parsed != ho["issue_json"]:
        errors.append("T13 JSON in brief must parse and equal handoff issue_json")
    if "/start" not in text or "### Stan sesji" not in text:
        errors.append("T13 brief must use /start + ### Stan sesji")
    if "STOP ma pierwszeństwo przed AC" not in text:
        errors.append("T13 brief must say STOP wins over AC")
    # Template only: issue content (dor_excerpts/AC) may legitimately quote old command names.
    template = _brief({**ho, "dor_excerpts": {}, "ac": []}) + _brief({**ho, "dor_excerpts": {}, "ac": []}, steer=True)
    if "context-state" in template or "scope-lock" in template or "/resume" in template:
        errors.append("T13 brief template must not reference context-state / scope-lock / resume")
    if ".cursor/commands/autopilot.md" not in text:
        errors.append("T13 autopilot.md path must stay unchanged (K1)")
    old = {k: v for k, v in ho.items() if k != "issue_json"}
    old_text = _brief(old)
    if '"estimate": null' not in old_text:
        errors.append("T13 pre-QUI-153 handoff must still get a bare ISSUE-JSON (→ STOP-LINEAR)")
    lab = _brief({**ho, "repo": "workflow-lab"})
    if "session-preflight" in lab:
        errors.append("T13 workflow-lab brief must not instruct platform preflight")
    return errors

def main() -> int:
    errors: list[str] = []
    handoff = {
        "issue_id": "QUI-ZZ",
        "title": "probe",
        "repo": "workflow-lab",
        "work_mode": "buduj",
        "cmd_id": "abc123",
        "brief_kind": "lab_probe",
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

    # T11: real Autopilot brief — no lab probe, uses repo + /autopilot + AC
    real_ho = {
        "issue_id": "QUI-43",
        "title": "brand-kit martwe zasoby",
        "repo": "dsaas-platform-main",
        "url": "https://linear.app/quietforge/issue/QUI-43",
        "work_mode": "buduj",
        "cmd_id": "real1",
        "brief_kind": "real",
        "ac": ["AC-1: usuń lub podłącz brand-kit/*"],
        "dor_excerpts": {
            "cel": "Usunąć martwe pliki brand-kit albo je wpiąć.",
            "kryteria akceptacji": "- [ ] zero martwych plików albo realny konsument",
        },
    }
    real_text = _brief(real_ho)
    if "conductor-lab-probe" in real_text:
        errors.append("T11 real brief must not mention conductor-lab-probe")
    if "Repo=dsaas-platform-main" not in real_text:
        errors.append(f"T11 real brief must use platform repo, got snippet={real_text[:200]}")
    if "autopilot.md" not in real_text:
        errors.append("T11 real brief must point at .cursor/commands/autopilot.md")
    if "AC-1" not in real_text or "brand-kit" not in real_text:
        errors.append("T11 real brief must include AC / brand-kit")
    if "Repo=workflow-lab" in real_text and "dsaas-platform-main" not in real_text:
        errors.append("T11 must not hardcode workflow-lab over platform")

    lab_text = _brief({**handoff, "brief_kind": "lab_probe"})
    if "conductor-lab-probe.md" not in lab_text:
        errors.append("T11 lab_probe brief must keep probe file instruction")

    if resolve_brief_kind({"id": "QUI-131", "repo": "workflow-lab"}) != "lab_probe":
        errors.append("T11 QUI-131 must resolve lab_probe")
    if resolve_brief_kind({"id": "QUI-43", "repo": "dsaas-platform-main"}) != "real":
        errors.append("T11 QUI-43 must resolve real")

    desc = (
        "## Cel\nUsunąć martwe brand-kit.\n"
        "## Kryteria akceptacji\n- [ ] pliki usunięte albo podłączone\n- [ ] zero dead imports\n"
        "## Ograniczenia\nZero deploy.\n"
    )
    excerpts = extract_dor_excerpts(desc)
    if "cel" not in excerpts or "kryteria akceptacji" not in excerpts:
        errors.append(f"T11 dor excerpts, got {list(excerpts)}")
    ac_list = extract_ac_list(desc, excerpts)
    if len(ac_list) < 2:
        errors.append(f"T11 ac list expect >=2, got {ac_list}")

    create_prompts: list[str] = []

    def fetch_real(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        if method == "POST" and url.rstrip("/").endswith("/agents"):
            if isinstance(payload, dict):
                create_prompts.append(str(((payload.get("prompt") or {}).get("text") or "")))
            return {
                "ok": True,
                "code": 200,
                "body": {
                    "agent": {"id": "bc-real", "url": "https://cursor.com/agents/bc-real"},
                    "run": {"id": "run-r1"},
                },
            }
        if "/archive" in url:
            return {"ok": True, "code": 200, "body": {}}
        return {"ok": True, "code": 200, "body": {}}

    real_created = step(
        handoff=real_ho,
        live=None,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_real),
    )
    if real_created.get("state") != "created":
        errors.append(f"T11 real create, got {real_created}")
    if not create_prompts or "conductor-lab-probe" in create_prompts[0]:
        errors.append(f"T11 create prompt must be real, got {create_prompts[:1]}")
    real_ac = ((real_created.get("live") or {}).get("conductor") or {}).get("ac") or []
    if not real_ac or str(real_ac[0].get("verdict")) != "UNKNOWN":
        errors.append(f"T11 real create AC must UNKNOWN, got {real_ac}")

    # T11b: write_handoff enrich without Linear network
    with __import__("tempfile").TemporaryDirectory() as tmp:
        hd = Path(tmp) / "handoff.json"
        write_handoff(
            {
                "id": "QUI-43",
                "title": "brand-kit",
                "repo": "dsaas-platform-main",
                "labels": ["agent"],
                "description": desc,
            },
            work_mode="buduj",
            cmd_id="cmd-x",
            path=hd,
            fetch_linear=False,
        )
        blob = __import__("json").loads(hd.read_text(encoding="utf-8"))
        if blob.get("brief_kind") != "real":
            errors.append(f"T11b handoff brief_kind, got {blob.get('brief_kind')}")
        if blob.get("repo") != "dsaas-platform-main":
            errors.append(f"T11b repo, got {blob.get('repo')}")
        if not blob.get("ac"):
            errors.append("T11b handoff must carry ac")
        if "description" in blob:
            errors.append("T11b must not persist raw description")
        if "kryteria akceptacji" not in (blob.get("dor_excerpts") or {}):
            errors.append(f"T11b dor_excerpts, got {blob.get('dor_excerpts')}")

    # T13 (QUI-153): ISSUE-JSON v1 in the brief, platform-preflight DoR passes, no context-state.
    errors.extend(_t13_issue_json())

    # T12: real FAIL AC → steer follow-up (no probe text)
    steer_prompts: list[str] = []

    def fetch_steer(method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        if method == "POST" and url.rstrip("/").endswith("/runs"):
            if isinstance(payload, dict):
                steer_prompts.append(str(((payload.get("prompt") or {}).get("text") or "")))
            return {
                "ok": True,
                "code": 200,
                "body": {
                    "agent": {"id": "bc-real", "url": "https://cursor.com/agents/bc-real"},
                    "run": {"id": "run-r2"},
                },
            }
        if "/unarchive" in url or "/stream" in url:
            if "/stream" in url:
                raise RuntimeError("no stream")
            return {"ok": True, "code": 200, "body": {}}
        return {"ok": True, "code": 200, "body": {}}

    live_fail = {
        "issue": "QUI-43",
        "cmd_id": "real1",
        "agent": {
            "agent_id": "bc-real",
            "run_id": "run-r1",
            "run_url": "https://cursor.com/agents/bc-real",
        },
        "conductor": {"ac": [{"id": "AC-1", "verdict": "FAIL"}], "followups_used": 0},
    }
    steered = step(
        handoff=real_ho,
        live=live_fail,
        ops=None,
        key="secret",
        client=CloudClient("secret", fetch=fetch_steer),
    )
    if steered.get("state") != "followup":
        errors.append(f"T12 real FAIL must followup, got {steered}")
    if not steer_prompts or "conductor-lab-probe" in steer_prompts[0]:
        errors.append(f"T12 steer must be real brief, got {steer_prompts[:1]}")
    if steer_prompts and "FOLLOW-UP" not in steer_prompts[0] and "autopilot" not in steer_prompts[0].lower():
        errors.append(f"T12 steer should mention FOLLOW-UP or autopilot, got {steer_prompts[0][:180]}")

    if errors:
        print("FAIL:")
        for item in errors:
            print(" -", item)
        return 1
    print(
        "PASS: hermes_conductor T1-T13 "
        "(early live, timeout, create-on-issue, followup, halt, auth, recover, adapter, real brief, ISSUE-JSON v1)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
