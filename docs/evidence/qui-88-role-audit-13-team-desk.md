# QUI-88 — ROLE-AUDIT-13: wniosek zatrudnienia na `team-desk` (5 kroków SSoT)

Date: 2026-09-22  
Linear: [QUI-88](https://linear.app/quietforge/issue/QUI-88/role-audit-13-p2-zespol-wniosek-zatrudnienia-na-team-desk-5-krokow-z)  
Parent: [QUI-75](https://linear.app/quietforge/issue/QUI-75/role-audit-qf-rolejob-audit-domkniecie-luk-pracownikow-i-dzialow)  
Depends on owner resolution: [QUI-79](https://linear.app/quietforge/issue/QUI-79/role-audit-04-p1-zespol-konflikt-leadid-owner-vs-hr-stewardb7) (Done)  
GitHub tracking: [workflow-lab#86](https://github.com/wozniaknorbert95-del/workflow-lab/issues/86)

Scope: **lab contract mirror** — producer + tests in `workflow-lab`; port to `dsaas-platform-main` runtime/Taca in a follow-up MR on platform (repo not accessible from this Cloud Agent token). Zero PII, zero deploy.

## E0 — delta 5 kroków SSoT vs płyta

| Źródło | Kroki | Uwagi |
| --- | ---: | --- |
| SSoT `business-rules.processes.zespol.zatrudnienie` | **5** | `need_submitted` → `role_defined` → `hr_review` → `owner_acceptance` → `onboarding_gate` |
| `base-plate.json` (krótszy wariant) | **3** | `request` → `owner_acceptance` → `done` — brak `hr_review` i jawnej bramki „no spawn agent” |

Fixture SSoT: `scripts/fixtures/qui-88/zespol-zatrudnienie-ssot-5steps.json`  
Fixture płyta: `scripts/fixtures/qui-88/zespol-zatrudnienie-base-plate-short.json`

## Właściciel wniosku (ROLE-AUDIT-04 / QUI-79)

| Rola | Id | Zastosowanie |
| --- | --- | --- |
| Szef wykonawczy Zespołu | `hr-steward` | Producer karty, kroki operacyjne |
| Human-stop akceptacji | `owner` | Akceptacja zatrudnienia na Tacy — **nie** worker id w katalogu |

## Producer karty `team-desk`

Moduł: `scripts/team_desk/employment.py`

Pola wniosku (AC #1): `department`, `position`, `duties_kpi`, `technology`.

Karta Taca (AC #2): `desk=team-desk`, `status=pending`, `labels` zawiera `hitl:approval-required`, `approval_owner=owner`, `producer=hr-steward`.

## Approve ≠ spawn agenta (AC #3)

`approve_employment_card()` ustawia `status=approved`, `executed=false`, `decision=employment_accepted_no_runtime_spawn`.  
Test utrzymuje stałą listę agentów runtime (`≤3`) — brak append/spawn.

## Weryfikacja (lab)

```bash
python scripts/test_team_desk.py
npm run lint && npm test && npm run build
```

## Następny krok (platforma)

Przenieść producer do `runtime/` + test pytest `team-desk` na `dsaas-platform-main` z tym samym kontraktem fixture; merge na platformie po GO / dostępie repo.
