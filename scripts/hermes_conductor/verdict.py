"""Tool D (QUI-163): verdict after a Cloud run ends. Pure, no network.

Inputs: run snapshot (Cloud API), ops-status live (tick: S3 PR, S4 checks),
AC ids, work mode. Output: verdict + next action. No evidence = UNKNOWN, never PASS.
"""
from __future__ import annotations

import re
from typing import Any

# Agent's final reply markers. STOP/HITL = legit stop (no follow-up).
_STOP_RX = re.compile(r"\b(STOP-LINEAR|HITL)\b|\bSTOP\b")
_FAIL_RX = re.compile(r"\b(PARTIAL|FAIL(?:ED)?)\b")


def _step(ops_live: dict[str, Any], n: int) -> dict[str, Any]:
    for item in ops_live.get("steps") or []:
        if isinstance(item, dict) and int(item.get("step") or 0) == n:
            return item
    return {}


def ac_from_result(ac_ids: list[str], result: str) -> list[dict[str, str]]:
    """Per-AC verdict only from an explicit line `AC-n … PASS|FAIL` in the agent reply."""
    lines = [ln.strip() for ln in str(result or "").splitlines() if ln.strip()]
    out: list[dict[str, str]] = []
    for aid in ac_ids:
        verdict = "UNKNOWN"
        rx = re.compile(rf"(?<![\w-]){re.escape(aid)}(?![\w])", re.IGNORECASE)
        for ln in lines:
            if not rx.search(ln):
                continue
            up = ln.upper()
            if re.search(r"\bFAIL\b", up):
                verdict = "FAIL"
                break
            if re.search(r"\bPASS\b", up):
                verdict = "PASS"
        out.append({"id": aid[:80], "verdict": verdict})
    return out


def tool_d(
    *,
    run: dict[str, Any],
    ops_live: dict[str, Any] | None,
    issue: str,
    ac_ids: list[str],
    auto_pr: bool,
) -> dict[str, Any]:
    """Return {verdict, action, reasons[], steer, ac[], pr_url}.

    action: done | followup | hitl | wait (CI pending).
    """
    status = str(run.get("status") or "").upper()
    result = str(run.get("result") or "")
    reasons: list[str] = []
    live = ops_live if isinstance(ops_live, dict) else {}
    live_issue = str(live.get("issue") or live.get("issue_id") or "").strip()
    if live_issue and issue and live_issue != issue:
        live = {}
    pr_url = str(run.get("pr_url") or live.get("pr_url") or "")
    ac = ac_from_result(ac_ids, result)

    if status in ("CANCELLED", "EXPIRED"):
        return {"verdict": "FAIL", "action": "hitl", "reasons": [f"run {status}"], "steer": "", "ac": ac, "pr_url": pr_url}
    if status == "ERROR":
        return {
            "verdict": "FAIL",
            "action": "followup",
            "reasons": ["run ERROR"],
            "steer": "Poprzedni run zakończył się błędem. Dokończ zadanie od miejsca, w którym przerwałeś.",
            "ac": ac,
            "pr_url": pr_url,
        }

    upper = result.upper()
    if _STOP_RX.search(upper):
        return {
            "verdict": "UNKNOWN",
            "action": "hitl",
            "reasons": ["agent zgłosił STOP/HITL"],
            "steer": "",
            "ac": ac,
            "pr_url": pr_url,
        }

    steer: list[str] = []
    verdict = "PASS"
    if _FAIL_RX.search(upper):
        verdict = "FAIL"
        reasons.append("agent: PARTIAL/FAIL w raporcie")
        steer.append("Raport kończy się PARTIAL/FAIL: domknij brakujące AC")
    failed = [x["id"] for x in ac if x["verdict"] == "FAIL"]
    if failed:
        verdict = "FAIL"
        reasons.append("AC FAIL: " + ", ".join(failed))
        steer.append("AC FAIL: " + ", ".join(failed))

    if auto_pr:
        if not pr_url:
            verdict = "FAIL"
            reasons.append("S3 brak PR")
            steer.append(
                "Brak PR: wypchnij gałąź z commitem i zakończ run — Cursor otworzy PR automatycznie; nie otwieraj go ręcznie"
            )
        else:
            s4 = _step(live, 4)
            s4_status = str(s4.get("status") or "UNKNOWN").upper()
            if s4_status == "FAIL":
                verdict = "FAIL"
                why = str(s4.get("reason") or "CI czerwone")[:120]
                reasons.append(f"S4 FAIL: {why}")
                steer.append(f"Wymagane checki CI czerwone ({why}): napraw i wypchnij")
            elif s4_status != "PASS" and verdict != "FAIL":
                return {
                    "verdict": "UNKNOWN",
                    "action": "wait",
                    "reasons": ["S4 czekam na CI"],
                    "steer": "",
                    "ac": ac,
                    "pr_url": pr_url,
                }
    elif verdict != "FAIL":
        reasons.append("PR wyłączony w tym trybie")

    if verdict == "FAIL":
        return {
            "verdict": "FAIL",
            "action": "followup",
            "reasons": reasons,
            "steer": ". ".join(steer) + ".",
            "ac": ac,
            "pr_url": pr_url,
        }
    if not ac or any(x["verdict"] != "PASS" for x in ac):
        reasons.append("AC bez dowodu w raporcie agenta = UNKNOWN")
        verdict = "UNKNOWN"
    if not auto_pr and verdict == "PASS":
        verdict = "UNKNOWN"
    return {"verdict": verdict, "action": "done", "reasons": reasons, "steer": "", "ac": ac, "pr_url": pr_url}
