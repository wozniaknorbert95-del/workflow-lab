"""release-desk gate: case study cannot reach /proof/ without closed experiment + evidence."""
from __future__ import annotations

from typing import Any

from release_desk.experiment_ledger import calibration_status

DESK_ID = "release-desk"
CARD_KIND_CASE_STUDY = "case_study"
PROOF_PREFIX = "/proof/"
STEWARD_WORKER = "release-steward"


def evaluate_case_study_publish(
    *,
    target_path: str,
    experiment: dict[str, Any],
    evidence_ready: bool,
    desk: str = DESK_ID,
) -> tuple[bool, str]:
    """
    Blocks case study on /proof/ until calibration PASS and R7 evidence_ready.
    Non-/proof/ targets are out of scope for this gate (lab mirror).
    """
    if desk != DESK_ID:
        return False, "wrong_desk"
    path = str(target_path or "").strip()
    if not path.startswith(PROOF_PREFIX):
        return True, "not_proof_surface"
    if not evidence_ready:
        return False, "evidence_required_before_proof"
    if calibration_status(experiment) != "PASS":
        return False, "experiment_calibration_not_pass"
    return True, "allowed"


def build_case_study_card(
    *,
    experiment: dict[str, Any],
    proposal_id: str,
    tenant_id: str = "quietforge",
    target_path: str = "/proof/case-study/draft",
) -> dict[str, Any]:
    """Pending card on release-desk; publish blocked until gate passes."""
    allowed, reason = evaluate_case_study_publish(
        target_path=target_path,
        experiment=experiment,
        evidence_ready=False,
    )
    return {
        "proposal_id": proposal_id,
        "tenant_id": tenant_id,
        "desk": DESK_ID,
        "kind": CARD_KIND_CASE_STUDY,
        "producer": STEWARD_WORKER,
        "target_path": target_path,
        "status": "blocked" if not allowed else "pending",
        "block_reason": None if allowed else reason,
        "experiment_id": experiment.get("experiment_id"),
        "labels": ["area:analityka", "gate:proof-blocked"],
    }
