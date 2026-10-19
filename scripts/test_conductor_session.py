#!/usr/bin/env python3
"""QUI-163: Hermes leads the session S2→S6 (watch → PR → CI → tool D → follow-up → report/HITL).

Offline: fake Cloud API transport, temp files. Stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hermes_conductor.cloud import CloudClient, run_snapshot  # noqa: E402
from hermes_conductor.loop import auto_pr_for, step  # noqa: E402
from hermes_conductor.verdict import ac_from_result, tool_d  # noqa: E402
from hermes_ops.conductor_adapter import (  # noqa: E402
    conductor_phase,
    conductor_pr_number,
    merge_conductor_into_live,
    sanitize_conductor,
)
from phone_loop_github import checks_from_runs  # noqa: E402

PR = "https://github.com/wozniaknorbert95-del/dsaas-platform-main/pull/211"
HANDOFF = {
    "issue_id": "QUI-161",
    "title": "próba",
    "repo": "dsaas-platform-main",
    "work_mode": "testuj",
    "cmd_id": "cmd-161",
    "brief_kind": "real",
    "ac": ["AC-1: run_url na /ops", "AC-2: preflight LANE=HERMES"],
}


class Fake:
    """Cloud API v1 fake: run status / git / result scripted per test."""

    def __init__(self, status: str = "RUNNING", pr_url: str = "", result: str = "", busy: bool = False):
        self.status = status
        self.pr_url = pr_url
        self.result = result
        self.busy = busy
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def __call__(self, method: str, url: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        self.calls.append((method, url, payload))
        if method == "POST" and url.rstrip("/").endswith("/agents"):
            return {
                "ok": True,
                "code": 201,
                "body": {
                    "agent": {"id": "bc-161", "url": "https://cursor.com/agents/bc-161", "latestRunId": "run-1"},
                    "run": {"id": "run-1", "status": "CREATING"},
                },
            }
        if method == "POST" and url.rstrip("/").endswith("/runs"):
            if self.busy:
                return {"ok": False, "code": 409, "body": {"error": "agent_busy"}}
            return {"ok": True, "code": 201, "body": {"run": {"id": "run-2", "agentId": "bc-161", "status": "CREATING"}}}
        if method == "GET" and "/runs/" in url and "/stream" not in url:
            body: dict[str, Any] = {"id": url.rsplit("/", 1)[-1], "agentId": "bc-161", "status": self.status}
            if self.status == "FINISHED":
                body["result"] = self.result
                branch = {"repoUrl": "github.com/wozniaknorbert95-del/dsaas-platform-main", "branch": "cursor/qui-161-x"}
                if self.pr_url:
                    branch["prUrl"] = self.pr_url
                body["git"] = {"branches": [branch]}
            return {"ok": True, "code": 200, "body": body}
        if "/stream" in url:
            return {
                "ok": True,
                "code": 200,
                "body": {"events": [{"callId": "c1", "name": "run_terminal_cmd", "status": "completed"}]},
            }
        return {"ok": True, "code": 200, "body": {}}

    def posts(self, suffix: str) -> list[dict[str, Any] | None]:
        return [p for m, u, p in self.calls if m == "POST" and u.rstrip("/").endswith(suffix)]


def _ops(s4: str = "UNKNOWN", issue: str = "QUI-161", reason: str = "") -> dict[str, Any]:
    return {
        "engine": "RUNNING",
        "reason": "vps_timer",
        "live": {
            "issue": issue,
            "pr_url": PR,
            "steps": [
                {"step": 3, "status": "PASS"},
                {"step": 4, "status": s4, "reason": reason},
            ],
        },
    }


def _aged(live: dict[str, Any]) -> dict[str, Any]:
    """Pretend the last watch was long ago (skip the poll throttle)."""
    out = json.loads(json.dumps(live))
    out["conductor"]["watch_at"] = 0
    return out


def _run(fake: Fake, live: dict[str, Any] | None, ops: dict[str, Any] | None = None, handoff=None) -> dict[str, Any]:
    return step(
        handoff=handoff or HANDOFF,
        live=live,
        ops=ops,
        key="k",
        client=CloudClient("k", fetch=fake),
    )


def main() -> int:
    errors: list[str] = []

    # C1: testuj on the platform → autoCreatePR on; workflow-lab testuj stays off (D-AUTOMERGE).
    if not auto_pr_for("testuj", "dsaas-platform-main") or auto_pr_for("testuj", "workflow-lab"):
        errors.append("C1 auto_pr_for testuj platform/lab")
    if auto_pr_for("ulepszaj", "dsaas-platform-main") or not auto_pr_for("buduj", "workflow-lab"):
        errors.append("C1 auto_pr_for ulepszaj/buduj")
    fake = Fake()
    created = _run(fake, None)
    create_payload = (fake.posts("/agents") or [{}])[0] or {}
    if create_payload.get("autoCreatePR") is not True:
        errors.append(f"C1 testuj platform create must autoCreatePR=true, got {create_payload.get('autoCreatePR')}")
    brief = str((create_payload.get("prompt") or {}).get("text") or "")
    if "WYNIK: PASS|PARTIAL|STOP" not in brief or "AC-2: preflight" not in brief:
        errors.append("C1 brief must ask for AC-n lines + WYNIK and number AC")
    if "nie otwieraj PR ręcznie" not in brief:
        errors.append("C1 testuj brief must say Cursor opens the PR")
    live = created.get("live") or {}
    cond = live.get("conductor") or {}
    if cond.get("phase") != "watching" or not cond.get("events"):
        errors.append(f"C1 create must start phase watching + event, got {cond}")
    lab = Fake()
    _run(lab, None, handoff={**HANDOFF, "repo": "workflow-lab"})
    if ((lab.posts("/agents") or [{}])[0] or {}).get("autoCreatePR") is not False:
        errors.append("C1 workflow-lab testuj must keep autoCreatePR=false")

    # C2: RUNNING → watching, polls GET run, no follow-up.
    fake = Fake(status="RUNNING")
    watching = _run(fake, live)
    wl = watching.get("live") or {}
    if watching.get("state") != "watching" or (wl.get("agent") or {}).get("run_status") != "RUNNING":
        errors.append(f"C2 RUNNING must watch, got {watching.get('state')} {wl.get('agent')}")
    if fake.posts("/runs"):
        errors.append("C2 RUNNING must not follow-up")
    if not any(m == "GET" and "/runs/run-1" in u for m, u, _ in fake.calls):
        errors.append("C2 must GET /runs/{runId}")

    # C3: throttle — immediate re-poll does no network and no write.
    fake = Fake(status="RUNNING")
    again = _run(fake, wl)
    if again.get("wrote") or fake.calls:
        errors.append(f"C3 throttle must not poll, calls={fake.calls}")

    # C4: FINISHED + PR + CI pending → verify (wait), PR recorded (S3), no follow-up.
    fake = Fake(status="FINISHED", pr_url=PR, result="AC-1: PASS — link\nAC-2: PASS — LANE=HERMES\nWYNIK: PASS")
    ver = _run(fake, _aged(wl), ops=_ops("UNKNOWN"))
    vl = ver.get("live") or {}
    if ver.get("state") != "verify" or (vl.get("agent") or {}).get("pr_url") != PR:
        errors.append(f"C4 FINISHED + CI pending must verify with PR, got {ver.get('state')} {vl.get('agent')}")
    if fake.posts("/runs"):
        errors.append("C4 CI pending must not follow-up")
    if not any("S3 PR" in str(e.get("text")) for e in (vl.get("conductor") or {}).get("events") or []):
        errors.append("C4 events must log S3 PR")

    # C5: CI green + AC PASS lines → D PASS, phase done (final).
    fake = Fake(status="FINISHED", pr_url=PR, result="AC-1: PASS — link\nAC-2: PASS — LANE=HERMES\nWYNIK: PASS")
    done = _run(fake, _aged(vl), ops=_ops("PASS"))
    dc = (done.get("live") or {}).get("conductor") or {}
    if done.get("state") != "done" or dc.get("phase") != "done" or dc.get("verdict") != "PASS":
        errors.append(f"C5 green CI + AC PASS must D PASS done, got {done.get('state')} {dc}")
    if "D PASS" not in str(dc.get("report_pl")):
        errors.append(f"C5 report must lead with verdict, got {dc.get('report_pl')}")
    after = _run(Fake(), _aged(done.get("live") or {}), ops=_ops("PASS"))
    if after.get("wrote") or after.get("state") != "unchanged":
        errors.append("C5 final phase must not poll again")

    # C6: agent says PARTIAL → D FAIL → follow-up on the SAME agentId, counter 1, back to watching.
    fake = Fake(status="FINISHED", pr_url=PR, result="Zrobione częściowo.\nWYNIK: PARTIAL")
    fol = _run(fake, _aged(vl), ops=_ops("PASS"))
    fl = fol.get("live") or {}
    fc = fl.get("conductor") or {}
    posts = [u for m, u, _ in fake.calls if m == "POST" and u.rstrip("/").endswith("/runs")]
    if fol.get("state") != "followup" or posts != ["https://api.cursor.com/v1/agents/bc-161/runs"]:
        errors.append(f"C6 PARTIAL must follow-up on bc-161, got {fol.get('state')} {posts}")
    if fc.get("followups_used") != 1 or fc.get("phase") != "watching" or (fl.get("agent") or {}).get("run_id") != "run-2":
        errors.append(f"C6 follow-up bookkeeping, got {fc} {fl.get('agent')}")
    text = str(((fake.posts("/runs") or [{}])[0] or {}).get("prompt", {}).get("text") or "")
    if "FOLLOW-UP" not in text or "PARTIAL" not in text:
        errors.append(f"C6 steer must name the D reason, got {text[:160]}")
    if any(x.get("verdict") == "PASS" for x in fc.get("ac") or []):
        errors.append("C6 AC after follow-up must be UNKNOWN, never painted PASS")

    # C7: follow-up budget exhausted → HITL, no POST, no refuse (re-Start stays possible).
    os.environ["OPS_CONDUCTOR_MAX_FOLLOWUPS"] = "1"
    fake = Fake(status="FINISHED", pr_url=PR, result="WYNIK: PARTIAL")
    hitl = _run(fake, _aged(fl), ops=_ops("PASS"))
    hl = hitl.get("live") or {}
    os.environ.pop("OPS_CONDUCTOR_MAX_FOLLOWUPS", None)
    if hitl.get("state") != "hitl" or (hl.get("conductor") or {}).get("phase") != "hitl":
        errors.append(f"C7 limit must HITL, got {hitl.get('state')}")
    if fake.posts("/runs") or hl.get("refuse"):
        errors.append("C7 HITL must not follow-up nor set refuse")

    # C8: FINISHED without PR (auto PR on) → D FAIL "brak PR" → follow-up steer.
    fake = Fake(status="FINISHED", pr_url="", result="AC-1: PASS\nAC-2: PASS\nWYNIK: PASS")
    nopr = _run(fake, _aged(wl), ops=None)
    steer = str(((fake.posts("/runs") or [{}])[0] or {}).get("prompt", {}).get("text") or "")
    if nopr.get("state") != "followup" or "Brak PR" not in steer:
        errors.append(f"C8 no PR must follow-up with 'Brak PR', got {nopr.get('state')} {steer[:120]}")

    # C9: CI red (S4 FAIL) → follow-up with the check reason.
    fake = Fake(status="FINISHED", pr_url=PR, result="AC-1: PASS\nAC-2: PASS\nWYNIK: PASS")
    red = _run(fake, _aged(wl), ops=_ops("FAIL", reason="CI not fully green"))
    steer = str(((fake.posts("/runs") or [{}])[0] or {}).get("prompt", {}).get("text") or "")
    if red.get("state") != "followup" or "CI" not in steer:
        errors.append(f"C9 S4 FAIL must follow-up, got {red.get('state')}")

    # C10: STOP-LINEAR in the reply → HITL, no follow-up.
    fake = Fake(status="FINISHED", pr_url="", result="STOP-LINEAR: brak JSON")
    stop = _run(fake, _aged(wl), ops=None)
    if stop.get("state") != "hitl" or fake.posts("/runs"):
        errors.append(f"C10 STOP must HITL without follow-up, got {stop.get('state')}")

    # C11: CI never returns → HITL after CONDUCTOR_VERIFY_SEC.
    os.environ["CONDUCTOR_VERIFY_SEC"] = "60"
    old = _aged(vl)
    old["conductor"]["finished_at"] = time.time() - 120
    late = _run(Fake(status="FINISHED", pr_url=PR, result="WYNIK: PASS"), old, ops=_ops("UNKNOWN"))
    os.environ.pop("CONDUCTOR_VERIFY_SEC", None)
    if late.get("state") != "hitl" or "CI nie wróciło" not in str((late.get("live") or {}).get("conductor", {}).get("d")):
        errors.append(f"C11 verify timeout must HITL, got {late.get('state')}")

    # C12: follow-up 409 busy → stay in verify, no refuse.
    fake = Fake(status="FINISHED", pr_url=PR, result="WYNIK: PARTIAL", busy=True)
    busy = _run(fake, _aged(vl), ops=_ops("PASS"))
    if busy.get("state") != "verify" or (busy.get("live") or {}).get("refuse"):
        errors.append(f"C12 busy follow-up must retry later, got {busy.get('state')}")

    # C13: tool D honesty — CI green but no per-AC evidence = UNKNOWN, never PASS.
    res = tool_d(
        run={"status": "FINISHED", "pr_url": PR, "result": "Gotowe."},
        ops_live=_ops("PASS")["live"],
        issue="QUI-161",
        ac_ids=["AC-1"],
        auto_pr=True,
    )
    if res["verdict"] != "UNKNOWN" or res["action"] != "done":
        errors.append(f"C13 no AC evidence must be UNKNOWN done, got {res}")
    foreign = tool_d(
        run={"status": "FINISHED", "pr_url": PR, "result": "AC-1: PASS"},
        ops_live=_ops("PASS", issue="QUI-999")["live"],
        issue="QUI-161",
        ac_ids=["AC-1"],
        auto_pr=True,
    )
    if foreign["action"] != "wait":
        errors.append(f"C13 foreign ops live must not count as CI evidence, got {foreign}")
    if ac_from_result(["AC-1", "AC-10"], "AC-10: FAIL\nAC-1: PASS") != [
        {"id": "AC-1", "verdict": "PASS"},
        {"id": "AC-10", "verdict": "FAIL"},
    ]:
        errors.append("C13 AC-1 must not match AC-10")

    # C14: legacy stream enrich never paints UNKNOWN as PASS.
    legacy = {
        "issue": "QUI-161",
        "cmd_id": "cmd-161",
        "agent": {"agent_id": "bc-161", "run_id": "run-1", "run_url": "https://cursor.com/agents/bc-161"},
        "conductor": {"ac": [{"id": "AC-1", "verdict": "UNKNOWN"}]},
    }
    enr = _run(Fake(), legacy)
    eac = ((enr.get("live") or {}).get("conductor") or {}).get("ac") or []
    if enr.get("state") != "enriched" or any(x.get("verdict") == "PASS" for x in eac):
        errors.append(f"C14 stream UNKNOWN must stay UNKNOWN, got {enr.get('state')} {eac}")

    # C15: run_snapshot parses v1 run; garbage → {}.
    snap = run_snapshot(Fake(status="FINISHED", pr_url=PR, result="x")("GET", "https://api.cursor.com/v1/agents/bc/runs/r", None))
    if snap.get("status") != "FINISHED" or snap.get("pr_url") != PR or snap.get("branch") != "cursor/qui-161-x":
        errors.append(f"C15 run_snapshot, got {snap}")
    if run_snapshot({"ok": True, "body": {"agents": []}}) or run_snapshot({"ok": False}):
        errors.append("C15 unknown shape must be {}")

    # C16: adapter keeps phase/verdict/events, Dziennik gets conductor events, PR number parsed.
    cond = sanitize_conductor({"phase": "verify", "verdict": "UNKNOWN", "d": ["S4 czekam"], "events": [{"at": "t", "text": "run FINISHED"}]})
    if cond.get("phase") != "verify" or cond.get("events") != [{"at": "t", "text": "run FINISHED"}]:
        errors.append(f"C16 sanitize_conductor, got {cond}")
    merged = merge_conductor_into_live({"issue": "QUI-161", "steps": []}, vl, work_mode="testuj") or {}
    if not any("Hermes" in str(r.get("text")) for r in merged.get("recent") or []):
        errors.append(f"C16 recent must carry conductor events, got {merged.get('recent')}")
    if (merged.get("agent") or {}).get("pr_url") != PR:
        errors.append("C16 merge must carry agent.pr_url")
    if conductor_pr_number(vl, owner="wozniaknorbert95-del", repo="dsaas-platform-main", issue_id="QUI-161") != 211:
        errors.append("C16 conductor_pr_number")
    if conductor_pr_number(vl, owner="wozniaknorbert95-del", repo="workflow-lab", issue_id="QUI-161"):
        errors.append("C16 PR of another repo must be ignored")
    if conductor_phase(vl, "QUI-999"):
        errors.append("C16 foreign issue phase must be ''")

    # C17: S4 platform `gates`; in progress = pending (UNKNOWN), no runs = {}.
    if checks_from_runs([{"name": "gates", "conclusion": "success"}]).get("validate") != "success":
        errors.append("C17 gates success must be validate success")
    pend = checks_from_runs([{"name": "gates", "conclusion": None}, {"name": "gitleaks", "conclusion": "success"}])
    if pend.get("validate") != "pending":
        errors.append(f"C17 gates in progress must be pending, got {pend}")
    if checks_from_runs([]):
        errors.append("C17 no runs must be {}")
    spec = importlib.util.spec_from_file_location("pls", ROOT / "scripts" / "phone-loop-status.py")
    pls = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(pls)
    ev = pls.evaluate_from_fixture({"linear": {}, "github": {}, "checks": pend, "review": {}, "merge": {}})
    s4 = next((s for s in ev.get("steps") or [] if s.get("step") == 4), {})
    if s4.get("status") != "UNKNOWN":
        errors.append(f"C17 pending checks must be S4 UNKNOWN, got {s4}")

    # C18: tick — PR from conductor → lock.pr; active conductor keeps slot past TTL; final phase frees it.
    from hermes_ops import orchestrator as orch
    from hermes_ops.github import GitHubOps

    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        os.environ["ACADEMY_DATA_DIR"] = tmp
        live_path = data / "hermes-conductor-live.json"
        eng = orch.Engine(
            github=GitHubOps(token="", fetch=lambda m, p, b: {"ok": False, "code": 404}),
            mode="MANUAL",
            lock_path=data / "lock.json",
            ledger=data / "ledger.jsonl",
            state_path=data / "state.json",
            github_read_token="",
        )
        eng.engine_state = "RUNNING"
        eng._write_lock(
            {"issue_id": "QUI-161", "repo": "dsaas-platform-main", "started": time.time() - 3600, "work_mode": "testuj"}
        )
        fresh = dict(vl)
        fresh["at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        live_path.write_text(json.dumps(fresh), encoding="utf-8")
        if not eng.busy():
            errors.append("C18 active conductor (verify, fresh) must keep slot past OPS_TTL_MIN")
        eng.refresh_live([])
        if int(eng._lock().get("pr") or 0) != 211:
            errors.append(f"C18 lock.pr from conductor prUrl, got {eng._lock()}")
        stale = dict(fresh)
        stale["at"] = "2020-01-01T00:00:00Z"
        live_path.write_text(json.dumps(stale), encoding="utf-8")
        if eng.busy():
            errors.append("C18 stale conductor heartbeat must let TTL free the slot")
        eng.engine_state = "RUNNING"
        eng._write_lock({"issue_id": "QUI-161", "repo": "dsaas-platform-main", "started": time.time(), "pr": 211})
        final = dict(done.get("live") or {})
        final["at"] = fresh["at"]
        live_path.write_text(json.dumps(final), encoding="utf-8")
        eng.refresh_live([])
        if eng._lock() or eng.engine_state != "PAUSED":
            errors.append(f"C18 final phase must free slot, lock={eng._lock()} engine={eng.engine_state}")
        if ((eng.live or {}).get("conductor") or {}).get("verdict") != "PASS":
            errors.append("C18 live snapshot must keep D verdict after release")
        ledger = (data / "ledger.jsonl").read_text(encoding="utf-8") if (data / "ledger.jsonl").exists() else ""
        if "conductor_done" not in ledger:
            errors.append("C18 ledger must record conductor_done")
        os.environ.pop("ACADEMY_DATA_DIR", None)

    if errors:
        print("FAIL:")
        for item in errors:
            print(" -", item)
        return 1
    print("PASS: conductor session S2→S6 C1-C18 (watch, PR, CI, tool D, follow-up, HITL, slot release, gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
