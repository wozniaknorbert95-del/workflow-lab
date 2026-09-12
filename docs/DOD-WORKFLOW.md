# DoD workflow-lab

PASS only with evidence (PR URL, API response, or `DECISIONS.md` line). Do not mark PASS from hope.

**Fully working** = W-01..W-06 + W-07 + W-08 PASS — **ACHIEVED 2026-09-12** (W-06 phone loop). W-09/W-10 PASS.

Updated: 2026-09-12 (B9-T2 morning ritual PASS; `DECISIONS.md` D-B9-MORNING-RITUAL).

## F4 partial — Autonomia cz. 2 (master plan §5 Faza 4, Slack parked)

| Criterion | Status | Evidence |
| --- | --- | --- |
| W-06 phone loop | PASS | D-W6-PHONE |
| Automation: issue comment → Cloud Agent | PASS | D-B8-AUTOMATION · PR #40/#42 |
| Grok Bot BADACZ (research) | PASS | D-B8-GROK-BADACZ · smoke report |
| Slack | PARKED | D-F4-SLACK-PARK |
| Daily digest | PASS | D-B9-DAILY-DIGEST · issue #44 smoke |
| Morning ritual 10′ | PASS | D-B9-MORNING-RITUAL · `docs/MORNING-RITUAL.md` |
| Evening ritual 5′ | PENDING | Batch 9 |

**F4 verdict:** **PARTIAL PASS** (core autonomia bez Slack). Next: Batch 9 rituals.

## F2 exit — Memory AI (master plan §5 Faza 2)

| Criterion | Status | Evidence |
| --- | --- | --- |
| `ARCHITECTURE.md` one-pager | PASS | [PR #28](https://github.com/wozniaknorbert95-del/workflow-lab/pull/28) |
| `PRODUCT.md` one-pager | PASS | [PR #28](https://github.com/wozniaknorbert95-del/workflow-lab/pull/28) |
| `TESTING.md` one-pager | PASS | [PR #25](https://github.com/wozniaknorbert95-del/workflow-lab/pull/25) |
| `DECISIONS.md` current | PASS | D-F3-EXIT, D-W3-GITHUB-OAUTH, D-W3-COST |
| 3 Skills | PASS | `dodaj-test`, `dodaj-script`, `review-bezpieczenstwa` |
| A1 audit filed | PASS | `docs/A1-AUDIT-2026-09-12.md` — 9.2/10 |
| Agent zero convention questions | PASS | ARCHITECTURE “where to add” table + skills |

**F2 verdict:** **PASS**. Next: Batch 5 (F2 scorecard formalize) → Batch 7 W-06 mobile.

## F3 exit — Cloud Agents (master plan §5 Faza 3)

| Criterion | Status | Evidence |
| --- | --- | --- |
| Green Cloud Build + `environment.json` | PASS | `.cursor/Dockerfile` (#12 ca-cert, #13 curl); build green post-fix |
| ≥3 Cloud Agent MRs | PASS | #14 W-05, #19 CA-1, #20 CA-3, #25 smoke — 4 total |
| Auto-PR post-OAuth (no `gh` fallback) | PASS | #25 agent `bc-fc7682c1`, branch `cursor/testing-md-0a8e` |
| ≥2/3 MR merged without manual code fixes | PASS | 4/4 agent code merged as-is (W-05 PR opened via `gh`, code untouched) |
| Bugbot enabled | PASS | API `bugBotEnabled: true` (`D-W3-GITHUB-OAUTH`) |
| Bugbot comment on MR | PARTIAL | No comments yet — carry to Batch 4 |
| `$/MR` recorded | PASS | `DECISIONS.md` D-W3-COST — $0 marginal (Pro+ included) |

**F3 verdict:** **PASS with one PARTIAL** (Bugbot comment deferred). Next: F2 memory AI (Batch 4).

## Scoreboard

| ID | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| W-01 | One `origin`. `main` merge-only via PR. Native GitHub protection on. | PASS | Origin = GitHub. Repo **public** (`D-W01-PUBLIC`). **Branch protection on `main`** 2026-09-12: required check `validate`, PR required (`D-W01-PROTECT`). |
| W-02 | `npm run lint` + `npm test` + `npm run build` = AGENTS.md §2 = `.github/workflows/ci.yml` | PASS | CI job `validate` SUCCESS on PR #1 |
| W-03 | Linear project `workflow-lab`, labels `agent`/`review`/`blocked`, 6-field template | PASS | Workspace https://linear.app/quietforge · project https://linear.app/quietforge/project/workflow-lab-93ba13d2e4b6 · labels created · template https://linear.app/quietforge/document/szablon-6-pol-agent-6decf6006360 · `DECISIONS.md` D-W3-LINEAR |
| W-04 | One laptop loop: issue/PR → green CI → merge to `main` | PASS | https://github.com/wozniaknorbert95-del/workflow-lab/pull/1 merged 2026-09-12 (`4ea746d`) |
| W-05 | One PR opened by Cursor Cloud Agent, CI green. Human merges. | PASS | Agent `bc-c187d412` → branch `cursor/greet-cloud-test-bfd7` → [PR #14](https://github.com/wozniaknorbert95-del/workflow-lab/pull/14) CI `validate` SUCCESS → squash-merged `8239f41` 2026-09-12. Infra: #12 ca-certificates, #13 curl. `DECISIONS.md` D-W5-CLOUD. |
| W-06 | Linear mobile issue → Cloud Agent → GitHub mobile merge | **PASS** | [QUI-10](https://linear.app/quietforge/issue/QUI-10) → agent `bc-2aeab115` → [PR #34](https://github.com/wozniaknorbert95-del/workflow-lab/pull/34) CI green → **GitHub mobile merge** `b8e261a` 2026-09-12. `DECISIONS.md` D-W6-PHONE. |
| W-07 | Human gates: merge, secrets, no dual-origin, no dsaas deploy from lab | PASS | `AGENTS.md` §1; `DECISIONS.md` D-W0 / D-C7 |
| W-08 | C7: dsaas not on this board | PASS | `DECISIONS.md` D-C7 |
| W-09 | Cursor spend limit on. `$/MR` recorded after first cloud run | PASS | Pro+ On-Demand Unlimited. First cloud delivery W-05 agent `bc-c187d412`. Usage snapshot 2026-09-12: 96.8M tokens included, on-demand **$0** ([dashboard/usage](https://cursor.com/dashboard/usage)). `$/MR` marginal = **$0** on included plan (`DECISIONS.md` D-W9-USAGE). |
| W-10 | `DECISIONS.md` current | PASS | D-W5-CLOUD, D-W9-USAGE, D-W01-PROTECT, D-W3-LINEAR, D-W4-LOOP |

## How to raise a FAIL to PASS

- W-01..W-10: **done** (2026-09-12). Repo **fully working** including phone loop (W-06).
- F3 optional: CA-2/3 extra Cloud runs (`docs/W2-CLOUD-AGENTS.md`), GitLab CE cutover (`D-W0-ORIGIN`).
