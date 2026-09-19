# W2 — Cursor Cloud Agents (GitHub origin)

CE token test (`05` §5) is **parked** until `docs/W0-GITLAB-CE-CHECKLIST.md` is green.
Until then Cloud Agents use **this GitHub repo** (official Cursor↔GitHub). Spend limit + Privacy Mode = Commander human-stop.

## Staff already landed

- `.cursor/environment.json` (Node 20, `dev` = `node src/hello.js`, install = `true` because zero deps)
- `.cursor/Dockerfile`
- Issue template 6 fields
- Skill `review-bezpieczenstwa`

## Commander — 15 min after spend limit

1. cursor.com → connect GitHub → this repo.
2. Enable Bugbot + Security on PRs. **PR Routing = off**.
3. Seed three Cloud Agent runs from issues labeled `agent` (prompts below). Merge remains human.

## Three agent tasks (S)

Copy into Cloud Agent / issue body. Each = one MR.

### CA-1 README truth

CEL: README pokazuje komendy 1:1 z AGENTS.md.
KONTEKST: `README.md`, `AGENTS.md` §2.
WYMAGANIA: sekcja „Komendy” w README = lint/test/build; zero pnpm/typecheck.
OGRANICZENIA: nie ruszaj `src/`.
KRYTERIA: `npm test` nadal zielone.
WERYFIKACJA: diff README.

### CA-2 greet trims inner spaces conservatively

CEL: `greet("  lab  ")` zwraca `hello lab`.
KONTEKST: `src/hello.js`.
WYMAGANIA: trim już jest — dodaj test jawny `"  lab  "`.
OGRANICZENIA: bez nowych zależności.
KRYTERIA: nowy test FAIL bez trima, PASS z trimem.
WERYFIKACJA: `npm test`.

### CA-3 CONTRIBUTING one-pager

CEL: `CONTRIBUTING.md` (≤40 linii) opisuje pętlę branch→CI→auto-merge.
KONTEKST: `AGENTS.md` §4–6.
WYMAGANIA: link do issue template; zakaz push do `main` przez agenta.
OGRANICZENIA: nie zmieniaj CI.
KRYTERIA: lint/test/build zielone.
WERYFIKACJA: plik istnieje.

## If CE cutover happens later

1. Create project access token Maintainer (`api` + `read_repository` + `write_repository`).
2. Cursor → GitLab Self-Hosted → Sync Repos (15 min).
3. PASS → keep GitLab as origin; do not dual-push.
4. FAIL → this GitHub repo stays Cloud Agents host; GitLab stays local origin only. Write `D-W2-CE-FAIL` in `DECISIONS.md`.
