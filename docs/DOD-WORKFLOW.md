# DoD workflow-lab

PASS only with evidence (PR URL, API response, or `DECISIONS.md` line). Do not mark PASS from hope.

**Fully working** = W-01..W-05 + W-07 + W-08 PASS. W-06 (phone) is a later checkpoint after Linear mobile. W-03 PASS 2026-09-12.

Updated: 2026-09-12 (Linear Quietforge connected; Cloud Agent issue #5 / QUI-5 seeded).

## Scoreboard

| ID | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| W-01 | One `origin`. `main` merge-only via PR. Native GitHub protection on. | PARTIAL | Origin = GitHub. PR #1 merged via PR. Native branch protection **403** on private Free plan (`Upgrade to GitHub Pro or make this repository public`). Social rule: AGENTS.md never push `main`. |
| W-02 | `npm run lint` + `npm test` + `npm run build` = AGENTS.md §2 = `.github/workflows/ci.yml` | PASS | CI job `validate` SUCCESS on PR #1 |
| W-03 | Linear project `workflow-lab`, labels `agent`/`review`/`blocked`, 6-field template | PASS | Workspace https://linear.app/quietforge · project https://linear.app/quietforge/project/workflow-lab-93ba13d2e4b6 · labels created · template https://linear.app/quietforge/document/szablon-6-pol-agent-6decf6006360 · `DECISIONS.md` D-W3-LINEAR |
| W-04 | One laptop loop: issue/PR → green CI → merge to `main` | PASS | https://github.com/wozniaknorbert95-del/workflow-lab/pull/1 merged 2026-09-12 (`4ea746d`) |
| W-05 | One PR opened by Cursor Cloud Agent, CI green. Human merges. | FAIL | Seeded GitHub https://github.com/wozniaknorbert95-del/workflow-lab/issues/5 and Linear https://linear.app/quietforge/issue/QUI-5 . Commander starts Cloud Agent on cursor.com/agents (GitHub origin). |
| W-06 | Linear mobile issue → Cloud Agent → GitHub mobile merge | FAIL | Blocked on W-05 |
| W-07 | Human gates: merge, secrets, no dual-origin, no dsaas deploy from lab | PASS | `AGENTS.md` §1; `DECISIONS.md` D-W0 / D-C7 |
| W-08 | C7: dsaas not on this board | PASS | `DECISIONS.md` D-C7 |
| W-09 | Cursor spend limit on. `$/MR` recorded after first cloud run | PARTIAL | Cloud Agents exist. `$/MR` not yet in `DECISIONS.md` |
| W-10 | `DECISIONS.md` current | PASS | D-W0 GitHub origin; D-W4-LOOP; D-W3-LINEAR Quietforge; D-W01-PROTECT blocked by GitHub Free |

## How to raise a FAIL to PASS

- W-01 remainder: GitHub Pro **or** public repo, then enable classic branch protection (require PR + required check `validate`). Until then: never push `main`.
- W-03: done. Live URLs in `docs/LINEAR.md`.
- W-05: open GitHub issue #5 on cursor.com/agents. Merge the PR yourself.
- W-06: after W-03 and W-05.
- W-09: one line in `DECISIONS.md` after the first billed cloud run.
