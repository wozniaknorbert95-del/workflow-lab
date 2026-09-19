# How to contribute (workflow-lab)

1. Open an issue with the [6-field template](.github/ISSUE_TEMPLATE/agent-task.md) (`Cel / Kontekst / Wymagania / Ograniczenia / Kryteria / Weryfikacja`).
2. Branch `feat|fix|chore/<short>` from `main`. Never push to `main`.
3. `npm run lint && npm test && npm run build` (same as CI; there is no typecheck).
4. Open a PR linking `Closes #N`.
5. Wait for green CI. **Auto-merge** merges the PR (D-AUTOMERGE). Agents never push to `main`.

This gym is not `dsaas-platform-main` and not the Academy. Do not mix.
