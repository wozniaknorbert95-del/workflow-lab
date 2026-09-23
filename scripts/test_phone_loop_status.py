#!/usr/bin/env python3
"""Tests phone-loop-status fixtures + fail-closed (no default PASS)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "scripts" / "phone-loop-status.py"


def load_mod():
    spec = importlib.util.spec_from_file_location("phone_loop_status_mod", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = load_mod()
    errors: list[str] = []

    happy = mod.load_fixture("happy")
    h = mod.evaluate_from_fixture(happy)
    if h["step"] != 6 or h["status"] != "PASS":
        errors.append(f"happy: expected step 6 PASS, got {h['step']} {h['status']}")
    if not all(s.get("evidence") for s in h["steps"] if s["status"] == "PASS"):
        errors.append("happy: PASS step without evidence")

    red = mod.load_fixture("ci_red")
    r = mod.evaluate_from_fixture(red)
    if r["status"] == "PASS":
        errors.append("ci_red: must not be PASS")
    if r["step"] != 4:
        errors.append(f"ci_red: expected stuck at step 4, got {r['step']}")

    nt = mod.load_fixture("no_token")
    n = mod.evaluate_from_fixture(nt)
    if n["status"] != "UNKNOWN":
        errors.append(f"no_token: expected UNKNOWN, got {n['status']}")

    # Mutacja guard: default empty fixture must not PASS
    empty = mod.evaluate_from_fixture({})
    if empty["status"] == "PASS":
        errors.append("empty fixture must not PASS")

    # Draft PR: S6 names the D-AUTOMERGE skip, not a generic "not merged".
    draft = {
        "linear": happy["linear"],
        "github": {**happy["github"], "draft": True},
        "checks": happy["checks"],
        "review": happy["review"],
        "merge": {"squash_on_main": False},
    }
    d = mod.evaluate_from_fixture(draft)
    s6 = next((s for s in d["steps"] if s.get("step") == 6), {})
    if s6.get("status") != "FAIL" or s6.get("reason") != "pr is draft (automerge skipped)":
        errors.append(f"draft PR S6 expected FAIL 'pr is draft (automerge skipped)', got {s6}")

    if errors:
        print("FAIL phone-loop-status:")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS: phone-loop-status fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
