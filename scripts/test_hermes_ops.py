#!/usr/bin/env python3
"""Hermes Ops policy + router + merge-both + no-deploy + live S1–S6 (stdlib)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hermes_ops.github import GitHubOps
from hermes_ops.live_enrich import build_approval, enrich_live
from hermes_ops.orchestrator import Engine
from hermes_ops.policy import allow_deploy, allow_merge, allow_run_all, has_workflow_dispatch_deploy
from hermes_ops.router import LANE_AUTOPILOT, LANE_LOCAL, LANE_MANUAL, classify_issue, load_fixture, split_lanes
from hermes_ops.ops_token_validate import validate_github_ops_write, validate_linear_ops_read
from hermes_ops.telemetry import append_event, redact, run_all_enabled, today_stats
from hermes_ops.live_enrich import _load_phone_loop


def main() -> int:
    errors: list[str] = []
    ok, reason = validate_github_ops_write("gho_OAUTH")
    if ok or reason != "reject_gho_oauth":
        errors.append(f"anty-gho_: expect reject, got {ok} {reason}")
    ok, _ = validate_github_ops_write("github_pat_testtokenvaluexx")
    if not ok:
        errors.append("github_pat_ powinien przejść walidację kształtu")
    ok, _ = validate_linear_ops_read("lin_api_testtokenvaluexx")
    if not ok:
        errors.append("lin_api_ powinien przejść walidację kształtu")
    fixture = ROOT / "scripts" / "fixtures" / "hermes-ops" / "labels_three.json"
    issues = load_fixture(fixture)
    load_phone_fixture = _load_phone_loop().load_fixture
    if len(issues) != 3:
        errors.append("fixture 3 etykiet != 3 issues")

    auto = split_lanes(issues, mode="AUTOPILOT")
    if not auto[LANE_AUTOPILOT]:
        errors.append("agent bez HITL powinien być autopilot")
    if not auto[LANE_LOCAL]:
        errors.append("hitl:approval-required powinien być local")
    if classify_issue(issues[2]) != LANE_LOCAL:
        errors.append("HITL nie jest tor lokalny")
    if classify_issue(issues[0], mode="MANUAL") != LANE_MANUAL:
        errors.append("MANUAL + agent = tor manual (Run next z telefonu)")

    ok, code, _ = allow_merge("workflow-lab", True, {"labels": ["agent"]})
    if not ok or code != 200:
        errors.append(f"merge lab na zielonym PR oczekiwano 200, jest {code}")
    ok, code, _ = allow_merge("dsaas-platform-main", True, {"labels": ["agent"]})
    if not ok or code != 200:
        errors.append(f"merge dsaas na zielonym PR oczekiwano 200, jest {code}")
    ok, code, reason = allow_merge("dsaas-platform-main", True, {"labels": ["hitl:approval-required"]})
    if ok or code != 403 or reason != "LOCAL_ONLY":
        errors.append(f"HITL merge powinien być 403 LOCAL_ONLY, jest {code} {reason}")
    if allow_deploy("workflow_dispatch")[0] or has_workflow_dispatch_deploy():
        errors.append("workflow dispatch deploy nie może istnieć w orchestratorze")

    ok, code, reason = allow_run_all(False)
    if ok or code != 403:
        errors.append("Run all default OFF — expect 403")

    calls: list[tuple] = []

    def fake_fetch(method, path, payload):
        calls.append((method, path, payload))
        if method == "GET" and "search/issues" in path:
            return {"ok": True, "code": 200, "body": {"items": []}}
        if method == "POST" and path.rstrip("/").endswith("/issues") and "/comments" not in path:
            return {
                "ok": True,
                "code": 201,
                "body": {"number": 501, "html_url": "https://github.com/wozniaknorbert95-del/workflow-lab/issues/501"},
            }
        if "merge" in path:
            return {"ok": True, "code": 200, "body": {"merged": True}}
        return {"ok": True, "code": 201, "body": {"id": 1, "html_url": "https://github.com/x/y/issues/1"}}

    gh = GitHubOps(token="test", fetch=fake_fetch)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ledger = tmp_path / "ledger.jsonl"
        lock = tmp_path / "lock.json"
        engine = Engine(
            github=gh,
            mode="MANUAL",
            lock_path=lock,
            ledger=ledger,
            state_path=tmp_path / "state-main.json",
            github_read_token="",
        )
        hitl = issues[2]
        denied = engine.run_next(hitl)
        if denied.get("code") != 403:
            errors.append(f"hitl Run next oczekiwano 403, jest {denied}")
        if any("@cursor" in json.dumps(c) for c in calls):
            errors.append("hitl nigdy @cursor — komentarz poszedł")

        phone = load_phone_fixture("happy")
        first = engine.run_next(issues[0], fixture=phone)
        if not first.get("ok"):
            errors.append(f"Run next agent expect ok, got {first}")
        if not engine.live or not engine.live.get("steps"):
            errors.append("live musi mieć steps S1–S6 z phone-loop")
        elif engine.live.get("progress", {}).get("total") != 6:
            errors.append(f"progress total=6, jest {engine.live.get('progress')}")
        if engine.live and "api.github.com" in json.dumps(engine.live):
            errors.append("live nie może zawierać api.github.com")

        second = engine.run_next(issues[1])
        if second.get("code") != 409:
            errors.append(f"1 concurrent — drugie Run next oczekiwano 409, jest {second}")
        same = engine.run_next(issues[0])
        if same.get("code") != 409:
            errors.append(f"idempotencja tego samego issue oczekiwano 409, jest {same}")

        engine._clear_lock()
        lab_merge = engine.maybe_merge("workflow-lab", 1, True, issues[0])
        plat_merge = engine.maybe_merge("dsaas-platform-main", 2, True, issues[1])
        if not lab_merge.get("ok") or not plat_merge.get("ok"):
            errors.append(f"auto-merge obu repo: lab={lab_merge} dsaas={plat_merge}")
        dispatch = gh.workflow_dispatch("prod")
        if dispatch.get("ok") or dispatch.get("exists"):
            errors.append("dispatch deploy nie jest deny")

        engine.mode = "AUTOPILOT"
        engine.engine_state = "RUNNING"
        engine._clear_lock()
        tick = engine.tick(issues)
        if not tick.get("ok") and tick.get("code") == 403:
            errors.append(f"autopilot tick: {tick}")

        append_event(
            {
                "kind": "merged",
                "repo": "workflow-lab",
                "issue": "QUI-201",
                "agent": "cursor",
                "input_tokens": None,
                "output_tokens": None,
                "cost": None,
                "result": "merged",
            },
            ledger,
        )
        stats = today_stats(ledger)
        if stats.get("merged", 0) < 1:
            errors.append("Today z ledgeru nie widzi merged")
        if stats.get("tokens") is not None or stats.get("cost") is not None:
            # null stays null when no numeric source
            if stats.get("cost") == 0 or stats.get("tokens") == 0:
                errors.append("cost/tokens nie mogą być fałszywym zerem bez źródła")
        leaked = redact("token ghp_SECRETBAD and lin_api_X")
        if "ghp_" in leaked or "lin_api_" in leaked:
            errors.append("redakcja sekretów nie działa")

        payload = engine.status_payload(issues)
        if payload.get("status") == "GREEN" and payload.get("engine") == "UNKNOWN":
            errors.append("UNKNOWN pomalowane na zielone")
        if "api.github.com" in json.dumps(payload):
            errors.append("status cache nie może zawierać api.github.com")
        if payload.get("worker") != "cursor":
            errors.append("worker v1 = cursor")
        if payload.get("run_all_enabled") is not False and not run_all_enabled():
            errors.append("run_all_enabled default false")

        from hermes_ops.linear import LinearOps, normalize_issue

        mapped = normalize_issue(
            {
                "identifier": "QUI-210",
                "title": "from project",
                "url": "https://linear.app/quietforge/issue/QUI-210",
                "state": {"name": "Ready"},
                "labels": {"nodes": [{"name": "agent"}]},
                "project": {"name": "dsaas-platform-main"},
                "attachments": {
                    "nodes": [{"url": "https://github.com/wozniaknorbert95-del/dsaas-platform-main/pull/9"}]
                },
            }
        )
        if mapped.get("repo") != "dsaas-platform-main":
            errors.append(f"project name ma mapować repo, jest {mapped.get('repo')}")
        if mapped.get("github_number") != 9:
            errors.append(f"attachment pull number oczekiwano 9, jest {mapped.get('github_number')}")

        empty = LinearOps(token="", queue_file=tmp_path / "no-queue.json")
        if empty.list_queue() or empty.last_error != "missing_LINEAR_OPS_READ":
            errors.append(f"brak tokenu Linear ma być UNKNOWN, jest {empty.last_error} {empty.list_queue()}")

        queue_src = ROOT / "scripts" / "fixtures" / "hermes-ops" / "linear-queue-open.json"
        from_file = LinearOps(token="", queue_file=queue_src)
        filed = from_file.list_queue()
        if from_file.last_error or from_file.source != "queue_file" or len(filed) < 5:
            errors.append(f"queue_file fallback broken: err={from_file.last_error} src={from_file.source} n={len(filed)}")
        if not any(i.get("id") == "QUI-61" for i in filed):
            errors.append("queue_file ma zawierać QUI-61")

        from hermes_ops.notify import build_payload as push_payload, should_alert
        from hermes_ops.router import active_agents_from, attach_lane_progress

        if not should_alert(mode="SUPERVISED", lanes={"local": [{"id": "QUI-40"}], "autopilot": [], "manual": []}, live=None, engine="PAUSED"):
            errors.append("SUPERVISED+HITL ma alertować push")
        if should_alert(mode="MANUAL", lanes={"local": [{"id": "QUI-40"}], "autopilot": [], "manual": []}, live=None, engine="PAUSED"):
            errors.append("MANUAL nie powinien auto-push HITL")
        pp = push_payload(lanes={"local": [{"id": "QUI-40", "title": "hitl"}], "autopilot": [], "manual": []}, live=None)
        if "HITL" not in pp.get("title", ""):
            errors.append(f"push title HITL: {pp}")

        state_file = tmp_path / "state.json"
        paused = Engine(
            github=gh,
            mode="AUTOPILOT",
            lock_path=tmp_path / "lock2.json",
            ledger=ledger,
            state_path=state_file,
        )
        paused.pause()
        restored = Engine(
            github=gh,
            mode="AUTOPILOT",
            lock_path=tmp_path / "lock2.json",
            ledger=ledger,
            state_path=state_file,
        )
        restored.load_state()
        if restored.engine_state != "PAUSED":
            errors.append(f"Pause ma przetrwać tick, jest {restored.engine_state}")
        picked = paused.pick_next(issues, "")
        if not picked or picked.get("id") != "QUI-201":
            errors.append(f"pick_next MANUAL/pierwszy agent: {picked}")

        # F3: take_over + SUPERVISED
        take = Engine(
            github=gh,
            mode="SUPERVISED",
            lock_path=tmp_path / "lock3.json",
            ledger=ledger,
            state_path=tmp_path / "state3.json",
        )
        take.engine_state = "RUNNING"
        take.live = {"issue": "QUI-201", "step": 2, "title": "agent", "progress": {"bar": "██░░░░", "passed": 2, "total": 6}}
        tot = take.take_over(issues[0])
        if tot.get("engine") != "PAUSED" or take.engine_state != "PAUSED":
            errors.append(f"take_over ma Pause, jest {tot}")
        if take.live and take.live.get("action") != "take_over":
            errors.append("take_over live.action")

        take.live = {
            "issue": "QUI-201",
            "title": "agent",
            "step": 2,
            "status": "RUNNING",
            "progress": {"bar": "██░░░░", "passed": 2, "total": 6},
            "worker": "cursor",
        }
        take.engine_state = "RUNNING"
        take._write_lock({"issue_id": "QUI-201", "started": 1, "repo": "workflow-lab"})
        st = take.status_payload(issues)
        if not st.get("active_agents"):
            errors.append("active_agents empty while RUNNING live")
        lane_prog = attach_lane_progress(st.get("lanes") or {}, take.live)
        auto_rows = lane_prog.get("autopilot") or []
        if auto_rows and str(auto_rows[0].get("id")) == "QUI-201" and not auto_rows[0].get("progress"):
            errors.append("lane progress not attached to live issue")
        agents = active_agents_from(take.live, take._lock(), "cursor")
        if not agents or agents[0].get("id") != "QUI-201":
            errors.append(f"active_agents_from: {agents}")

        mode_ok = take.set_mode("SUPERVISED")
        if not mode_ok.get("ok") or take.mode != "SUPERVISED":
            errors.append(f"set_mode SUPERVISED: {mode_ok}")
        bad = take.set_mode("HACK")
        if bad.get("ok"):
            errors.append("bad mode should fail")

        os.environ.pop("OPS_RUN_ALL", None)
        # reload module flag is process-start; call policy directly
        ra = take.run_all(issues)
        if ra.get("code") != 403:
            errors.append(f"run_all bez flagi expect 403, jest {ra}")

        live_ci = enrich_live(issue=issues[0], fixture=phone, worker="cursor")
        cards = build_approval({"local": [issues[2]], "autopilot": [], "manual": []}, live_ci)
        kinds = {c.get("kind") for c in cards}
        if "hitl_local" not in kinds:
            errors.append("approval ma kartę hitl_local")
        # happy fixture is fully merged PASS step 6 — ci_green_waiting only when checks PASS but not merged
        mid = dict(phone)
        mid["merge"] = {"squash_on_main": False}
        mid["review"] = {"approved": False}
        live_wait = enrich_live(issue=issues[0], fixture=mid, worker="cursor")
        cards2 = build_approval({"local": [], "autopilot": [], "manual": []}, live_wait)
        if not any(c.get("kind") == "ci_green_waiting" for c in cards2):
            # S4 PASS but S6 not — should show waiting
            if str((live_wait.get("checks") or {}).get("overall") or "").upper() == "PASS":
                errors.append(f"approval ci_green_waiting missing: {cards2} live={live_wait.get('status')}")

        # QUI-70: ack/refuse + ensure_cursor when github_number missing
        from hermes_ops.dispatch_ack import make_ack, write_refuse, refuse_reason_from_result

        ack = make_ack({"id": "abc123", "action": "start"})
        if not ack or ack.get("cmd_id") != "abc123":
            errors.append(f"make_ack: {ack}")
        refuse_path = tmp_path / "refuse-abc123.json"
        blob = write_refuse({"id": "abc123", "action": "start"}, "missing_GITHUB_OPS_WRITE", directory=tmp_path)
        if blob.get("reason") != "missing_GITHUB_OPS_WRITE" or not refuse_path.is_file():
            errors.append(f"write_refuse: {blob} exists={refuse_path.is_file()}")
        if refuse_reason_from_result({"ok": False, "code": 429, "error": "daily_cap"}) != "cap_OPS_MAX_RUNS_PER_DAY":
            errors.append("refuse_reason daily_cap mapping")

        bare = {"id": "QUI-ZZ", "title": "no gh yet", "repo": "workflow-lab", "labels": ["agent"]}
        engine_e4 = Engine(
            github=gh,
            mode="MANUAL",
            lock_path=tmp_path / "lock-e4.json",
            ledger=tmp_path / "ledger-e4.jsonl",
            state_path=tmp_path / "state-e4.json",
            github_read_token="",
        )
        trig = engine_e4.run_next(bare, fixture=phone)
        if not trig.get("ok"):
            errors.append(f"E4 ensure_cursor without github_number: {trig}")
        else:
            created_calls = [c for c in calls if c[0] == "POST" and str(c[1]).rstrip("/").endswith("/issues")]
            comment_calls = [c for c in calls if "comments" in str(c[1])]
            if not created_calls:
                errors.append("E4 expect create issue when github_number missing")
            if not any("@cursor" in json.dumps(c[2] or {}) for c in comment_calls):
                errors.append("E4 @cursor comment body missing")
            lock_e4 = json.loads((tmp_path / "lock-e4.json").read_text(encoding="utf-8"))
            if int(lock_e4.get("github_issue") or 0) != 501 or lock_e4.get("pr"):
                errors.append(f"E4 lock tracking≠PR: {lock_e4}")
            # fixture path may still show a demo PR — real no-PR path covered by fallback test below.
        # E4/E5: dsaas create 403 → fallback workflow-lab; never invent dsaas PR URL.
        calls_fb: list[tuple] = []

        def fetch_fallback(method, path, payload):
            calls_fb.append((method, path, payload))
            if method == "POST" and "/dsaas-platform-main/issues" in path and "/comments" not in path:
                return {"ok": False, "code": 403, "error": "http_403", "detail": "Resource not accessible"}
            if method == "POST" and path.rstrip("/").endswith("/issues") and "/comments" not in path:
                return {
                    "ok": True,
                    "code": 201,
                    "body": {
                        "number": 77,
                        "html_url": "https://github.com/wozniaknorbert95-del/workflow-lab/issues/77",
                    },
                }
            if "comments" in path:
                return {"ok": False, "code": 403, "error": "http_403"}
            return {"ok": True, "code": 200, "body": {}}

        gh_fb = GitHubOps(token="test", fetch=fetch_fallback)
        engine_fb = Engine(
            github=gh_fb,
            mode="MANUAL",
            lock_path=tmp_path / "lock-fb.json",
            ledger=tmp_path / "ledger-fb.jsonl",
            state_path=tmp_path / "state-fb.json",
            github_read_token="tok",  # would wrongly fetch PR if we pass issue# as pr
        )
        dsaas_bare = {
            "id": "QUI-89",
            "title": "discover",
            "repo": "dsaas-platform-main",
            "labels": ["agent"],
            "github_number": 0,
        }
        out_fb = engine_fb.run_next(dsaas_bare)
        if not out_fb.get("ok"):
            errors.append(f"E4 fallback create expect ok: {out_fb}")
        else:
            live_fb = engine_fb.live or {}
            if live_fb.get("repo") != "workflow-lab":
                errors.append(f"E4 fallback repo expect workflow-lab, got {live_fb.get('repo')}")
            if live_fb.get("pr_url") or live_fb.get("pr_number"):
                errors.append(f"E4 fallback must not invent PR: {live_fb.get('pr_url')}")
            if int(live_fb.get("github_issue") or 0) != 77:
                errors.append(f"E4 fallback github_issue: {live_fb.get('github_issue')}")
            if "dsaas-platform-main/pull" in json.dumps(live_fb):
                errors.append("E4 fallback must never point at dsaas pull from tracking issue#")
            lock_fb = json.loads((tmp_path / "lock-fb.json").read_text(encoding="utf-8"))
            if lock_fb.get("repo") != "workflow-lab" or lock_fb.get("pr"):
                errors.append(f"E4 fallback lock: {lock_fb}")

    if errors:
        print("FAIL:")
        for item in errors:
            print(" -", item)
        return 1
    print("PASS: hermes_ops (Linear router, merge both, live S1-S6, take_over, deny deploy, QUI-70 ack)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
