# QUI-87 — ROLE-AUDIT-12: eksperymenty, release-desk i benchmark ledger (wykonanie lab)

Date: 2026-09-23  
Linear: [QUI-87](https://linear.app/quietforge/issue/QUI-87/role-audit-12-p2-analityka-eksperymenty-release-desk-i-benchmark)  
Parent: [QUI-75](https://linear.app/quietforge/issue/QUI-75/role-audit-qf-rolejob-audit-domkniecie-luk-pracownikow-i-dzialow)  
Surface language: ROLE-AUDIT-06 (Analityka)  
GitHub tracking: [workflow-lab#92](https://github.com/wozniaknorbert95-del/workflow-lab/issues/92)

Scope: **lab contract mirror** — ledger + release-desk gate + tests in `workflow-lab`; port to `dsaas-platform-main` (`release-desk` pytest + ruff per issue §7) in a follow-up MR. Zero PII, zero live `/proof/` publish, append-only ledger.

## E0 — pomiar przed

| Obszar | Stan | Skutek |
| --- | --- | --- |
| `eksperyment-kalibracja` | deklaracja w business-rules | Brak zamkniętego wpisu z wynikiem |
| Case study → `/proof/` | brak bramki w lab | Możliwość „PASS” bez wyniku / bez evidence |
| Benchmark ledger | brak SSoT wpisu | Brak audytowalnej decyzji po eksperymencie |

## E1 — szablon wpisu eksperymentu (ledger)

Fixture szablonu: `scripts/fixtures/qui-87/experiment-entry-template.json`  
Proces (mirror): `scripts/fixtures/qui-87/eksperyment-kalibracja-process.json`  
Zamknięty wpis lab (EV): `scripts/fixtures/qui-87/experiment-closed-lab-sample.json`

Moduł: `scripts/release_desk/experiment_ledger.py`

| Pole | Rola |
| --- | --- |
| `hypothesis` | hipoteza biznesowa |
| `metric` | metryka sukcesu |
| `result` | wynik (pusty = kalibracja **nie** PASS) |
| `decision` | decyzja po kalibracji |
| `evidence_url` | link HTTP(S) do materiału dowodowego (bez PII) |

Append-only: `append_ledger_line()` → JSONL, duplicate `experiment_id` = FAIL.

## E2 — release-desk gate na case study

Moduł: `scripts/release_desk/case_study_gate.py`

- `target_path` z prefiksem `/proof/` **wymaga** `evidence_ready=True` oraz `calibration_status == PASS`.
- Karta `release-desk` startuje ze `status=blocked` dopóki R7 evidence nie jest gotowe.
- Producer: `release-steward`.

## Język Kokpitu (ROLE-AUDIT-06)

`scripts/release_desk/surface_labels.py` — etykiety PL bez żargonu (`EV`, `ledger`).

## Kryteria akceptacji (mapa)

| AC | Lab |
| --- | --- |
| 1. hipoteza, metryka, wynik, decyzja, evidence | `validate_experiment_entry` + closed sample |
| 2. release-desk blokuje case study przed `/proof/` | `evaluate_case_study_publish` |
| 3. brak wyniku ≠ PASS | `test_release_desk.py` |
| 4. język biznesowy | `kokpit_label` / `SURFACE_LABELS_PL` |

## Weryfikacja (lab)

```bash
python scripts/test_release_desk.py
npm run lint && npm test && npm run build
```

## Następny krok (platforma)

Przenieść gate + ledger do `dsaas-platform-main` release-desk; uruchomić pytest + ruff z issue §7; **bez** deploy z workflow-lab.
