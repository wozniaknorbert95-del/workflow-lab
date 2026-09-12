# W4 — Automations + Grok (gated)

**Do not enable until three MRs from this repo are merged with green CI.**
Until then these are specs only. Activation = Commander.

Source: `akademia/ops/workflow-marzen/04-INSTRUKCJA-OBSUGI.md` rytuały 10′/5′/piątek.

## Automation 1 — daily digest (07:30)

Trigger: cron 07:30 Europe/Warsaw.
Action: comment on Linear project `workflow-lab` (or GitHub tracking issue) with: open `agent` issues, PRs waiting review, CI red.
Do not post secrets. Do not mention dsaas ENT-*.

## Automation 2 — weekly security sweep (Monday)

Trigger: weekly.
Action: open issue `chore: weekly security sweep` labeled `agent`.
Body: run skill `review-bezpieczenstwa` on `main` since last sweep. Output = list or “clean”.

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
