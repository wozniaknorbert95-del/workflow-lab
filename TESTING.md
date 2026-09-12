# TESTING.md — workflow-lab

One page. Matches `AGENTS.md` §5. Zero npm dependencies.

## Commands (same as CI `validate`)

```
lint:   npm run lint
test:   npm test
build:  npm run build
```

There is no `typecheck`. Do not invent one.

## Framework

- Node 20 built-in `node:test` + `node:assert/strict`.
- Contract file: `src/hello.test.js` (`npm test` runs `node --test src/hello.test.js`).
- New behaviour: add a unit test in `src/*.test.js`.
- Bugfix: add a regression test that fails without the fix.
- Do not mock the filesystem for `greet`.

## Cases covered today

| Case | Input | Expect |
| --- | --- | --- |
| Happy path | `greet()` | `hello workflow-lab` |
| Trim | `greet("  lab  ")` | `hello lab` |
| Empty | `greet("  ")` | throws `TypeError` |
| Cloud | `greet("Cloud")` | `hello Cloud` |

## Rules

- Every feature ships happy path + one edge.
- User-visible behaviour has an error path.
- Do not delete or weaken a failing test unless the test is wrong.
- Fresh clone + `AGENTS.md` = works (no install step).
