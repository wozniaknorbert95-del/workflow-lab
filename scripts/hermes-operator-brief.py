#!/usr/bin/env python3
"""Hermes Engineer voice: step N + playbook path from JSON (C3). No git write."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PLAYBOOK = [
    ("workflow-lab/docs/LINEAR.md", "Linear mobile — issue z 6 polami i etykietą agent"),
    ("workflow-lab/docs/W2-CLOUD-AGENTS.md", "Komentarz @cursor / run Cloud Agent"),
    ("workflow-lab/.cursor/environment.json", "Cloud Agent otwiera PR cursor/*"),
    ("workflow-lab/.github/workflows/ci.yml", "CI validate + execute musi być zielone z realnymi krokami"),
    ("workflow-lab/docs/W6-PHONE-LOOP.md", "GitHub mobile review"),
    ("workflow-lab/DECISIONS.md", "Auto-merge squash na main labu (nie platforma)"),
]

DENY = re.compile(r"\b(git push|gh pr merge|gh api.*merge)\b", re.I)


def brief(state: dict) -> str:
    step = int(state.get("step") or 1)
    status = str(state.get("status") or "UNKNOWN")
    steps = state.get("steps") or []
    cur = next((s for s in steps if s.get("step") == step), {})
    evidence = cur.get("evidence") or []

    if status in ("FAIL", "UNKNOWN"):
        return (
            f"Krok {step}: STOP ({status}). "
            f"Cursor Cloud Agent jest jedynym executorem kodu — Ty napraw warunek, nie merguj. "
            f"Evidence: {json.dumps(evidence, ensure_ascii=False)}"
        )

    path, action = PLAYBOOK[min(step - 1, 5)]
    return (
        f"Krok {step}: {action}. Plik playbooku: {path}. "
        f"Evidence: {json.dumps(evidence, ensure_ascii=False)}. "
        f"Jesteś operatorem — Cursor wykonuje kod."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("json_file", nargs="?", help="phone-loop-status JSON (stdin if omitted)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sample = {"step": 4, "status": "FAIL", "steps": [{"step": 4, "status": "FAIL", "evidence": []}]}
        out = brief(sample)
        if "STOP" not in out or "merguj" not in out.lower():
            print("FAIL self-test: brak STOP przy FAIL")
            return 1
        if not DENY.search("git push origin main"):
            print("FAIL self-test: deny-list nie dziala")
            return 1
        print("PASS: hermes-operator-brief self-test")
        return 0

    raw = sys.stdin.read() if not args.json_file else Path(args.json_file).read_text(encoding="utf-8")
    if DENY.search(raw):
        print("ABORT: polecenie z deny-list w wejściu", file=sys.stderr)
        return 2
    state = json.loads(raw)
    print(brief(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
