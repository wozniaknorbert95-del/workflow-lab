# Daily Digest — B9-T1

Daily digest posts the `workflow-lab` morning status to GitHub issue
[#44](https://github.com/wozniaknorbert95-del/workflow-lab/issues/44).

## Runtime

- Cursor Automation: `workflow-lab: daily digest 07:30`
- GitHub Actions workflow: `.github/workflows/daily-digest.yml`
- Script: `scripts/daily-digest.mjs`
- Schedule: `30 5 * * 1,3,5` UTC (Mon/Wed/Fri 07:30 Europe/Warsaw during CEST). Phase 1 audit reduced from daily — see `docs/AUDIT-PHASE-1.md`.
- Output target: GitHub issue #44

## Digest Content

- Open `agent` issues, excluding the tracking issue itself.
- Open PRs waiting for review or merge.
- Red/failing checks on open PRs.
- One next action.

## Smoke

Run locally from repo root:

```powershell
node --check scripts/daily-digest.mjs
node scripts/daily-digest.mjs
```

To post a smoke comment with the same code path:

```powershell
$env:GH_TOKEN = gh auth token
$env:POST_COMMENT = "true"
$env:DIGEST_HEADING = "Daily digest smoke"
$env:TRACKING_ISSUE = "44"
node scripts/daily-digest.mjs
```

Do not print or commit tokens.

## Evidence

- Cursor Automation config: `docs/evidence/b9-t1-cursor-automation-config.png`
- Final issue smoke: `docs/evidence/b9-t1-digest-issue-smoke.png`
- Decision: `DECISIONS.md` → `D-B9-DAILY-DIGEST`
