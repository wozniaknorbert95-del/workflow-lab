# W4 — Automations + Grok (gated)

**Do not enable until three MRs from this repo are merged with green CI.**
Until then these are specs only. Activation = Commander.

Source: `akademia/ops/workflow-marzen/04-INSTRUKCJA-OBSUGI.md` rytuały 10′/5′/piątek.

## Automation 1 — digest (07:30, Mon/Wed/Fri)

Trigger: cron Mon/Wed/Fri 07:30 Europe/Warsaw (Phase 1 audit, 2026-09-13).
Action: comment on Linear project `workflow-lab` (or GitHub tracking issue) with: open `agent` issues, PRs waiting review, CI red.
Do not post secrets. Do not mention dsaas ENT-*.

**Implemented (B9-T1, 2026-09-12; schedule optimized Phase 1, 2026-09-13):**

- Cursor Automation: `workflow-lab: daily digest 07:30` *(Commander: align Cursor UI schedule to Mon/Wed/Fri if still daily)*
- Automation ID: `d968fd5d-aeb5-11f1-bf4b-42ffb4d10ea7`
- GitHub Actions cron: `30 5 * * 1,3,5` UTC (Mon/Wed/Fri 07:30 Europe/Warsaw during CEST)
- Durable output path: GitHub issue [#44](https://github.com/wozniaknorbert95-del/workflow-lab/issues/44)
- Reliable posting mechanism: `.github/workflows/daily-digest.yml` → `scripts/daily-digest.mjs`
- Smoke: final comment on #44 shows `Open agent issues: 0`, `PRs waiting review/merge: 0`, `CI red: 0`

## Automation 2 — weekly security sweep (manual)

Trigger: `workflow_dispatch` only (Phase 1 audit, 2026-09-13). Run from morning ritual or Actions tab.
Action: open issue `chore: weekly security sweep` labeled `agent`.
Body: run skill `review-bezpieczenstwa` on `main` since last sweep. Output = list or “clean”.

**Implemented (B9-T5, 2026-09-12; schedule removed Phase 1, 2026-09-13):**

- GitHub Actions workflow: `.github/workflows/weekly-security-sweep.yml`
- Reliable issue opener: `scripts/weekly-security-sweep.mjs`
- Trigger: manual only — no cron (saves scheduled minutes; morning ritual owns cadence)
- Script is idempotent per ISO week and reuses an existing open sweep issue instead of creating duplicates
- Output issue body points to skill `review-bezpieczenstwa` and requires `PASS: clean` or exact blockers

## Automation 3 — label `agent` → plan comment

Trigger: issue labeled `agent`.
Action: comment a C3 plan (Cel/Kryteria/pliki) — **no code**. Wait for Commander “wykonaj”.

## Grok Bot BADACZ

Rola: research nie-kodowy (ceny, docs.gitlab.com, cursor.com/docs).
Zakaz: kod, sekrety, produkcyjne konta, merge.
Prompt: `docs/grok-bots/BADACZ.md`.

## Grok Bot PM

Rola: “co boli dziś” z boardu (WIP, wiszące PR).
Zakaz: kod.
Prompt: `docs/grok-bots/PM.md`.

## Rituals (after activation)

- Morning 10 min, evening 5 min, Friday 30 min — handbook `04`.
- Upgrade purchases only on Friday.
