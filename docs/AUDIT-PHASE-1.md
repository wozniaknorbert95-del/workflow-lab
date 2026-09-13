# Audit Phase 1 — CI workflow optimization

**Scope:** `workflow-lab` only. **Branch:** `audit/phase-1-optimize-ci-workflows`.

## Goal

Reduce scheduled and redundant GitHub Actions minutes without weakening the delivery loop (lint / test / build on code changes).

## Changes

| Workflow | Before | After | Rationale |
| --- | --- | --- | --- |
| `daily-digest.yml` | Daily 07:30 Warsaw | Mon/Wed/Fri 07:30 Warsaw | Digest still covers the week; ~57% fewer scheduled runs |
| `weekly-security-sweep.yml` | Weekly cron (Mon 07:00 Warsaw) | `workflow_dispatch` only | Security sweep runs on demand via morning ritual (B9-T2) |
| `ci.yml` | Every PR + push to `main` | Path filters on `src/`, `scripts/`, `package.json`, `ci.yml` | Docs-only PRs skip `validate`; code paths unchanged |

## Path filters (`ci.yml`)

CI runs when any of these paths change:

- `src/**`
- `scripts/**`
- `package.json`
- `.github/workflows/ci.yml`

Docs-only changes (e.g. `README.md`, `docs/**`) no longer trigger `validate`. Merge still requires green CI when the PR touches filtered paths.

## Manual triggers retained

- `daily-digest` — `workflow_dispatch` (B9-T1 evening ritual)
- `weekly-security-sweep` — `workflow_dispatch` only (B9-T2 morning ritual)

## Verification

```bash
npm run lint && npm test && npm run build
```

For workflow YAML: push branch and confirm Actions tab shows expected trigger behaviour on a docs-only vs code PR.

## Out of scope (Phase 2)

Platform repo (`dsaas-quietforge` / `dsaas-platform-main`) — separate audit; not modified from this lab.

## Rollback

Revert this branch or restore individual workflow files from `main`.
