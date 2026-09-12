---
name: dodaj-script
description: Dodaj npm script z parity CI — package.json, AGENTS.md §2, GitHub + GitLab yaml. Użyj gdy issue wymaga nowej komendy projektu.
---

# Dodaj script (workflow-lab)

## When to use

Issue asks for a new repeatable command (e.g. `verify`, `diag`, `precommit`).

## Steps

1. Confirm the command belongs in **this lab** — not platform tooling.
2. Add script to `package.json` `"scripts"` — keep zero npm deps (prefer `node` invocations).
3. Update **all parity surfaces** in one MR:
   - `AGENTS.md` §2 (Project commands)
   - `README.md` Komendy section
   - `.github/workflows/ci.yml` if CI must run it
   - `.gitlab-ci.yml` if CI must run it
   - `TESTING.md` if it is a test/lint/build sibling
4. Run the new script locally; run full gate: `npm run lint && npm test && npm run build`.
5. Document in MR **why** the script exists (one sentence).

## Quality checklist

- [ ] No duplicate command names (`typecheck` is forbidden — see AGENTS.md).
- [ ] Script works on fresh clone without `npm install`.
- [ ] CI and local use the **same** `npm run <name>` invocation.
- [ ] No secrets or env vars required for default path.

## Common mistakes

- Adding script only to `package.json` but not AGENTS.md (A2 audit FAIL).
- Shell-specific syntax that breaks Cloud Agent Linux VM.
- Adding eslint/prettier as dependency — out of scope unless architecture change in `DECISIONS.md`.

## Reference

Current truth: `package.json` scripts `lint`, `test`, `build`. CI: `.github/workflows/ci.yml` job `validate`.
