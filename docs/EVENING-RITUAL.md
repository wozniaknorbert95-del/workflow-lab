# Evening Ritual — 5 Minutes

Use this at the end of the day to prevent stale PRs, vague Linear state, and lost morning context.

Goal: nothing important hangs overnight without a clear next owner.

## Timer

Set a 5-minute timer. This ritual is a shutdown checklist, not a planning session.

## Checklist

| Minute | Check | Done When |
|--------|-------|-----------|
| 0-2 | Review every open PR | Each PR is merged, commented with the exact fix needed, or closed |
| 2-3 | Check failed/queued CI | Every red or stuck run has one owner and one next action |
| 3-4 | Update Linear / GitHub facts | Status reflects facts, not hope |
| 4-5 | Write tomorrow's first action | One sentence exists with action, owner, and link |

## PR Rule

Every open PR must end the day in exactly one of these states:

- **Merge:** CI green, scope understood, no blocker.
- **Comment:** specific blocker or requested fix written in the PR.
- **Close:** duplicate, stale, wrong scope, or superseded.

No PR should be left in "I'll look later" state.

## Output

Write one line:

```text
Tomorrow first: <one action, one owner, one link>
```

Example:

```text
Tomorrow first: R1 implements B9-T4 Grok PM after digest confirms no red CI.
```

## Guardrails

- Do not start new coding work during the evening ritual.
- Do not merge if CI is red or unknown.
- Do not deploy from this ritual.
- Do not make spending or upgrade decisions here; use the Friday review.
