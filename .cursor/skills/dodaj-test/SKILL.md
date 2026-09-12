---
name: dodaj-test
description: Dodaj test node:test dla workflow-lab — happy path + edge, bez mocków FS. Użyj przy każdej zmianie greet lub nowego modułu src/.
---

# Dodaj test (workflow-lab)

## When to use

Issue changes behaviour in `src/*.js` or fixes a bug in `greet`.

## Steps

1. Read `TESTING.md` — existing cases and rules.
2. Open or create `src/<module>.test.js` (today: only `hello.test.js`).
3. Import: `import { test } from "node:test"` + `import assert from "node:assert/strict"`.
4. Import subject: `import { greet } from "./hello.js"`.
5. Add **happy path** test if new export; add **one edge** (empty, trim, type error).
6. Run `npm test` — must pass before PR.
7. Add a row to the table in `TESTING.md` if user-visible case is new.

## Quality checklist

- [ ] Test fails if you revert the production fix (regression).
- [ ] No `fs` mocks for `greet`.
- [ ] No new npm dependencies.
- [ ] `npm run lint` still passes (`node --check` on test file).

## Common mistakes

- Forgetting to wire new test file in `package.json` `"test"` script.
- Asserting untrimmed input when `greet` trims.
- Using `assert.equal` instead of `assert.strictEqual` for strings.

## Reference

Pattern file: `src/hello.test.js`. Contract doc: `TESTING.md`.
