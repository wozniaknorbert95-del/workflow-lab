"""Validate Hermes Ops token shapes — never log values. Used by push script + CI."""
from __future__ import annotations


def validate_linear_ops_read(token: str) -> tuple[bool, str]:
    t = (token or "").strip()
    if not t:
        return False, "empty"
    if t.startswith("gho_") or t.startswith("github_pat_") or t.startswith("ghp_"):
        return False, "not_linear"
    if t.startswith("lin_api_"):
        return True, "ok"
    if len(t) >= 20:
        return True, "ok_len"
    return False, "too_short"


def validate_github_ops_write(token: str) -> tuple[bool, str]:
    t = (token or "").strip()
    if not t:
        return False, "empty"
    if t.startswith("gho_"):
        return False, "reject_gho_oauth"
    if t.startswith("github_pat_") or t.startswith("ghp_"):
        return True, "ok"
    return False, "bad_prefix"


def main() -> int:
    errors: list[str] = []
    ok, reason = validate_github_ops_write("gho_SECRETBAD")
    if ok or reason != "reject_gho_oauth":
        errors.append(f"gho_ must reject, got {ok} {reason}")
    ok, reason = validate_github_ops_write("github_pat_abcdefghijklmnop")
    if not ok:
        errors.append(f"github_pat_ must accept, got {reason}")
    ok, reason = validate_github_ops_write("ghp_abcdefghijklmnop")
    if not ok:
        errors.append(f"ghp_ must accept, got {reason}")
    ok, reason = validate_linear_ops_read("lin_api_abcdefghijklmnop")
    if not ok:
        errors.append(f"lin_api_ must accept, got {reason}")
    ok, reason = validate_linear_ops_read("gho_nope")
    if ok:
        errors.append("linear must reject gho_")
    ok, reason = validate_linear_ops_read("short")
    if ok:
        errors.append("short linear must fail")
    if errors:
        print("FAIL:")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS: ops_token_validate (reject gho_, accept pat/lin_api)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
