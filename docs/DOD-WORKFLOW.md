# DoD workflow-lab

PASS only with evidence (PR URL, API response, or `DECISIONS.md` line). Do not mark PASS from hope.

**Fully working** = W-01..W-05 + W-07 + W-08 PASS — **ACHIEVED 2026-09-12** (plan W-05 close). W-06 (phone) = next checkpoint after Linear mobile.

Updated: 2026-09-12 (plan closed — W-01 protection on, W-05/W-09 evidence; `DECISIONS.md`).

## Scoreboard

| ID | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| W-01 | One `origin`. `main` merge-only via PR. Native GitHub protection on. | PASS | Origin = GitHub. Repo **public** (`D-W01-PUBLIC`). **Branch protection on `main`** 2026-09-12: required check `validate`, PR required (`D-W01-PROTECT`). |
| W-02 | `npm run lint` + `npm test` + `npm run build` = AGENTS.md §2 = `.github/workflows/ci.yml` | PASS | CI job `validate` SUCCESS on PR #1 |
| W-03 | Linear project `workflow-lab`, labels `agent`/`review`/`blocked`, 6-field template | PASS | Workspace https://linear.app/quietforge · project https://linear.app/quietforge/project/workflow-lab-93ba13d2e4b6 · labels created · template https://linear.app/quietforge/document/szablon-6-pol-agent-6decf6006360 · `DECISIONS.md` D-W3-LINEAR |
| W-04 | One laptop loop: issue/PR → green CI → merge to `main` | PASS | https://github.com/wozniaknorbert95-del/workflow-lab/pull/1 merged 2026-09-12 (`4ea746d`) |
| W-05 | One PR opened by Cursor Cloud Agent, CI green. Human merges. | PASS | Agent `bc-c187d412` → branch `cursor/greet-cloud-test-bfd7` → [PR #14](https://github.com/wozniaknorbert95-del/workflow-lab/pull/14) CI `validate` SUCCESS → squash-merged `8239f41` 2026-09-12. Infra: #12 ca-certificates, #13 curl. `DECISIONS.md` D-W5-CLOUD. |
| W-06 | Linear mobile issue → Cloud Agent → GitHub mobile merge | FAIL | Next checkpoint after Linear mobile setup |
| W-07 | Human gates: merge, secrets, no dual-origin, no dsaas deploy from lab | PASS | `AGENTS.md` §1; `DECISIONS.md` D-W0 / D-C7 |
| W-08 | C7: dsaas not on this board | PASS | `DECISIONS.md` D-C7 |
| W-09 | Cursor spend limit on. `$/MR` recorded after first cloud run | PASS | Pro+ On-Demand Unlimited. First cloud delivery W-05 agent `bc-c187d412`. Usage snapshot 2026-09-12: 96.8M tokens included, on-demand **$0** ([dashboard/usage](https://cursor.com/dashboard/usage)). `$/MR` marginal = **$0** on included plan (`DECISIONS.md` D-W9-USAGE). |
| W-10 | `DECISIONS.md` current | PASS | D-W5-CLOUD, D-W9-USAGE, D-W01-PROTECT, D-W3-LINEAR, D-W4-LOOP |

## How to raise a FAIL to PASS

- W-01..W-05, W-07..W-10: **done** (2026-09-12). Repo **fully working** per strict DoD.
- W-06: Linear mobile → Cloud Agent → GitHub mobile merge (next session).
- F3 optional: CA-2/3 extra Cloud runs (`docs/W2-CLOUD-AGENTS.md`), GitLab CE cutover (`D-W0-ORIGIN`).
