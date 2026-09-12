# ARCHITECTURE.md — workflow-lab

One page.

## What this is

A tiny Node 20 ESM package used to **train the delivery loop**, not to ship a product.

```
issue (Linear or GitHub 6-field template)
  → branch feat|fix|chore
  → npm run lint && npm test && npm run build
  → MR/PR
  → CI (same three commands)
  → human merge
```

## Runtime

- No HTTP server, no database, no Docker Compose for the app.
- Library: `src/hello.js` exports `greet(name = "workflow-lab")`.
- Tests: `src/hello.test.js` via `node:test`.
- Build: `scripts/build.js` copies `src/*.js` (not tests) into `dist/`.

## CI parity

GitHub Actions `.github/workflows/ci.yml` and GitLab `.gitlab-ci.yml` run **exactly** the commands in `AGENTS.md` §2. No extra tools.

## What is not here

- QuietForge Kokpit, ontologies, OPA, MCP.
- Academy lessons (`DASHBOARD.html`).
- Secrets, `.env` values, deploy to VPS.
