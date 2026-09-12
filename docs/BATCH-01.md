# Batch 01 — F3 infra closure

**Started:** 2026-09-12 · **Plan ref:** `ROADMAP-MASTER.md` Batch 1

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| B1-T1 | OAuth auto-PR smoke (CA-1 @cursor) | PARTIAL | Agent `bc-54ca70ec` pushed branch; PR [#19](https://github.com/wozniaknorbert95-del/workflow-lab/pull/19) via `gh` (auto-PR blocked — GitHub Connect fail) |
| B1-T2 | Bugbot ON | BLOCKED | Integrations: **Failed to load GitHub settings** → **Connect** required |
| B1-T3 | Security Agents ON | BLOCKED | Same as B1-T2 |
| B1-T4 | PR Routing OFF | PENDING | After B1-T2 |
| B1-T5 | F3 cost baseline D-W3-COST | DONE | `DECISIONS.md` D-W3-COST |

**Also executed (Batch 2 overlap):** CA-3 agent `bc-4b9bb898` → PR [#20](https://github.com/wozniaknorbert95-del/workflow-lab/pull/20) merged.

**Exit gate:** B1-T2..T4 PASS → close Batch 1 → full Batch 2 scorecard in [BATCH-02.md](./BATCH-02.md)
