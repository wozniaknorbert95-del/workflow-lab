# notebooks/ — analysis & evidence layer (opt-in Python)

This directory is the **analysis/evidence layer** of `workflow-lab`. It is Python, and it is
**strictly separate** from the Node 20 zero-dependency core (`greet`, `npm run lint/test/build`).

- Notebooks are reproducible artifacts: cost reports, CI metrics, digest analysis, smoke evidence.
- They do **not** import the Node core, and the Node core never depends on them.

## Local run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Headless check of a single notebook:

```bash
jupyter nbconvert --to notebook --execute notebooks/hello-analysis.ipynb \
  --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=600
```

## CI contract

`.github/workflows/notebooks.yml` (and the GitLab `notebooks` job) run every `notebooks/*.ipynb`
headless via `scripts/run-notebooks.sh` with a fresh `ci-kernel`. The job is **path-filtered** —
it does not run on the Node core loop and it does not slow down Node-only PRs.

## Git hygiene

Outputs are **never committed**. The repo ships `.gitattributes` with the `nbstripout` filter and
CI runs `nbstripout --verify`. If you edit a notebook and git shows diff noise, run:

```bash
nbstripout notebooks/<name>.ipynb
```

## Adding a notebook

Use skill `dodaj-notebook` (`.cursor/skills/dodaj-notebook/`). Happy path + one edge cell, stdlib
preferred, any new third-party import goes in `requirements.txt` (pinned) with MR justification.
