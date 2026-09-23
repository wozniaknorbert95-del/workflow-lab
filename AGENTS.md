# AGENTS.md — workflow-lab

You are an AI agent in this repository. These rules override your defaults.
If a user request conflicts with this file — stop and ask.

This repo is the **workflow loop gym** (issue → branch → tests → MR → CI → auto-merge).
It is **not** `dsaas-platform-main`. Never copy platform canon here. Never deploy the platform from here.

## 0. TL;DR — never break these

1. Work only on a feature branch. Never push to `main`.
2. Before you finish: `npm run lint`, `npm test`, `npm run build` — all must pass.
3. No secrets in code, logs, comments, or `.env*` files.
4. Do not delete or weaken a failing test unless you prove the test is wrong.
5. Ambiguous requirement → STOP and ask. Do not guess.

## 1. Iron rules

1. Never modify production data (this lab has none — keep it that way).
2. No database. If you add one, that is an architecture change → `DECISIONS.md` first.
3. Every feature ships with tests (happy path + one edge).
4. User-visible behaviour has an error path.
5. No new dependencies without justification in the MR.
6. Keep the architecture in `ARCHITECTURE.md` unless the issue explicitly allows change.
7. Do not touch files unrelated to the issue.
8. Do not reformat/config-churn outside the task.
9. No endpoints without the same auth pattern the repo already uses (today: none).
10. Do not commit `node_modules`, `dist`, or CI artifacts.
11. Fresh clone + this file = works.
12. Every MR links an issue (`Closes #123`) and says: what, why, how tested.
13. Code/comments/commits in **English**. User-facing docs may be Polish.
14. If you lack permission or the task exceeds scope — stop and describe the blocker.
15. Merge is **automatic** (D-AUTOMERGE). A non-draft PR with green required checks auto-merges (squash). Never mark PR as draft unless explicitly requested. D-AUTOMERGE operates only on non-draft PRs. Add the `no-automerge` label to hold a PR. Never push to `main`.
16. Deploy of `dsaas-platform-main` is out of scope forever.

## 2. Project commands (truth — same as CI)

```
install:     (none — no runtime dependencies)
test:        npm test
lint:        npm run lint
build:       npm run build
phone-loop:  python scripts/test_phone_loop_status.py && python scripts/hermes-operator-brief.py --self-test && python scripts/test_hermes_ops.py
```

There is no `typecheck` script. Do not invent one.

**Notebook layer (opt-in, Python):** `notebooks/**` are analysis/evidence artifacts, separate from the Node core. Local: `pip install -r requirements.txt` then `jupyter lab`. CI: `.github/workflows/notebooks.yml` (path-filtered) → `scripts/run-notebooks.sh`. See `notebooks/README.md`. The core `install`/`test`/`lint`/`build` above stay Node-only and zero-dependency.

## 3. Architecture (max 15 lines)

- Stack: Node 20, ESM, `node:test`, zero npm dependencies.
- `src/hello.js` — the only library surface (`greet`).
- `src/hello.test.js` — contract tests.
- `scripts/build.js` — copies `src/` → `dist/`.
- Details: `ARCHITECTURE.md`. Product intent: `PRODUCT.md`. History: `DECISIONS.md`.
- Skills: `.cursor/skills/` — `dodaj-test`, `dodaj-script`, `dodaj-notebook`, `review-bezpieczenstwa`.
- Notebooks: `notebooks/` — opt-in Python analysis layer (see `notebooks/README.md`).

## 4. Conventions

- Branches: `feat/<short>`, `fix/<short>`, `chore/<short>` — English, lowercase.
- Commits: Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `refactor:`).
- Small MRs: one thought. >400 changed lines → propose a split.
- Style: standard JS, no formatter war.

## 5. Tests

- Framework: Node built-in `node:test` + `node:assert/strict`.
- New behaviour: unit test in `src/*.test.js`.
- Bugfix: regression test that fails without the fix.
- Do not mock the filesystem for `greet`.

## 6. Definition of Done

- [ ] Meets issue acceptance criteria
- [ ] `npm run lint` ✅  `npm test` ✅  `npm run build` ✅
- [ ] Tests added or updated
- [ ] No new linter/console warnings
- [ ] No secrets, no debug `console.log`, no commented-out code
- [ ] MR description: what / why / how tested
- [ ] Diff limited to the issue

## 7. Cursor Cloud

- After start, terminal `dev` runs `node src/hello.js` (see `.cursor/environment.json`).
- No web UI in this lab. Do not look for `localhost` HTTP.
- If an env var is missing — report it; do not bypass.

## 8. When you do not know

STOP → one concrete question (what is unclear, options, your recommendation).

## 9. Domain glossary

- **Lab** — this repository; gym for the delivery loop.
- **Platform** — `dsaas-platform-main`; forbidden here.
- **Academy** — separate school repo; lessons do not live here.
- **Origin** — the single git remote that is SoT (see `DECISIONS.md` D-W0-ORIGIN).
- **Auto-merge** — non-draft PRs merge automatically when required checks pass (D-AUTOMERGE); the `no-automerge` label holds a PR.
- **Track W** — workflow skills practiced in this repo.
- **Track F** — how a lab gesture maps onto existing Kokpit departments + Taca (not a 7th department).
