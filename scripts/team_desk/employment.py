"""Produce team-desk employment request cards from SSoT steps (QUI-88 / ROLE-AUDIT-13)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAX_RUNTIME_AGENTS = 3
DESK_ID = "team-desk"
CARD_KIND = "employment_request"
PRODUCER_WORKER = "hr-steward"
APPROVAL_HUMAN_STOP = "owner"

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "qui-88"
SSOT_FIXTURE = FIXTURES / "zespol-zatrudnienie-ssot-5steps.json"
PLATE_FIXTURE = FIXTURES / "zespol-zatrudnienie-base-plate-short.json"

REQUIRED_REQUEST_FIELDS = ("department", "position", "duties_kpi", "technology")


class EmploymentRequestError(ValueError):
    """Invalid employment request or approval."""


def load_process_steps(path: Path | None = None) -> list[dict[str, Any]]:
    data = json.loads((path or SSOT_FIXTURE).read_text(encoding="utf-8"))
    steps = list(data.get("steps") or [])
    steps.sort(key=lambda s: int(s.get("order") or 0))
    return steps


def process_step_delta(
    ssot_path: Path | None = None,
    plate_path: Path | None = None,
) -> dict[str, Any]:
    ssot = load_process_steps(ssot_path)
    plate = load_process_steps(plate_path or PLATE_FIXTURE)
    ssot_ids = [s.get("id") for s in ssot]
    plate_ids = [s.get("id") for s in plate]
    return {
        "ssot_step_count": len(ssot),
        "plate_step_count": len(plate),
        "ssot_only_ids": [i for i in ssot_ids if i not in plate_ids],
        "plate_only_ids": [i for i in plate_ids if i not in ssot_ids],
        "ssot_requires_hr_review": any(s.get("id") == "hr_review" for s in ssot),
        "plate_requires_hr_review": any(s.get("id") == "hr_review" for s in plate),
    }


def resolve_employment_owners() -> dict[str, str]:
    """QUI-79: executive lead = hr-steward; Commander = human-stop on approval."""
    return {
        "executive_lead_worker": PRODUCER_WORKER,
        "approval_human_stop": APPROVAL_HUMAN_STOP,
        "producer": PRODUCER_WORKER,
    }


def _validate_request_payload(payload: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_REQUEST_FIELDS if not str(payload.get(k) or "").strip()]
    if missing:
        raise EmploymentRequestError(f"missing_fields:{','.join(missing)}")
    for key in REQUIRED_REQUEST_FIELDS:
        val = str(payload[key])
        if any(token in val.lower() for token in ("@", "nip", "pesel", "phone")):
            raise EmploymentRequestError("pii_forbidden_in_request")


def build_employment_card(
    payload: dict[str, Any],
    *,
    proposal_id: str,
    tenant_id: str = "quietforge",
    ssot_path: Path | None = None,
) -> dict[str, Any]:
    """Build a Taca-ready team-desk card (pending owner approval)."""
    _validate_request_payload(payload)
    steps = load_process_steps(ssot_path)
    if len(steps) != 5:
        raise EmploymentRequestError(f"expected_5_ssot_steps,got={len(steps)}")
    owners = resolve_employment_owners()
    return {
        "proposal_id": proposal_id,
        "tenant_id": tenant_id,
        "desk": DESK_ID,
        "kind": CARD_KIND,
        "producer": owners["producer"],
        "approval_owner": owners["approval_human_stop"],
        "executive_lead_worker": owners["executive_lead_worker"],
        "status": "pending",
        "executed": False,
        "labels": ["hitl:approval-required"],
        "department": str(payload["department"]).strip(),
        "position": str(payload["position"]).strip(),
        "duties_kpi": str(payload["duties_kpi"]).strip(),
        "technology": str(payload["technology"]).strip(),
        "process_id": "zespol.zatrudnienie",
        "process_steps": steps,
        "spawn_runtime_agent": False,
    }


def approve_employment_card(
    card: dict[str, Any],
    runtime_agents: list[str],
    *,
    approver: str = APPROVAL_HUMAN_STOP,
) -> dict[str, Any]:
    """Owner approval closes the card without spawning a runtime agent."""
    if card.get("desk") != DESK_ID:
        raise EmploymentRequestError("wrong_desk")
    if card.get("status") != "pending":
        raise EmploymentRequestError("not_pending")
    if approver != card.get("approval_owner"):
        raise EmploymentRequestError("wrong_approver")
    before = len(runtime_agents)
    if before > MAX_RUNTIME_AGENTS:
        raise EmploymentRequestError("agent_cap_exceeded_before_approve")
    updated = dict(card)
    updated["status"] = "approved"
    updated["executed"] = False
    updated["decision"] = "employment_accepted_no_runtime_spawn"
    if len(runtime_agents) != before:
        raise EmploymentRequestError("agents_mutated_during_approve")
    if len(runtime_agents) > MAX_RUNTIME_AGENTS:
        raise EmploymentRequestError("agent_cap_exceeded_after_approve")
    return updated
