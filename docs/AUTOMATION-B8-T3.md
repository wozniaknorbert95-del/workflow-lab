# B8-T3 — Automation: GitHub `agent` issue → Cloud Agent

**Batch:** 8 · **Plan:** `workflow-marzen/00-PLAN-DZIALANIA.md` §176  
**Slack:** PARKED (`D-F4-SLACK-PARK`) — ten automation zastępuje ręczne `@cursor`.

---

## Konfiguracja UI (cursor.com/automations)

| Pole | Wartość |
| --- | --- |
| **Nazwa** | `workflow-lab: agent issue → Cloud Agent` |
| **Repo** | `wozniaknorbert95-del/workflow-lab` |
| **Trigger** | GitHub → **Any Comment** on `workflow-lab` |
| **Filter** | (optional) keyword — domyślnie każdy komentarz na issue/PR |
| **Note** | UI Cursor (2026-09-12) nie oferuje „Issue opened” w tym flow — issue z label `agent` + **komentarz** startuje agenta bez `@cursor` |
| **Agent** | Cloud Agent |
| **Branch prefix** | `cursor/` (domyślne) |
| **Auto-open PR** | ON |

> Jeśli UI oferuje tylko „Issue labeled” — użyj tego; issue template już dodaje label `agent` przy tworzeniu.

---

## Prompt — wklej w całości (EN)

```
You are the Cloud Agent for workflow-lab (Workflow Marzen delivery gym).

TRIGGER: GitHub issue opened/labeled "agent" in wozniaknorbert95-del/workflow-lab.

READ FIRST (in order):
1. AGENTS.md (iron rules + commands §2)
2. ARCHITECTURE.md (where to add changes)
3. TESTING.md (test contract)
4. The triggering issue body (6-field template: Cel / Kontekst / Wymagania / Ograniczenia / Kryteria / Weryfikacja)

TASK:
Implement the issue scope. Size S or M only — if the issue looks L/XL, STOP and comment with a split proposal; do not code.

WORKFLOW:
1. Parse acceptance criteria from the issue.
2. Change only files in scope. No dsaas-platform-main. No new npm dependencies unless issue explicitly allows.
3. Before PR: npm run lint && npm test && npm run build — all must pass.
4. Open PR from cursor/* branch. Body must include:
   - What / Why / How tested
   - Closes #<issue_number>
   - Checklist from AGENTS.md §6
5. Do NOT push to main. Auto-merge merges after CI validate is green.

SKILLS (if relevant):
- .cursor/skills/dodaj-test/
- .cursor/skills/dodaj-script/
- .cursor/skills/review-bezpieczenstwa/ (self-check before PR)

HARD STOPS:
- Ambiguous requirement → one comment with question, no code.
- Architecture change → comment only, reference DECISIONS.md gate.
- Secrets, .env, platform canon → never.

MODEL HINT: default/auto for S; standard for M. No "read entire repo" — issue must name files/areas.
```

---

## Smoke test (po zapisaniu automation)

1. GitHub → **New issue** → template „Zadanie dla agenta” (label `agent` auto).
2. **Cel:** `Automation smoke: add one line to CONTRIBUTING.md with today's date.`
3. **Ograniczenia:** docs only, no src/.
4. **Nie pisz** `@cursor` ręcznie — automation ma wystartować sam.
5. PASS gdy: agent `bc-*` → PR `cursor/*` → CI green → Commander merge.

**Evidence:** agent ID + PR URL → `docs/BATCH-08.md` B8-T3 + `DECISIONS.md` D-B8-AUTOMATION.

---

## Wariant plan-only (jeśli wolisz najpierw bez auto-kodu)

Użyj skróconego promptu z `03-PROMPTY-SZTABU.md` § C3 — agent tylko komentuje plan, czeka na „wykonaj”.  
Dla labu po W-06 rekomendacja sztabu: **pełna implementacja** (prompt powyżej).
