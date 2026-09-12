---
name: review-bezpieczenstwa
description: Review MR/PR workflow-lab pod kątem sekretów, scope creep i CI parity. Użyj przed zgłoszeniem MR.
---

# Review bezpieczeństwa (lab)

1. `git diff` — czy wyciekł token, `.env`, hasło, klucz?
2. Czy CI nadal = `npm run lint` + `npm test` + `npm run build` (AGENTS.md §2)?
3. Czy MR nie ciągnie plików z `dsaas-platform-main` / akademii?
4. Czy nie ma dual-origin / force-push / `--no-verify`?
5. Wynik: PASS albo lista blockerów. Nie zgaduj.
