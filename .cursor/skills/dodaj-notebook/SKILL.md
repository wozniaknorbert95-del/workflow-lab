---
name: dodaj-notebook
description: Add a Jupyter notebook to workflow-lab's analysis/evidence layer (Python, opt-in). Use when an issue adds or changes notebooks/.
---

# Dodaj notebook (workflow-lab)

Notebooks live in `notebooks/` and are the **opt-in Python analysis layer** — they never touch
the Node core (`greet`, zero-dependency). Use `dodaj-test` for Node behaviour, `dodaj-script` for
npm scripts; use this skill only for `.ipynb` artifacts.

## Steps

1. Confirm the notebook belongs to **analysis/evidence** — not the Node core loop.
2. Create `notebooks/<name>.ipynb` (nbformat 4, kernel `python3`, **no outputs committed**).
3. Add any new third-party import to `requirements.txt` (pinned) — justify in the MR.
4. Add a happy-path cell + one edge cell (mirror of `TESTING.md` doctrine).
5. Run locally: `jupyter nbconvert --to notebook --execute notebooks/<name>.ipynb`.
6. Strip outputs before commit: `nbstripout notebooks/<name>.ipynb`.
7. CI (`.github/workflows/notebooks.yml`) executes every `notebooks/*.ipynb` — it must pass.

## Quality checklist

- [ ] No outputs / no secrets in the committed `.ipynb` (`nbstripout --verify` passes).
- [ ] stdlib preferred; any new dependency is pinned + justified in the MR.
- [ ] Notebook executes on a fresh `ci-kernel` (no reliance on a local venv).
- [ ] No debug `print`/scratch cells left in.
- [ ] `npm run lint && npm test && npm run build` still green (Node core untouched).

## Common mistakes

- Committing outputs (`execution_count`, base64 images) → huge diffs + secret risk.
- Relying on a kernel name saved in notebook metadata → CI overrides with `ci-kernel`.
- Adding a heavyweight dependency for a one-off cell → inline stdlib instead.

## Reference

- CI: `.github/workflows/notebooks.yml` · runner: `scripts/run-notebooks.sh`
- Git hygiene: `.gitattributes` (`*.ipynb filter=nbstripout`)
- Local dev: `notebooks/README.md`
