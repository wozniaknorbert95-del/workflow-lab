# DoD workflow-lab

PASS only with evidence (PR URL, API response, or `DECISIONS.md` line). Do not mark PASS from hope.

**Fully working** = W-01..W-05 + W-07 + W-08 PASS. W-06 (phone) is a later checkpoint after Linear mobile. W-03 PASS 2026-09-12.

Updated: 2026-09-12 (W-05 BLOCKED — Cursor checkout; see `DECISIONS.md` D-W5-CLOUD).

## Scoreboard

| ID | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| W-01 | One `origin`. `main` merge-only via PR. Native GitHub protection on. | PARTIAL | Origin = GitHub. Repo **public** since 2026-09-12 (`DECISIONS.md` D-W01-PUBLIC). Classic branch protection not yet enabled. Social rule: AGENTS.md never push `main`. |
| W-02 | `npm run lint` + `npm test` + `npm run build` = AGENTS.md §2 = `.github/workflows/ci.yml` | PASS | CI job `validate` SUCCESS on PR #1 |
| W-03 | Linear project `workflow-lab`, labels `agent`/`review`/`blocked`, 6-field template | PASS | Workspace https://linear.app/quietforge · project https://linear.app/quietforge/project/workflow-lab-93ba13d2e4b6 · labels created · template https://linear.app/quietforge/document/szablon-6-pol-agent-6decf6006360 · `DECISIONS.md` D-W3-LINEAR |
| W-04 | One laptop loop: issue/PR → green CI → merge to `main` | PASS | https://github.com/wozniaknorbert95-del/workflow-lab/pull/1 merged 2026-09-12 (`4ea746d`) |
| W-05 | One PR opened by Cursor Cloud Agent, CI green. Human merges. | FAIL | Issue https://github.com/wozniaknorbert95-del/workflow-lab/issues/5 — 9 `@cursor` retries; latest agents `bc-787c46b3`, `bc-c6bd0185`, `bc-86e070d2` checkout FAIL; 0 open PRs. Env `6d364999-ae9a-11f1-bf4b-42ffb4d10ea7` 0 green builds. `DECISIONS.md` D-W5-CLOUD. |
| W-06 | Linear mobile issue → Cloud Agent → GitHub mobile merge | FAIL | Blocked on W-05 |
| W-07 | Human gates: merge, secrets, no dual-origin, no dsaas deploy from lab | PASS | `AGENTS.md` §1; `DECISIONS.md` D-W0 / D-C7 |
| W-08 | C7: dsaas not on this board | PASS | `DECISIONS.md` D-C7 |
| W-09 | Cursor spend limit on. `$/MR` recorded after first cloud run | PARTIAL | On-Demand Unlimited enabled 2026-09-12. Agents start but checkout FAIL before billable delivery; `$/MR` not recorded. |
| W-10 | `DECISIONS.md` current | PASS | D-W0 GitHub origin; D-W4-LOOP; D-W3-LINEAR Quietforge; D-W01-PROTECT blocked by GitHub Free |

## How to raise a FAIL to PASS

- W-01 remainder: enable classic branch protection on public repo (require PR + required check `validate`).
- W-03: done. Live URLs in `docs/LINEAR.md`.
- W-05: fix Cursor checkout per `DECISIONS.md` D-W5-CLOUD (reinstall GitHub App + green environment build), then `@cursor` on issue #5. Merge the PR yourself.
- W-06: after W-03 and W-05.
- W-09: one line in `DECISIONS.md` after the first billed cloud run.
