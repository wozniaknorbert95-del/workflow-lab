"""Append-only experiment / benchmark ledger (QUI-87 / ROLE-AUDIT-12)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "qui-87"
TEMPLATE_FIXTURE = FIXTURES / "experiment-entry-template.json"
CLOSED_SAMPLE = FIXTURES / "experiment-closed-lab-sample.json"

REQUIRED_FIELDS = ("experiment_id", "hypothesis", "metric", "decision", "evidence_url")
OPTIONAL_WITH_DEFAULT = ("result", "status")


class ExperimentLedgerError(ValueError):
    """Invalid experiment ledger entry or append."""


def load_entry_template(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or TEMPLATE_FIXTURE).read_text(encoding="utf-8"))


def validate_experiment_entry(entry: dict[str, Any]) -> None:
    """Structural validation — result may be empty while experiment is open."""
    missing = [k for k in REQUIRED_FIELDS if not str(entry.get(k) or "").strip()]
    if missing:
        raise ExperimentLedgerError(f"missing_fields:{','.join(missing)}")
    url = str(entry["evidence_url"]).strip()
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ExperimentLedgerError("evidence_url_must_be_http")
    for key in ("hypothesis", "metric", "result", "decision"):
        val = str(entry.get(key) or "").lower()
        if any(token in val for token in ("@", "nip", "pesel", "phone")):
            raise ExperimentLedgerError("pii_forbidden_in_entry")


def calibration_status(entry: dict[str, Any]) -> str:
    """
    eksperyment-kalibracja outcome for Kokpit.
    AC: brak wyniku ≠ PASS.
    """
    result = str(entry.get("result") or "").strip()
    if not result:
        return "FAIL"
    decision = str(entry.get("decision") or "").strip()
    if not decision:
        return "FAIL"
    try:
        validate_experiment_entry(entry)
    except ExperimentLedgerError:
        return "FAIL"
    return "PASS"


def append_ledger_line(
    entry: dict[str, Any],
    ledger_path: Path,
    *,
    allow_duplicate_id: bool = False,
) -> None:
    """Append-only JSONL; never rewrite prior lines."""
    validate_experiment_entry(entry)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    eid = str(entry["experiment_id"]).strip()
    if ledger_path.is_file() and not allow_duplicate_id:
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            prior = json.loads(line)
            if str(prior.get("experiment_id")) == eid:
                raise ExperimentLedgerError(f"duplicate_experiment_id:{eid}")
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def closed_lab_sample(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or CLOSED_SAMPLE).read_text(encoding="utf-8"))
