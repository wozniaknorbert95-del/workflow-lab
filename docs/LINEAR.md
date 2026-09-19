# Linear — Quietforge (W-03)

Workspace exists. Staff is connected via Linear MCP as `wozniaknorbert95@gmail.com`.
Do not create a second workspace named `quietforge-ops`. The live slug is **`quietforge`**.

dsaas stays **off this project's issue board** (C7). GitHub Reviews in Linear may still list other repos until you narrow the GitHub app to `workflow-lab` only.

## Live facts (2026-09-12)

| Piece | Evidence |
| --- | --- |
| Workspace | https://linear.app/quietforge (`Quietforge`) |
| Team | `Quietforge` (`QUI`) |
| Project | https://linear.app/quietforge/project/workflow-lab-93ba13d2e4b6 |
| Labels | `agent`, `review`, `blocked` |
| 6-field template (document) | https://linear.app/quietforge/document/szablon-6-pol-agent-6decf6006360 |
| Twin GitHub template | `.github/ISSUE_TEMPLATE/agent-task.md` |
| First CO issue | https://linear.app/quietforge/issue/QUI-5 (GitHub twin: workflow-lab#5) |
| GitHub sync | Linear already sees this repo (example: workflow-lab PR #6 in Reviews) |

## How staff creates a task

1. New issue in team `Quietforge`, project `workflow-lab`, label `agent`.
2. Paste the six fields from the project document (Cel / Kontekst / Wymagania / Ograniczenia / Kryteria / Weryfikacja).
3. Link the GitHub issue if Cloud Agent will run (Cursor Cloud uses GitHub, not Linear as origin).
4. Auto-merge (green CI) merges the PR.

WIP: max 3 agent runs, max 5 In progress (`ops/workflow-marzen/04` in the academy repo).

## Optional Commander clicks (not required for W-03 PASS)

1. Phone 2FA if Linear web asks (staff API is already authenticated).
2. Settings → Integrations → GitHub → keep **only** `workflow-lab` if you want a clean Reviews inbox (C7 hygiene).
3. Settings → Templates → save the 6-field body as a native issue template (document above is the SoT until then).
4. cursor.com/agents → GitHub `workflow-lab` issue #5 → Start (this is **W-05**, not W-03).
