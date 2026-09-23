"""ROLE-AUDIT-06 — business-facing Kokpit labels (no internal jargon)."""
from __future__ import annotations

SURFACE_LABELS_PL: dict[str, str] = {
    "hypothesis": "Hipoteza biznesowa",
    "metric": "Metryka sukcesu",
    "result": "Wynik eksperymentu",
    "decision": "Decyzja po kalibracji",
    "evidence_url": "Link do materiału dowodowego",
    "experiment_id": "Identyfikator eksperymentu",
    "calibration_status": "Status kalibracji",
    "case_study": "Studium przypadku",
    "release_desk": "Biuro publikacji",
}


def kokpit_label(field_key: str) -> str:
    return SURFACE_LABELS_PL.get(field_key, field_key.replace("_", " ").title())
