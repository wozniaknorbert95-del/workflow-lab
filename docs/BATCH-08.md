# Batch 08 — F4 autonomia cz. 2 (bez Slack)

**Started:** 2026-09-12 · **Plan ref:** `ROADMAP-MASTER.md` Batch 8 · Master plan F4 §174-179  
**Scope cut:** Slack **PARKED** — `DECISIONS.md` D-F4-SLACK-PARK (Dowódca 2026-09-12).

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| B8-T1 | ~~Slack Connect~~ | **PARKED** | Odłożone — Linear + GitHub mobile wystarczą na teraz |
| B8-T2 | Automation: daily digest | PENDING | GitHub/Linear event, bez Slack |
| B8-T3 | Automation: comment → Cloud Agent | **PASS** | [Automation 64ead0a5](https://cursor.com/automations/64ead0a5-aeb1-11f1-bf4b-42ffb4d10ea7) ON · comment on [#38](https://github.com/wozniaknorbert95-del/workflow-lab/issues/38#issuecomment-5646344422) → agent `bc-9172fb9e` → [PR #40](https://github.com/wozniaknorbert95-del/workflow-lab/pull/40) CI green |
| B8-T4 | Grok Bot BADACZ (research) | PENDING | Cursor dashboard |
| B8-T5 | Grok Bot PM (Linear status) | PENDING | Zamiennik części notyfikacji Slack |

**Exit gate (bez Slack):** B8-T3 + (B8-T4 lub B8-T5) → F4 partial PASS

**Prerequisite:** W-06 PASS ✅ · Slack nie blokuje bramki

**Next action:** Merge [PR #40](https://github.com/wozniaknorbert95-del/workflow-lab/pull/40) (Commander) → B8-T4 Grok BADACZ lub B8-T2 daily digest
