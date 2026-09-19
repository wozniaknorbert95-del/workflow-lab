# ARCHITECTURE.md — workflow-lab

One page. Read this + `AGENTS.md` §2 before touching code.

## What this is

A **Node 20 ESM gym** for the Workflow Marzeń delivery loop — not a product, not the DSaaS platform.

```
Linear / GitHub issue (6-field template)
  → branch feat|fix|chore
  → npm run lint && npm test && npm run build
  → PR (human opens or Cloud Agent auto-PR)
  → CI validate (same three commands)
  → auto-merge (green CI) → DECISIONS.md if irreversible
```

## Directory map

| Path | Role |
| --- | --- |
| `src/hello.js` | Only library export: `greet(name?)` |
| `src/hello.test.js` | Contract tests (`node:test`) — see `TESTING.md` |
| `scripts/build.js` | Copies `src/*.js` (not tests) → `dist/` |
| `scripts/cloud-env-diag.js` | Cloud Build smoke (TLS, curl, git) |
| `.github/workflows/ci.yml` | GitHub CI — **must match** `AGENTS.md` §2 |
| `.gitlab-ci.yml` | GitLab CE mirror (same commands, future F0) |
| `notebooks/` | **Opt-in Python** analysis/evidence layer — not Node core |
| `requirements.txt` | Pinned Python deps for the notebook layer |
| `.github/workflows/notebooks.yml` | Notebook CI — executes `notebooks/*.ipynb` headless (path-filtered) |
| `scripts/run-notebooks.sh` | Discovers + executes notebooks via `nbconvert` |
| `.gitattributes` | `*.ipynb` nbstripout filter — no outputs in git |
| `.cursor/Dockerfile` | Cloud Agent image: node:20 + ca-certificates + curl |
| `.cursor/environment.json` | Cloud install + `dev` terminal |
| `.cursor/skills/` | Repeatable procedures for agents |
| `.cursor/rules/` | Polish guardrails; **AGENTS.md wins** on conflict |
| `docs/DOD-WORKFLOW.md` | Scoreboard W-01..W-10 |
| `DECISIONS.md` | Irreversible choices (newest first) |

## Runtime layer

- **No** HTTP server, database, Docker Compose app, or npm dependencies.
- `greet(name = "workflow-lab")` — trims input; empty/whitespace → `TypeError`.
- CLI: `node src/hello.js` prints default greeting (Cloud `dev` terminal).
- Build output: `dist/hello.js` (artifact only; tests never copied).
- Notebook layer (`notebooks/`): opt-in Python (venv + `requirements.txt`), executed headless in CI. It does **not** change the Node core's zero-dependency contract.

## CI parity rule

Single source of truth: `package.json` scripts.

```
lint:  node --check on src/*.js + scripts/build.js
test:  node --test src/hello.test.js
build: node scripts/build.js
```

GitHub `validate` job and GitLab `lint`/`unit-tests`/`build` stages run **exactly** these. Do not add tools without updating all three surfaces.

The notebook layer is a **separate, path-filtered** concern: `.github/workflows/notebooks.yml` (+ GitLab `notebooks` job) runs `jupyter nbconvert --execute` over `notebooks/*.ipynb` with a fresh `ci-kernel`. It does **not** run inside the Node `validate` job.

## Cloud Agent layer

Cloud Agents clone via GitHub App, build `.cursor/Dockerfile`, run in isolated VM.

- Infra fixes: PR #12 (ca-certificates), #13 (curl) — required for checkout/exec.
- OAuth auto-PR: Integrations User OAuth (separate from GitHub App) — see `D-W3-GITHUB-OAUTH`.
- Evidence: agent ID + PR URL in `DECISIONS.md` / `docs/DOD-WORKFLOW.md`.

## Three architectural decisions

1. **Zero npm deps** — fresh clone + Node 20 = works. Trade-off: no eslint/jest; use `node --check` + `node:test`.
2. **Single origin GitHub** — lab SoT is `wozniaknorbert95-del/workflow-lab`. GitLab CE is future cutover (F0), not dual-origin.
3. **Auto-merge on green CI** (D-AUTOMERGE) — non-draft PRs auto-merge (squash) when required checks pass; `no-automerge` label holds. No one pushes to `main`.

## Where to add [example feature]

| Change type | Where |
| --- | --- |
| New `greet` behaviour | `src/hello.js` + regression test in `src/hello.test.js` + row in `TESTING.md` |
| New npm script | `package.json` + `AGENTS.md` §2 + CI yaml(s) — use skill `dodaj-script` |
| New test file | `src/*.test.js` + wire in `package.json` `test` — use skill `dodaj-test` |
| New notebook | `notebooks/*.ipynb` + `requirements.txt` if needed — use skill `dodaj-notebook` |
| Cloud/env change | `.cursor/Dockerfile` or `environment.json` + `DECISIONS.md` entry |

## What is not here

QuietForge Kokpit, ontologies, OPA, MCP runtime, tenant data, Academy lessons, production deploy of DSaaS.
