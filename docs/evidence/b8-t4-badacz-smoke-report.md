# B8-T4 — Grok Bot BADACZ smoke report

**Date:** 2026-09-12 · **Bot:** BADACZ (Grok Bot desktop v0.44.0) · **Query by:** Playwright CDP automation

## Query

> For public GitHub repositories like `wozniaknorbert95-del/workflow-lab` — are standard GitHub-hosted runner minutes free?  
> Official GitHub docs only. Format: Facts → Hypotheses → One recommendation.

## Facts (verified 2026-09-12)

1. **GitHub Actions usage is free for public repositories using standard GitHub-hosted runners.**  
   Source: https://docs.github.com/en/billing/concepts/product-billing/github-actions

2. **Standard GitHub-hosted runners are free in public repositories** (ubuntu/windows/macos standard labels).  
   Source: same billing page + https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job#standard-github-hosted-runners-for-public-repositories

3. **Larger runners are always charged**, even on public repos.  
   Source: GitHub Actions billing docs (caveat section).

## Hypotheses

None material — docs are explicit. Only risk: workflow accidentally selects a **larger runner** (billable).

## Recommendation

Treat standard GitHub-hosted minutes as **$0** on `workflow-lab` (public); avoid larger runners unless budget approved.

## Evidence artifacts

- `b8-t4-grok-07-smoke-response.png` — BADACZ chat with cited answer
- `b8-t4-grok-smoke-transcript.txt` — full UI transcript
- `b8-t4-grok-05-bot-created.png` — bot created in Grok Bot app
