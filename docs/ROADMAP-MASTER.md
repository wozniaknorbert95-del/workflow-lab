# Roadmap master — Workflow Marzeń (15×5)

**Source:** `workflow-marzen/00-PLAN-DZIALANIA.md` · **Lab scoreboard:** `DOD-WORKFLOW.md`  
**Rule:** each batch = 5 tasks → verify gates → next batch. Human-stop = Dowódca only where marked.

**Current batch:** [BATCH-08.md](./BATCH-08.md) · **Status:** IN PROGRESS (F4 Automations + Grok; Slack **PARKED**)

---

## Progress map

| Batches | Theme | Plan phase | Status |
|---------|-------|------------|--------|
| **1–3** | Cloud Agents + Bugbot | F3 | **CLOSED** (F3 PASS, Bugbot comment PARTIAL) |
| **4–6** | Memory AI (docs + skills) | F2 | **CLOSED** (Batch 4–5) |
| **7–9** | Mobile + Automations + Grok (Slack parked) | F4 | Batch 7 **CLOSED** · Batch 8 IN PROGRESS |
| **10–12** | GitLab CE cutover | F0 | PENDING (VPS human-stop) |
| **13–15** | Hardening + Academy sync | F5 + §8a | PENDING |

---

## Batch 1 — F3 infra closure (post W-05)

| ID | Task | Owner | Gate |
|----|------|-------|------|
| B1-T1 | OAuth auto-PR smoke (@cursor on CA-1 issue) | R1 + Cloud | PR opened without `gh` fallback |
| B1-T2 | Bugbot ON for `workflow-lab` | Browser | Bugbot comment on ≥1 PR |
| B1-T3 | Security Agents ON on MRs | Browser | Scan visible on MR |
| B1-T4 | PR Routing = OFF | Browser | Screenshot + `DECISIONS.md` |
| B1-T5 | F3 cost baseline (`$/MR` per run) | R1 | `D-W3-COST` in `DECISIONS.md` |

## Batch 2 — Cloud Agent MR wave (CA-1..CA-3)

| ID | Task | Owner | Gate |
|----|------|-------|------|
| B2-T1 | CA-1: README „Komendy" = AGENTS.md §2 | Cloud | PR merged, CI green |
| B2-T2 | CA-2: trim test MR (cloud-attributed) | Cloud | 2nd cloud MR or marked superseded |
| B2-T3 | CA-3: CONTRIBUTING cloud MR or verify | Cloud | ≤40 lines, merged |
| B2-T4 | ≥2/3 MR without manual code fixes | Dowódca | Score in DOD |
| B2-T5 | Register agent IDs + PR links | R1 | `DECISIONS.md` |

## Batch 3 — Bugbot loop + F3 exit

| ID | Task | Owner | Gate |
|----|------|-------|------|
| B3-T1 | Collect Bugbot findings from CA MRs | R1 | Issue list with links |
| B3-T2 | Cloud follow-up fixes ≥1 finding | Cloud | Follow-up PR merged |
| B3-T3 | Security: zero Critical/Serious on main | R1 | Scan report |
| B3-T4 | F3 exit scorecard in DOD | R1 | Section F3 PASS |
| B3-T5 | Academy module 3 checkpoint | Browser | `akademia/` export |

*(Batches 4–15: see full tables in plan session artifact; expanded on demand per batch start.)*

---

## Operating loop

```
PLAN (this file + BATCH-NN.md)
  → EXECUTE (issue / PR / dashboard)
  → VERIFY (CI + gate column)
  → EVIDENCE (DECISIONS.md + DOD)
  → NEXT BATCH
```

**W-06** closes in Batch 7. **GitLab CE** starts Batch 10 (Commander VPS).
