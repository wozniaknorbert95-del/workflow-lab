#!/usr/bin/env python3
"""Deterministic Telefon loop state S1–S6 (PASS/FAIL/UNKNOWN). LLM is not the judge."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "scripts" / "fixtures" / "phone-loop"

DEFAULT_TTL_MIN = 15


def _step(step: int, status: str, evidence: list | None = None, reason: str = "") -> dict:
    return {
        "step": step,
        "status": status,
        "evidence": evidence or [],
        "reason": reason,
    }


def _unknown(step: int, reason: str) -> dict:
    return _step(step, "UNKNOWN", [{"kind": "unknown", "detail": reason}], reason)


def evaluate_from_fixture(data: dict[str, Any]) -> dict[str, Any]:
    """Pure evaluation from captured API-shaped fixture (tests + offline)."""
    steps: list[dict] = []
    linear = data.get("linear") or {}
    github = data.get("github") or {}
    checks = data.get("checks") or {}
    review = data.get("review") or {}
    merge = data.get("merge") or {}

    # S1
    if linear.get("missing_token"):
        steps.append(_unknown(1, "linear token missing"))
    elif linear.get("issue_id") and linear.get("six_fields") and linear.get("agent_label"):
        steps.append(_step(1, "PASS", [{"kind": "linear_issue", "id": str(linear["issue_id"])}]))
    else:
        steps.append(_step(1, "FAIL", reason="issue missing 6 fields or agent label"))

    # S2
    if github.get("missing_token"):
        steps.append(_unknown(2, "github token missing"))
    elif github.get("cursor_comment") or github.get("cloud_run_id") or str(
        github.get("head_ref") or ""
    ).startswith("cursor/"):
        ev = {"kind": "cursor_trigger"}
        if github.get("cursor_comment"):
            ev["comment"] = "present"
        if github.get("cloud_run_id"):
            ev["run_id"] = str(github["cloud_run_id"])
        steps.append(_step(2, "PASS", [ev]))
    else:
        steps.append(_step(2, "FAIL", reason="no @cursor comment or cloud run"))

    # S3
    pr_url = github.get("pr_url") or ""
    head_ref = str(github.get("head_ref") or "")
    if github.get("missing_token"):
        steps.append(_unknown(3, "github token missing"))
    elif pr_url.startswith("https://") and (head_ref.startswith("cursor/") or "/cursor/" in pr_url):
        steps.append(_step(3, "PASS", [{"kind": "pr", "url": pr_url, "head": head_ref or "cursor/*"}]))
    else:
        steps.append(_step(3, "FAIL", reason="no cursor/* PR URL"))

    # S4
    if checks.get("missing_token"):
        steps.append(_unknown(4, "github checks token missing"))
    elif checks.get("validate") == "success" and (
        checks.get("execute") == "success"
        or checks.get("execute") in ("skipped", None)
        or merge.get("squash_on_main")
    ):
        if not checks.get("jobs_ran_steps") and not merge.get("squash_on_main"):
            steps.append(
                _step(
                    4,
                    "FAIL",
                    reason="validate/execute green but job did not run steps (docs-only false green)",
                )
            )
        else:
            steps.append(
                _step(
                    4,
                    "PASS",
                    [
                        {"kind": "check", "name": "validate", "conclusion": "success"},
                        {"kind": "check", "name": "execute", "conclusion": "success"},
                    ],
                )
            )
    elif checks.get("validate") or checks.get("execute"):
        steps.append(_step(4, "FAIL", reason="CI not fully green"))
    else:
        steps.append(_unknown(4, "checks not available"))

    # S5
    if review.get("missing_policy"):
        steps.append(_unknown(5, "review policy unknown"))
    elif review.get("approved"):
        steps.append(_step(5, "PASS", [{"kind": "review", "state": "approved"}]))
    else:
        steps.append(_step(5, "FAIL", reason="mobile review not satisfied"))

    # S6
    if merge.get("missing_token"):
        steps.append(_unknown(6, "merge state unknown"))
    elif merge.get("squash_on_main"):
        sha = str(merge.get("sha") or "")
        steps.append(_step(6, "PASS", [{"kind": "merge", "method": "squash", "sha": sha}]))
    elif github.get("draft") or merge.get("draft"):
        steps.append(_step(6, "FAIL", reason="pr is draft (automerge skipped)"))
    else:
        steps.append(_step(6, "FAIL", reason="not merged to main"))

    current = 1
    for sr in steps:
        if sr["status"] == "PASS" and sr["step"] == current:
            current = min(6, current + 1)
        elif sr["status"] in ("FAIL", "UNKNOWN"):
            current = sr["step"]
            break
    else:
        current = 6 if steps and steps[-1]["status"] == "PASS" and steps[-1]["step"] == 6 else current

    overall = "PASS" if current == 6 and steps[-1]["status"] == "PASS" else steps[current - 1]["status"]

    return {
        "step": current,
        "status": overall,
        "steps": steps,
        "ttl_minutes": data.get("ttl_minutes", DEFAULT_TTL_MIN),
        "issue_id": linear.get("issue_id"),
    }


def load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", help="happy | ci_red | no_token")
    ap.add_argument("--pr", type=int, default=0, help="Live: GitHub PR number")
    ap.add_argument("--issue", type=int, default=0, help="Live: GitHub issue number")
    ap.add_argument(
        "--env-file",
        default=os.environ.get("HERMES_ENGINEER_ENV", "/etc/workflow-lab/hermes-engineer.env"),
    )
    ap.add_argument("--issue-id", default=os.environ.get("PHONE_LOOP_ISSUE_ID", ""))
    args = ap.parse_args()

    if args.fixture:
        data = load_fixture(args.fixture)
    elif args.pr or args.issue:
        from phone_loop_github import build_live_payload, token_from_env_file

        token = os.environ.get("GITHUB_ENGINEER_TOKEN") or token_from_env_file(args.env_file)
        data = build_live_payload(
            pr_number=args.pr or None,
            issue_number=args.issue or None,
            token=token,
        )
    else:
        data = {
            "linear": {"missing_token": True},
            "github": {"missing_token": True},
            "checks": {"missing_token": True},
            "review": {"missing_policy": True},
            "merge": {"missing_token": True},
            "ttl_minutes": DEFAULT_TTL_MIN,
        }

    out = evaluate_from_fixture(data)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
