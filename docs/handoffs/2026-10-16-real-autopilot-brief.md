# Handoff — Real Autopilot Brief (2026-10-16)

## Cel

Conductor `_brief()` nie jest już hardcodowanym lab-probe dla każdego Start. QUI-43 / platforma dostaje real Autopilot + `/autopilot`; smoke zostaje na `lab_probe`.

## Zmiany

| Plik | Co |
| --- | --- |
| `scripts/hermes_ops/issue_brief.py` | DoR excerpts + AC + `brief_kind` + opcjonalny Linear fetch |
| `scripts/hermes_ops/conductor_adapter.py` | `write_handoff` → url/ac/dor_excerpts/brief_kind (bez raw description) |
| `scripts/hermes_conductor/loop.py` | `_brief` real vs lab_probe; AC seed; steer follow-up |
| `scripts/test_hermes_conductor.py` | T11/T12 real brief + handoff |
| `docs/ops/hermes-conductor/CONDUCTOR.md` | brief_kind w procedurze |

## Dogfood (unit)

```
python scripts/test_hermes_conductor.py  → PASS T1-T12
python scripts/test_hermes_ops.py        → PASS
```

QUI-43 create prompt (mock): `Repo=dsaas-platform-main`, `autopilot.md`, AC brand-kit, **zero** `conductor-lab-probe`.  
QUI-131 / `brief_kind=lab_probe`: nadal probe.

## VPS

Wymaga deploy obrazu conductor / sync skryptów na VPS (Zasada 11, osobne GO). Po deploy: Start QUI-43 → sprawdź prompt w Cloud (nie probe).

## Env

| Var | Znaczenie |
| --- | --- |
| `CONDUCTOR_LAB_PROBE_ISSUES` | CSV id smoke (default QUI-129,QUI-130,QUI-131) |
| `OPS_CONDUCTOR_LAB_PROBE=1` | wymuś lab_probe na wszystkie |
| `LINEAR_OPS_READ` | przy Start: fetch description → excerpts (kolejka nadal OFF) |
