# Audit Phase 1 — CI workflow optimization

**Scope:** `workflow-lab` only. **Branch:** `cursor/phase-1-optimize-ci-workflows-4fbb` (renamed from `audit/phase-1-optimize-ci-workflows`).  
**Started by:** Copilot (daily-digest). **Completed by:** Cursor Agent (2026-09-13).

## Goal

Reduce scheduled and redundant GitHub Actions minutes without weakening the delivery loop (lint / test / build on code changes).

## Summary

| Metric | Before | After | Delta |
| --- | --- | --- | --- |
| `daily-digest` scheduled runs | 7/week | 3/week | −57% |
| `weekly-security-sweep` scheduled runs | 1/week | 0 (manual) | −100% scheduled |
| `ci` on docs-only PRs | always runs | skipped | fewer redundant runs |

Estimated savings: ~4 fewer scheduled workflow runs per week plus skipped `validate` on docs-only PRs.

## Changes

| Workflow | Before | After | Rationale |
| --- | --- | --- | --- |
| `daily-digest.yml` | Daily 07:30 Warsaw | Mon/Wed/Fri 07:30 Warsaw | Digest still covers the week |
| `weekly-security-sweep.yml` | Weekly cron (Mon 07:00 Warsaw) | `workflow_dispatch` only | Morning ritual owns cadence |
| `ci.yml` | Every PR + push to `main` | Path filters on code paths | Docs-only PRs skip `validate` |

## Path filters (`ci.yml`)

CI runs when any of these paths change:

- `src/**`
- `scripts/**`
- `package.json`
- `.github/workflows/ci.yml`

Docs-only changes (e.g. `README.md`, `docs/**`) no longer trigger `validate`. Branch protection still requires green checks when the workflow runs.

## Manual triggers retained

- `daily-digest` — `workflow_dispatch` (evening ritual / on-demand smoke)
- `weekly-security-sweep` — `workflow_dispatch` only (morning ritual step)

## Docs updated

- `docs/DAILY-DIGEST.md` — schedule
- `docs/W4-AUTOMATIONS.md` — automation specs
- `docs/MORNING-RITUAL.md` — digest cadence + manual security sweep step
- `DECISIONS.md` → `D-AUDIT-PHASE-1`

## Commander follow-up (post-merge)

1. **Cursor Automation** — if UI still shows daily digest, align schedule to Mon/Wed/Fri (GitHub Actions already updated).
2. **Merge PR** — human gate; squash merge after green `validate`.
3. **Smoke** — dispatch `daily-digest` once; confirm comment on issue #44.

## Verification

```bash
npm run lint && npm test && npm run build
```

PR touching `.github/workflows/ci.yml` must show green `validate` in Actions.

## Out of scope (Phase 2)

Platform repo (`dsaas-quietforge` / `dsaas-platform-main`) — separate audit; not modified from this lab.

## Rollback

Revert merge commit or restore individual workflow files from `main` pre-merge.
