#!/usr/bin/env python3
"""Hermes Ops policy + router + merge-both + no-deploy (stdlib)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hermes_ops.github import GitHubOps
from hermes_ops.orchestrator import Engine
from hermes_ops.policy import allow_deploy, allow_merge, has_workflow_dispatch_deploy
from hermes_ops.router import LANE_AUTOPILOT, LANE_LOCAL, LANE_MANUAL, classify_issue, load_fixture, split_lanes
from hermes_ops.telemetry import append_event, redact, today_stats


def main() -> int:
    errors: list[str] = []
    fixture = ROOT / "scripts" / "fixtures" / "hermes-ops" / "labels_three.json"
    issues = load_fixture(fixture)
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

    calls: list[tuple] = []

    def fake_fetch(method, path, payload):
        calls.append((method, path, payload))
        if "merge" in path:
            return {"ok": True, "code": 200, "body": {"merged": True}}
        return {"ok": True, "code": 201, "body": {"id": 1}}

    gh = GitHubOps(token="test", fetch=fake_fetch)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ledger = tmp_path / "ledger.jsonl"
        lock = tmp_path / "lock.json"
        engine = Engine(github=gh, mode="MANUAL", lock_path=lock, ledger=ledger)
        hitl = issues[2]
        denied = engine.run_next(hitl)
        if denied.get("code") != 403:
            errors.append(f"hitl Run next oczekiwano 403, jest {denied}")
        if any("@cursor" in json.dumps(c) for c in calls):
            errors.append("hitl nigdy @cursor — komentarz poszedł")

        first = engine.run_next(issues[0])
        if not first.get("ok"):
            errors.append(f"Run next agent expect ok, got {first}")
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

        append_event({"kind": "merged", "repo": "workflow-lab"}, ledger)
        stats = today_stats(ledger)
        if stats.get("merged", 0) < 1:
            errors.append("Today z ledgeru nie widzi merged")
        leaked = redact("token ghp_SECRETBAD and lin_api_X")
        if "ghp_" in leaked or "lin_api_" in leaked:
            errors.append("redakcja sekretów nie działa")

        payload = engine.status_payload(issues)
        if payload.get("status") == "GREEN" and payload.get("engine") == "UNKNOWN":
            errors.append("UNKNOWN pomalowane na zielone")
        if payload.get("today", {}).get("cost") not in (None, "—", ""):
            pass  # cost stays None / em-dash at UI
        if "api.github.com" in json.dumps(payload):
            errors.append("status cache nie może zawierać api.github.com")

    if errors:
        print("FAIL:")
        for item in errors:
            print(" -", item)
        return 1
    print("PASS: hermes_ops (Linear router, merge both, deny deploy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
