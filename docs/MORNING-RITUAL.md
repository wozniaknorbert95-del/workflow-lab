# Morning Ritual — 10 Minutes

Use this every morning after the 07:30 daily digest lands in issue
[#44](https://github.com/wozniaknorbert95-del/workflow-lab/issues/44).

Goal: know what needs your decision today without opening five dashboards.

## Timer

Set a 10-minute timer. Stop when the timer ends. Anything unclear becomes one next action, not a rabbit hole.

## Checklist

| Minute | Check | Done When |
|--------|-------|-----------|
| 0-2 | Read the latest daily digest in issue #44 | You know open `agent` issues, PRs waiting review/merge, and CI red |
| 2-4 | Open Linear `workflow-lab` board | You checked what is `In review` |
| 4-7 | Check agent runs / open PRs | Each finished run has one status: merge, comment, or close |
| 7-9 | Pick 1-3 priorities for today | Priorities have labels/status in Linear or GitHub |
| 9-10 | Write one sentence: "first action now" | You can start without re-reading context |

## Decision Rules

- If a PR is green and small, review it first.
- If CI is red, fix or assign the red check before starting new work.
- If more than three agent runs are active, stop launching new work and close/kill one.
- If a task is not actionable, rewrite it into the six-field issue template before assigning `agent`.

## Output

At the end, write exactly one line in your notes or as a comment where relevant:

```text
Today first: <one action, one owner, one link>
```

Example:

```text
Today first: Commander reviews PR #45 after green CI.
```

## Guardrails

- No deploy decisions during the ritual.
- No spend or upgrade decisions during the ritual; those belong to the Friday review.
- No dsaas-platform-main work from this lab ritual.
