#!/usr/bin/env python3
"""QUI-162 guard: conductor image must contain every package hermes_conductor.loop imports.

Parses COPY lines of docs/ops/Dockerfile.hermes-conductor, stages them like /app,
then imports in a fresh interpreter with -I -S (no site-packages, no PYTHONPATH):
only stdlib + copied dirs, same as python:3.12-slim. No docker needed.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "docs" / "ops" / "Dockerfile.hermes-conductor"
APP = "/app"
PROBE = (
    "import sys; sys.path.insert(0, sys.argv[1]); "
    "import hermes_conductor.loop; from hermes_conductor.loop import run_once; print('IMPORT_OK')"
)


def copy_lines(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for raw in text.splitlines():
        parts = raw.strip().split()
        if not parts or parts[0].upper() != "COPY":
            continue
        args = [a for a in parts[1:] if not a.startswith("--")]
        if len(args) != 2:
            raise ValueError(f"unsupported COPY line: {raw!r}")
        out.append((args[0], args[1]))
    return out


def stage(pairs: list[tuple[str, str]], dest: Path) -> None:
    for src, dst in pairs:
        if not dst.startswith(APP + "/"):
            raise ValueError(f"COPY target outside {APP}: {dst}")
        s = ROOT / src
        d = dest / dst[len(APP) + 1 :]
        if s.is_dir():
            shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)


def probe(pairs: list[tuple[str, str]]) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        app = Path(tmp) / "app"
        app.mkdir()
        stage(pairs, app)
        return subprocess.run(
            [sys.executable, "-I", "-S", "-c", PROBE, str(app)],
            cwd=str(app),
            capture_output=True,
            text=True,
            timeout=60,
        )


def main() -> int:
    errors: list[str] = []
    pairs = copy_lines(DOCKERFILE.read_text(encoding="utf-8"))
    if not pairs:
        errors.append("T1 no COPY lines parsed")
    r = probe(pairs)
    if r.returncode != 0 or "IMPORT_OK" not in r.stdout:
        tail = (r.stderr or "").strip().splitlines()[-1:] or [""]
        errors.append(f"T1 image import failed: {tail[0]}")
    # T2: guard really catches the QUI-162 regression (image without hermes_ops).
    broken = [p for p in pairs if not p[1].rstrip("/").endswith("/hermes_ops")]
    r2 = probe(broken)
    if r2.returncode == 0 or "hermes_ops" not in (r2.stderr or ""):
        errors.append("T2 guard must fail without COPY scripts/hermes_ops")
    if errors:
        for e in errors:
            print(f"FAIL {e}")
        return 1
    print(f"PASS test_conductor_image ({len(pairs)} COPY lines, -I -S stdlib-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
