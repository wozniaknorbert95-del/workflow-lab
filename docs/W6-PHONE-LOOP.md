# W-06 — Phone loop runbook

One page. Closes `docs/DOD-WORKFLOW.md` W-06.

## Definition

> Linear mobile issue → Cloud Agent → GitHub mobile merge — **without opening laptop**.

## Preconditions (check once)

| # | Check | How |
| --- | --- | --- |
| 1 | Linear app | iOS/Android, workspace **Quietforge**, project **workflow-lab** |
| 2 | GitHub mobile | Logged in as `wozniaknorbert95-del`, notifications ON |
| 3 | Cursor Cloud | OAuth connected (`D-W3-GITHUB-OAUTH`), green build |
| 4 | Branch protection | `main` requires PR + `validate` (already ON) |

## Steps (Commander, phone)

1. **Linear mobile** — New issue → project `workflow-lab` → label `agent` → paste 6 fields from issue template (size S, docs-only).
2. **GitHub** — Open twin issue (staff creates link) or duplicate from `.github/ISSUE_TEMPLATE/agent-task.md`.
3. **Comment** `@cursor` on GitHub issue with scope (≤5 lines README change).
4. **Wait** — Cloud Agent opens `cursor/*` PR; CI runs `validate`.
5. **GitHub mobile** — Review PR → squash merge when green.
6. **Evidence** — Screenshot Linear + GitHub merge; staff updates DOD + DECISIONS.

## Suggested first task (smoke)

Add to `README.md` after Status line:

```markdown
- **Mobile loop (W-06):** verified YYYY-MM-DD from phone.
```

## Fail paths

| Symptom | Fix |
| --- | --- |
| Agent no PR | Check Integrations OAuth (`D-W3-GITHUB-OAUTH`) |
| CI red | Agent must fix; do not merge |
| Cannot merge on phone | Human-stop: laptop merge once, log blocker in issue |

## Related

- Batch tracker: `docs/BATCH-07.md`
- GitHub issue: [#32](https://github.com/wozniaknorbert95-del/workflow-lab/issues/32)
- Master plan: Faza 4 — `workflow-marzen/00-PLAN-DZIALANIA.md:174-179`
