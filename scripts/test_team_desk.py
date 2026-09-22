#!/usr/bin/env python3
"""QUI-88: team-desk employment request producer + no agent spawn on approve."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from team_desk.employment import (  # noqa: E402
    MAX_RUNTIME_AGENTS,
    EmploymentRequestError,
    approve_employment_card,
    build_employment_card,
    load_process_steps,
    process_step_delta,
    resolve_employment_owners,
)

SAMPLE = {
    "department": "Zespol",
    "position": "People Ops Specialist",
    "duties_kpi": "Maintain hiring pipeline; KPI: time-to-fill ≤45d",
    "technology": "Linear + Kokpit Taca",
}


def main() -> int:
    errors: list[str] = []

    steps = load_process_steps()
    if len(steps) != 5:
        errors.append(f"SSoT steps expect 5, got {len(steps)}")
    if not any(s.get("id") == "owner_acceptance" and s.get("requires_approval") for s in steps):
        errors.append("SSoT missing owner_acceptance approval step")

    delta = process_step_delta()
    if delta["ssot_step_count"] <= delta["plate_step_count"]:
        errors.append(f"E0 delta: SSoT should be longer than plate: {delta}")
    if not delta["ssot_requires_hr_review"]:
        errors.append("E0: SSoT should include hr_review step missing on plate")

    owners = resolve_employment_owners()
    if owners["executive_lead_worker"] != "hr-steward":
        errors.append(f"ROLE-AUDIT-04 owner mapping: {owners}")
    if owners["approval_human_stop"] != "owner":
        errors.append(f"human-stop should be owner: {owners}")

    card = build_employment_card(SAMPLE, proposal_id="PROP-qui88-smoke")
    for field in ("department", "position", "duties_kpi", "technology"):
        if card.get(field) != SAMPLE[field]:
            errors.append(f"card field {field}: {card.get(field)}")
    if card.get("desk") != "team-desk":
        errors.append(f"desk: {card.get('desk')}")
    if card.get("producer") != "hr-steward":
        errors.append(f"producer: {card.get('producer')}")
    if card.get("status") != "pending" or card.get("executed") is not False:
        errors.append(f"pending/executed: {card.get('status')} executed={card.get('executed')}")

    agents = ["cursor", "cron-agent", "phone-loop"]
    if len(agents) > MAX_RUNTIME_AGENTS:
        errors.append("fixture agents exceed cap")
    approved = approve_employment_card(card, agents, approver="owner")
    if approved.get("status") != "approved":
        errors.append(f"approve status: {approved.get('status')}")
    if approved.get("executed") is not False:
        errors.append("approve must not set executed=true (no hire side-effect in lab)")
    if len(agents) > MAX_RUNTIME_AGENTS:
        errors.append("agents after approve exceed cap")

    try:
        build_employment_card({"department": "x"}, proposal_id="bad")
        errors.append("missing fields should raise")
    except EmploymentRequestError as exc:
        if "missing_fields" not in str(exc):
            errors.append(f"unexpected missing_fields error: {exc}")

    try:
        approve_employment_card(card, agents, approver="hr-steward")
        errors.append("hr-steward must not approve owner human-stop card")
    except EmploymentRequestError:
        pass

    bad_pii = dict(SAMPLE, duties_kpi="contact jan@example.com")
    try:
        build_employment_card(bad_pii, proposal_id="pii")
        errors.append("PII email in payload should fail")
    except EmploymentRequestError:
        pass

    if errors:
        print("FAIL:")
        for item in errors:
            print(" -", item)
        return 1
    print(
        "PASS: team_desk "
        + json.dumps(
            {
                "steps": len(steps),
                "delta": delta["ssot_step_count"] - delta["plate_step_count"],
                "agents": len(agents),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
