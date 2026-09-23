#!/usr/bin/env python3
"""QUI-87: experiment ledger, calibration PASS rules, release-desk /proof/ gate."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from release_desk.case_study_gate import (  # noqa: E402
    DESK_ID,
    build_case_study_card,
    evaluate_case_study_publish,
)
from release_desk.experiment_ledger import (  # noqa: E402
    ExperimentLedgerError,
    append_ledger_line,
    calibration_status,
    closed_lab_sample,
    load_entry_template,
)
from release_desk.surface_labels import SURFACE_LABELS_PL, kokpit_label  # noqa: E402

PROCESS_FIXTURE = ROOT / "fixtures" / "qui-87" / "eksperyment-kalibracja-process.json"


def main() -> int:
    errors: list[str] = []

    template = load_entry_template()
    req = template.get("required_fields") or []
    for field in ("hypothesis", "metric", "result", "decision", "evidence_url"):
        if field not in req:
            errors.append(f"template missing required field {field}")

    process = json.loads(PROCESS_FIXTURE.read_text(encoding="utf-8"))
    if process.get("owner") != "release-steward":
        errors.append(f"process owner: {process.get('owner')}")
    if len(process.get("steps") or []) < 5:
        errors.append("eksperyment-kalibracja needs ≥5 steps")

    closed = closed_lab_sample()
    if calibration_status(closed) != "PASS":
        errors.append("closed lab sample must calibrate PASS")

    no_result = dict(closed, result="")
    if calibration_status(no_result) == "PASS":
        errors.append("AC#3: brak wyniku must not PASS kalibracji")

    no_decision = dict(closed, decision="")
    if calibration_status(no_decision) == "PASS":
        errors.append("empty decision must not PASS")

    ok, reason = evaluate_case_study_publish(
        target_path="/proof/case-study/qui-87",
        experiment=closed,
        evidence_ready=True,
    )
    if not ok or reason != "allowed":
        errors.append(f"/proof/ publish with PASS+evidence: {ok} {reason}")

    blocked, block_reason = evaluate_case_study_publish(
        target_path="/proof/case-study/qui-87",
        experiment=no_result,
        evidence_ready=True,
    )
    if blocked or block_reason != "experiment_calibration_not_pass":
        errors.append(f"/proof/ must block without result: {blocked} {block_reason}")

    blocked_ev, ev_reason = evaluate_case_study_publish(
        target_path="/proof/case-study/qui-87",
        experiment=closed,
        evidence_ready=False,
    )
    if blocked_ev or ev_reason != "evidence_required_before_proof":
        errors.append(f"R7 evidence gate: {blocked_ev} {ev_reason}")

    off_proof, off_reason = evaluate_case_study_publish(
        target_path="/internal/draft",
        experiment=no_result,
        evidence_ready=False,
    )
    if not off_proof or off_reason != "not_proof_surface":
        errors.append(f"non-/proof/ should not gate: {off_proof} {off_reason}")

    card = build_case_study_card(experiment=closed, proposal_id="PROP-qui87-cs")
    if card.get("desk") != DESK_ID:
        errors.append(f"desk: {card.get('desk')}")
    if card.get("status") != "blocked":
        errors.append("case study card starts blocked before evidence_ready")

    if kokpit_label("hypothesis") != SURFACE_LABELS_PL["hypothesis"]:
        errors.append("kokpit_label mismatch")
    if "EV" in kokpit_label("evidence_url") or "ledger" in kokpit_label("experiment_id").lower():
        errors.append("ROLE-AUDIT-06: avoid internal jargon in surface labels")

    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "experiments.jsonl"
        append_ledger_line(closed, ledger)
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) != 1:
            errors.append(f"append-only ledger lines: {len(lines)}")
        try:
            append_ledger_line(closed, ledger)
            errors.append("duplicate experiment_id should fail")
        except ExperimentLedgerError as exc:
            if "duplicate" not in str(exc):
                errors.append(f"unexpected duplicate error: {exc}")
        try:
            append_ledger_line({"experiment_id": "x"}, ledger)
            errors.append("incomplete entry should fail validate")
        except ExperimentLedgerError:
            pass

    if errors:
        print("FAIL:")
        for item in errors:
            print(" -", item)
        return 1
    print(
        "PASS: release_desk "
        + json.dumps(
            {
                "process_steps": len(process.get("steps") or []),
                "closed_id": closed.get("experiment_id"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
