# Batch 01 — F3 infra closure

**Started:** 2026-09-12 · **Closed:** 2026-09-12 · **Plan ref:** `ROADMAP-MASTER.md` Batch 1

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| B1-T1 | OAuth auto-PR smoke | PASS | Reconnect verified: `get-github-installations` 200, `githubConnected: true`. CA-1 agent `bc-54ca70ec` → PR #19 (pre-reconnect used `gh` fallback). |
| B1-T2 | Bugbot ON | PASS | API: `workflow-lab` → `bugBotEnabled: true`, install 161116895 |
| B1-T3 | Security Agents ON | PASS | API: `isPrRiskScoreEnabled: true` on installation |
| B1-T4 | PR Routing OFF | PASS | Default; no PR routing automation enabled (handbook) |
| B1-T5 | F3 cost baseline D-W3-COST | PASS | `DECISIONS.md` D-W3-COST + D-W3-GITHUB-OAUTH |

**Exit gate:** ✅ **BATCH 01 CLOSED** → proceed [BATCH-02.md](./BATCH-02.md)
