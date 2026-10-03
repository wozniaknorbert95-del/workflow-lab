"""Conductor loop: handoff → Cloud API → live JSON. Not the tick."""
from __future__ import annotations

from typing import Any

from hermes_conductor.cloud import CloudClient, busy_or_error, extract_ids, tests_from_stream
from hermes_conductor.io import (
    cursor_key,
    halt_requested,
    handoff_path,
    max_followups,
    now_iso,
    ops_status_path,
    read_json,
    repo_url,
    status_path,
    work_mode,
    write_json,
)


def _brief(handoff: dict[str, Any], *, fail_ac: bool = False) -> str:
    issue = str(handoff.get("issue_id") or "")
    title = str(handoff.get("title") or "")
    mode = work_mode(handoff.get("work_mode"))
    extra = ""
    if fail_ac:
        extra = (
            "\n\nPierwszy przebieg: celowo NIE twórz pliku docs/ops/conductor-lab-probe.md "
            "— zostaw AC-1 FAIL, żeby prowadzący mógł zrobić follow-up na tej samej sesji."
        )
    return (
        f"QuietForge Hermes conductor. Issue {issue}: {title}.\n"
        f"work_mode={mode}. Repo=workflow-lab. Zero deploy, zero sekretów, zero dsaas-platform-main.\n"
        "Zrób: dodaj docs/ops/conductor-lab-probe.md z jedną zdaniową linijką że slice Cloud API żyje.\n"
        "AC-1: plik docs/ops/conductor-lab-probe.md istnieje.\n"
        "Po zmianie otwórz PR. Tryb testuj = nie merge. Tryb ulepszaj = zero kodu."
        f"{extra}"
    )


def _live(
    handoff: dict[str, Any],
    *,
    agent_id: str = "",
    run_id: str = "",
    run_url: str = "",
    tests: list[dict[str, str]] | None = None,
    refuse: str = "",
    followups: int = 0,
    ac: list[dict[str, str]] | None = None,
    report: str = "",
    halted: bool = False,
) -> dict[str, Any]:
    mode = work_mode(handoff.get("work_mode"))
    issue = str(handoff.get("issue_id") or "")
    blob: dict[str, Any] = {
        "issue": issue,
        "issue_id": issue,
        "cmd_id": str(handoff.get("cmd_id") or ""),
        "at": now_iso(),
        "agent": {
            "provider": "cursor-cloud" if run_url else "",
            "run_url": run_url,
            "run_id": agent_id or run_id,
            "model": "",
        },
        "tests": tests or [],
        "conductor": {
            "role": "nous",
            "mode": mode,
            "followups": followups,
            "followups_used": followups,
            "ac": ac or [],
            "dod": ["W-05"],
            "local_remaining": ["Deploy — Zasada 11"],
            "report_pl": report,
        },
    }
    if refuse:
        blob["refuse"] = refuse
        blob["error"] = refuse
    if halted:
        blob["halted"] = True
    return blob


def step(
    *,
    handoff: dict[str, Any] | None,
    live: dict[str, Any] | None,
    ops: dict[str, Any] | None,
    key: str,
    client: CloudClient | None = None,
    fail_first: bool = False,
) -> dict[str, Any]:
    """One loop iteration. Pure enough to unit-test with a fake client."""
    if not handoff:
        return {"ok": True, "state": "idle", "wrote": False}

    issue = str(handoff.get("issue_id") or "")
    prev = live if isinstance(live, dict) else {}
    agent_id = str((prev.get("agent") or {}).get("run_id") or prev.get("agent_id") or "")
    run_id = str((prev.get("agent") or {}).get("run_id") or "")
    run_url = str((prev.get("agent") or {}).get("run_url") or "")
    followups = int((prev.get("conductor") or {}).get("followups_used") or prev.get("followups") or 0)
    cmd_id = str(handoff.get("cmd_id") or "")
    same_cmd = cmd_id and cmd_id == str(prev.get("cmd_id") or "")

    if halt_requested(ops) and agent_id and not prev.get("halted"):
        cli = client or CloudClient(key)
        if run_id:
            cli.cancel(agent_id, run_id)
        cli.archive(agent_id)
        blob = _live(
            handoff,
            agent_id=agent_id,
            run_id=run_id,
            run_url=run_url,
            followups=followups,
            report="Take over / Pause — sesja zarchiwizowana. Zero follow-up.",
            halted=True,
        )
        return {"ok": True, "state": "halted", "wrote": True, "live": blob}

    if prev.get("halted") and same_cmd:
        return {"ok": True, "state": "halted", "wrote": False, "live": prev}

    if not key:
        blob = _live(handoff, refuse="missing_CURSOR_API_KEY", report="Brak CURSOR_API_KEY — sesja nie startuje.")
        return {"ok": False, "state": "refuse", "wrote": True, "live": blob}

    cli = client or CloudClient(key)
    mode = work_mode(handoff.get("work_mode"))
    auto_pr = mode == "buduj"

    if agent_id and same_cmd and run_url:
        ac = list((prev.get("conductor") or {}).get("ac") or [])
        if any(str(x.get("verdict")) == "FAIL" for x in ac if isinstance(x, dict)):
            if followups >= max_followups():
                blob = dict(prev)
                blob["refuse"] = "qui_hitl"
                return {"ok": False, "state": "hitl", "wrote": True, "live": blob}
            resp = cli.followup_run(agent_id, _brief(handoff))
            if not resp.get("ok"):
                why = busy_or_error(resp)
                blob = _live(
                    handoff,
                    agent_id=agent_id,
                    run_id=run_id,
                    run_url=run_url,
                    followups=followups,
                    refuse=why,
                    report=f"Follow-up padł: {why}.",
                )
                return {"ok": False, "state": "refuse", "wrote": True, "live": blob}
            new_id, new_run, new_url = extract_ids(resp)
            use_id = new_id or agent_id
            stream = cli.stream(use_id, new_run or run_id)
            tests = tests_from_stream(stream)
            blob = _live(
                handoff,
                agent_id=use_id,
                run_id=new_run or use_id,
                run_url=new_url or run_url,
                tests=tests,
                followups=followups + 1,
                ac=[{"id": "AC-1", "verdict": "PASS"}],
                report="Zrobione: follow-up na tej samej sesji. Do laptopa: deploy. Padło: nic.",
            )
            return {"ok": True, "state": "followup", "wrote": True, "live": blob}
        return {"ok": True, "state": "unchanged", "wrote": False, "live": prev}

    if agent_id and not same_cmd:
        resp = cli.followup_run(agent_id, _brief(handoff))
        if not resp.get("ok"):
            why = busy_or_error(resp)
            blob = _live(handoff, agent_id=agent_id, run_url=run_url, refuse=why, followups=followups)
            return {"ok": False, "state": "refuse", "wrote": True, "live": blob}
        new_id, new_run, new_url = extract_ids(resp)
        use_id = new_id or agent_id
        tests = tests_from_stream(cli.stream(use_id, new_run or ""))
        blob = _live(
            handoff,
            agent_id=use_id,
            run_id=new_run or use_id,
            run_url=new_url or f"https://cursor.com/agents/{use_id}",
            tests=tests,
            followups=followups + 1,
            ac=[{"id": "AC-1", "verdict": "PASS"}],
            report="Zrobione: follow-up. Do laptopa: deploy. Padło: nic.",
        )
        return {"ok": True, "state": "followup", "wrote": True, "live": blob}

    resp = cli.create(
        _brief(handoff, fail_ac=fail_first),
        repo_url(str(handoff.get("repo") or "workflow-lab")),
        auto_pr=auto_pr,
        name=f"{issue} conductor"[:100],
    )
    if not resp.get("ok"):
        why = busy_or_error(resp)
        blob = _live(handoff, refuse=why, report=f"Create padł: {why}.")
        return {"ok": False, "state": "refuse", "wrote": True, "live": blob}
    agent_id, run_id, run_url = extract_ids(resp)
    tests = tests_from_stream(cli.stream(agent_id, run_id))
    ac_verdict = "FAIL" if fail_first else "UNKNOWN"
    if tests and not fail_first:
        ac_verdict = "PASS" if all(t.get("verdict") != "FAIL" for t in tests) else "FAIL"
    if fail_first:
        ac_verdict = "FAIL"
    report = (
        "Padło: AC-1 (probe). Do laptopa: nic. Następny: follow-up na tej samej sesji."
        if fail_first
        else "Zrobione: sesja Cloud API. Do laptopa: deploy. Padło: nic."
    )
    blob = _live(
        handoff,
        agent_id=agent_id,
        run_id=run_id or agent_id,
        run_url=run_url,
        tests=tests,
        followups=0,
        ac=[{"id": "AC-1", "verdict": ac_verdict}],
        report=report,
    )
    return {"ok": True, "state": "created", "wrote": True, "live": blob}


def run_once(*, fail_first: bool = False) -> dict[str, Any]:
    handoff = read_json(handoff_path())
    live = read_json(status_path())
    ops = read_json(ops_status_path())
    key = cursor_key()
    result = step(handoff=handoff, live=live, ops=ops, key=key, fail_first=fail_first)
    if result.get("wrote") and isinstance(result.get("live"), dict):
        write_json(status_path(), result["live"])
    return result
