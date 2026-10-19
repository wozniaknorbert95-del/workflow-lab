"""Conductor loop: handoff → Cloud API → live JSON. Not the tick."""
from __future__ import annotations

import time
from typing import Any

from hermes_conductor.cloud import (
    CloudClient,
    busy_or_error,
    extract_ids,
    recover_agent_by_name,
    tests_from_stream,
)
from hermes_ops.issue_brief import build_issue_json, issue_json_block
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


PLATFORM_REPO = "dsaas-platform-main"


def _tests(cli: CloudClient, agent_id: str, run_id: str) -> list[dict[str, str]]:
    try:
        return tests_from_stream(cli.stream(agent_id, run_id))
    except Exception:
        return []


def _brief_kind(handoff: dict[str, Any]) -> str:
    kind = str(handoff.get("brief_kind") or "").strip().lower()
    if kind in ("lab_probe", "real"):
        return kind
    # Smoke defaults (QUI-13x) when handoff pre-dates enrich.
    issue = str(handoff.get("issue_id") or "").strip().upper()
    if issue in ("QUI-129", "QUI-130", "QUI-131"):
        return "lab_probe"
    return "real"


def _mode_rules(mode: str) -> str:
    if mode == "testuj":
        return "Tryb testuj: dowód bez merge (autoCreatePR off)."
    if mode == "ulepszaj":
        return "Tryb ulepszaj: jedna propozycja / draft — zero kodu, zero PR."
    return "Tryb buduj: wdróż issue, otwórz PR po zmianie."


def _ac_lines(handoff: dict[str, Any]) -> list[str]:
    raw = handoff.get("ac")
    out: list[str] = []
    if isinstance(raw, list):
        for item in raw[:20]:
            if isinstance(item, dict):
                text = str(item.get("id") or item.get("label") or "").strip()
            else:
                text = str(item).strip()
            if text:
                out.append(text[:160])
    return out


def _dor_block(handoff: dict[str, Any]) -> str:
    excerpts = handoff.get("dor_excerpts") if isinstance(handoff.get("dor_excerpts"), dict) else {}
    prefer = ("cel", "kryteria akceptacji", "ograniczenia", "wymagania", "weryfikacja", "kontekst")
    lines: list[str] = []
    for key in prefer:
        val = str(excerpts.get(key) or "").strip()
        if val:
            lines.append(f"## {key}\n{val[:600]}")
    return "\n\n".join(lines)


def _issue_json(handoff: dict[str, Any]) -> dict[str, Any]:
    """Handoff ISSUE-JSON v1; a pre-QUI-153 handoff gets a bare one (preflight → STOP-LINEAR)."""
    blob = handoff.get("issue_json")
    if isinstance(blob, dict) and blob.get("id"):
        return blob
    return build_issue_json(
        {
            "id": handoff.get("issue_id"),
            "title": handoff.get("title"),
            "labels": handoff.get("labels") or [],
            "repo": handoff.get("repo"),
        }
    )


def _brief(handoff: dict[str, Any], *, fail_ac: bool = False, steer: bool = False) -> str:
    issue = str(handoff.get("issue_id") or "")
    title = str(handoff.get("title") or "")
    mode = work_mode(handoff.get("work_mode"))
    kind = _brief_kind(handoff)
    if kind == "lab_probe":
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

    repo = str(handoff.get("repo") or "workflow-lab").strip() or "workflow-lab"
    url = str(handoff.get("url") or "").strip()
    if not url and issue:
        url = f"https://linear.app/quietforge/issue/{issue}"
    ac = _ac_lines(handoff)
    ac_block = "\n".join(f"- {x}" for x in ac) if ac else "- (brak checklisty w handoff — czytaj Linear URL / kryteria w dor_excerpts)"
    dor = _dor_block(handoff)
    dor_part = f"\n\nDoR (sanitized excerpts):\n{dor}" if dor else ""
    steer_part = ""
    if steer:
        failed = []
        prev_ac = handoff.get("_steer_ac")
        if isinstance(prev_ac, list):
            for item in prev_ac:
                if isinstance(item, dict) and str(item.get("verdict")) == "FAIL":
                    failed.append(str(item.get("id") or ""))
        if not failed:
            failed = [x.split(":")[0].strip() for x in ac] or ["AC"]
        steer_part = (
            "\n\nFOLLOW-UP (ta sama sesja): domknij brakujące "
            + ", ".join(f for f in failed if f)
            + ". Trzymaj kontrakt /autopilot — nie zaczynaj od zera."
        )
    playbook = (
        "Playbook: wykonaj kontrakt `.cursor/commands/autopilot.md` w tym repo "
        "(preflight → plan → kod 1 atom → gate → verify → evidence → Stan sesji w PR; max 3 atomy). "
        "Nie kończ po samym odczytaniu promptu — domknij AC albo jawny FAIL/HITL/STOP."
    )
    if repo != "dsaas-platform-main":
        playbook += (
            " Jeśli brak `.cursor/commands/autopilot.md`, stosuj ten sam łańcuch "
            "(plan → implement → test → PR) i nie wymyślaj deployu."
        )
    issue_part = ""
    if repo == PLATFORM_REPO:
        issue_part = "\n\n" + issue_json_block(_issue_json(handoff))
    return (
        f"QuietForge Hermes conductor (real Autopilot). Issue {issue}: {title}.\n"
        f"Linear: {url}\n"
        f"work_mode={mode}. Repo={repo}.\n"
        "Zakazy: zero deploy, zero SSH prod, zero sekretów, zero workflow_dispatch, zero push main.\n"
        f"{_mode_rules(mode)}\n"
        f"{playbook}\n"
        f"AC do domknięcia:\n{ac_block}"
        f"{issue_part}"
        f"{dor_part}"
        f"{steer_part}"
    )


def _ac_seed(handoff: dict[str, Any], *, fail_first: bool) -> list[dict[str, str]]:
    kind = _brief_kind(handoff)
    if kind == "lab_probe":
        return [{"id": "AC-1", "verdict": "FAIL" if fail_first else "UNKNOWN"}]
    lines = _ac_lines(handoff)
    if not lines:
        return [{"id": "AC-1", "verdict": "UNKNOWN"}]
    out: list[dict[str, str]] = []
    for i, line in enumerate(lines[:20]):
        aid = line.split(":", 1)[0].strip() if ":" in line else f"AC-{i + 1}"
        if not aid.startswith("AC"):
            aid = f"AC-{i + 1}"
        out.append({"id": aid[:80], "verdict": "UNKNOWN"})
    return out


def _steer_brief(handoff: dict[str, Any], prev: dict[str, Any]) -> str:
    payload = dict(handoff)
    payload["_steer_ac"] = list((prev.get("conductor") or {}).get("ac") or [])
    return _brief(payload, steer=True)


def _agent_fields(prev: dict[str, Any]) -> tuple[str, str, str]:
    agent = prev.get("agent") if isinstance(prev.get("agent"), dict) else {}
    agent_id = str(agent.get("agent_id") or prev.get("agent_id") or "")
    run_id = str(agent.get("run_id") or "")
    # Legacy: older live stored agent_id inside run_id.
    if not agent_id and run_id.startswith("bc-"):
        agent_id = run_id
        run_id = ""
    if not agent_id:
        agent_id = str(prev.get("agent_id") or "")
    run_url = str(agent.get("run_url") or "")
    return agent_id, run_id, run_url


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
    create_ms: int | None = None,
    http_code: int | None = None,
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
            "agent_id": agent_id,
            "run_id": run_id,
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
    if create_ms is not None:
        blob["create_ms"] = int(create_ms)
    if http_code is not None:
        blob["http"] = int(http_code)
    if refuse:
        blob["refuse"] = refuse
        blob["error"] = refuse
    if halted:
        blob["halted"] = True
    return blob


def _ac_fail(prev: dict[str, Any]) -> bool:
    ac = list((prev.get("conductor") or {}).get("ac") or [])
    return any(str(x.get("verdict")) == "FAIL" for x in ac if isinstance(x, dict))


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

    issue = str(handoff.get("issue_id") or "").strip()
    if not issue:
        return {"ok": True, "state": "idle", "wrote": False}

    prev = live if isinstance(live, dict) else {}
    agent_id, run_id, run_url = _agent_fields(prev)
    followups = int((prev.get("conductor") or {}).get("followups_used") or prev.get("followups") or 0)
    cmd_id = str(handoff.get("cmd_id") or "").strip()
    same_cmd = bool(cmd_id and cmd_id == str(prev.get("cmd_id") or "").strip())
    same_issue = bool(issue and issue == str(prev.get("issue") or prev.get("issue_id") or "").strip())

    # Fail-closed: empty cmd_id must never create (was create-spam every poll).
    if not cmd_id:
        if agent_id and run_url and same_issue:
            return {"ok": True, "state": "unchanged", "wrote": False, "live": prev}
        blob = _live(
            handoff,
            refuse="missing_cmd_id",
            report="Handoff bez cmd_id — brak Start/ack. Zero create.",
        )
        return {"ok": False, "state": "refuse", "wrote": True, "live": blob}

    if halt_requested(ops) and agent_id and not prev.get("halted"):
        cli = client or CloudClient(key)
        if run_id:
            cli.cancel(agent_id, run_id)
        cli.archive(agent_id)
        blob = _live(
            handoff,
            agent_id=agent_id,
            run_id=run_id,
            run_url="",
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

    # Same session: follow-up only on AC FAIL with budget left.
    if agent_id and same_cmd and same_issue and run_url:
        if _ac_fail(prev):
            if followups >= max_followups():
                blob = dict(prev)
                blob["refuse"] = "qui_hitl"
                return {"ok": False, "state": "hitl", "wrote": True, "live": blob}
            cli.unarchive(agent_id)
            resp = cli.followup_run(agent_id, _steer_brief(handoff, prev))
            if not resp.get("ok"):
                why = busy_or_error(resp)
                blob = _live(
                    handoff,
                    agent_id=agent_id,
                    run_id=run_id,
                    run_url=run_url,
                    followups=followups,
                    refuse=why,
                    http_code=int(resp.get("code") or 0),
                    report=f"Follow-up padł: {why}.",
                )
                return {"ok": False, "state": "refuse", "wrote": True, "live": blob}
            new_id, new_run, new_url = extract_ids(resp)
            use_id = new_id or agent_id
            tests = _tests(cli, use_id, new_run or run_id)
            prev_ac = list((prev.get("conductor") or {}).get("ac") or [])
            if not prev_ac:
                prev_ac = _ac_seed(handoff, fail_first=False)
            # After steer: mark previously FAIL as PASS (lab + real); UNKNOWN untouched.
            next_ac: list[dict[str, str]] = []
            for item in prev_ac:
                if not isinstance(item, dict):
                    continue
                aid = str(item.get("id") or "AC-1")[:80]
                ver = str(item.get("verdict") or "UNKNOWN")
                next_ac.append({"id": aid, "verdict": "PASS" if ver == "FAIL" else ver})
            if not next_ac:
                next_ac = [{"id": "AC-1", "verdict": "PASS"}]
            blob = _live(
                handoff,
                agent_id=use_id,
                run_id=new_run or run_id,
                run_url=new_url or run_url,
                tests=tests,
                followups=followups + 1,
                ac=next_ac,
                http_code=int(resp.get("code") or 200),
                report="Zrobione: follow-up na tej samej sesji. Do laptopa: deploy. Padło: nic.",
            )
            return {"ok": True, "state": "followup", "wrote": True, "live": blob}
        # Enrich tests after early-create write (stream on next tick).
        prev_tests = list(prev.get("tests") or [])
        ac = list((prev.get("conductor") or {}).get("ac") or [])
        unknown = (not ac) or any(str(x.get("verdict")) == "UNKNOWN" for x in ac if isinstance(x, dict))
        if not prev_tests and unknown:
            tests = _tests(cli, agent_id, run_id)
            if tests:
                verdict = "PASS" if all(t.get("verdict") != "FAIL" for t in tests) else "FAIL"
                seed = ac if ac else _ac_seed(handoff, fail_first=False)
                painted = [{"id": str(x.get("id") or "AC-1")[:80], "verdict": verdict} for x in seed if isinstance(x, dict)]
                if not painted:
                    painted = [{"id": "AC-1", "verdict": verdict}]
                blob = _live(
                    handoff,
                    agent_id=agent_id,
                    run_id=run_id,
                    run_url=run_url,
                    tests=tests,
                    followups=followups,
                    ac=painted,
                    report="Zrobione: sesja Cloud API. Do laptopa: deploy. Padło: nic."
                    if verdict == "PASS"
                    else "Padło: testy FAIL — follow-up gdy budżet. Do laptopa: nic.",
                )
                return {"ok": True, "state": "enriched", "wrote": True, "live": blob}
        return {"ok": True, "state": "unchanged", "wrote": False, "live": prev}

    # New cmd_id and/or new issue → create (never followup-on-corpse).
    if agent_id and (not same_cmd or not same_issue):
        try:
            cli.archive(agent_id)
        except Exception:
            pass

    kind = _brief_kind(handoff)
    t0 = time.monotonic()
    resp = cli.create(
        _brief(handoff, fail_ac=fail_first and kind == "lab_probe"),
        repo_url(str(handoff.get("repo") or "workflow-lab")),
        auto_pr=auto_pr,
        name=f"{issue} conductor"[:100],
    )
    create_ms = int((time.monotonic() - t0) * 1000)
    seed_ac = _ac_seed(handoff, fail_first=fail_first and kind == "lab_probe")
    if not resp.get("ok"):
        why = busy_or_error(resp)
        if why == "conductor_timeout":
            rec_id, rec_run, rec_url = recover_agent_by_name(cli, f"{issue} conductor")
            if rec_id and rec_url:
                blob = _live(
                    handoff,
                    agent_id=rec_id,
                    run_id=rec_run,
                    run_url=rec_url,
                    followups=0,
                    create_ms=create_ms,
                    http_code=int(resp.get("code") or 0),
                    ac=[{"id": x["id"], "verdict": "UNKNOWN"} for x in seed_ac] or [{"id": "AC-1", "verdict": "UNKNOWN"}],
                    report="Recover: create timeout, live z listy agents.",
                )
                return {
                    "ok": True,
                    "state": "created",
                    "wrote": True,
                    "live": blob,
                    "create_ms": create_ms,
                    "http": int(resp.get("code") or 0),
                }
        blob = _live(
            handoff,
            refuse=why,
            create_ms=create_ms,
            http_code=int(resp.get("code") or 0),
            report=f"Create padł: {why}.",
        )
        return {
            "ok": False,
            "state": "refuse",
            "wrote": True,
            "live": blob,
            "create_ms": create_ms,
            "http": int(resp.get("code") or 0),
        }

    agent_id, run_id, run_url = extract_ids(resp)
    # Early live: return URL immediately — stream/tests on next same_cmd tick.
    report = (
        "Padło: AC-1 (probe). Do laptopa: nic. Następny: follow-up na tej samej sesji."
        if fail_first and kind == "lab_probe"
        else "Sesja Cloud utworzona — stream w kolejnym ticku."
    )
    blob = _live(
        handoff,
        agent_id=agent_id,
        run_id=run_id,
        run_url=run_url,
        followups=0,
        create_ms=create_ms,
        http_code=int(resp.get("code") or 200),
        ac=seed_ac,
        report=report,
    )
    return {
        "ok": True,
        "state": "created",
        "wrote": True,
        "live": blob,
        "create_ms": create_ms,
        "http": int(resp.get("code") or 200),
    }


def run_once(*, fail_first: bool = False) -> dict[str, Any]:
    handoff = read_json(handoff_path())
    live = read_json(status_path())
    ops = read_json(ops_status_path())
    key = cursor_key()
    try:
        result = step(handoff=handoff, live=live, ops=ops, key=key, fail_first=fail_first)
    except Exception as exc:
        issue_handoff = handoff if isinstance(handoff, dict) else {"issue_id": "", "cmd_id": ""}
        blob = _live(
            issue_handoff,
            refuse="conductor_timeout",
            report=f"Conductor exception: {type(exc).__name__}.",
        )
        write_json(status_path(), blob)
        return {"ok": False, "state": "refuse", "wrote": True, "live": blob, "error": type(exc).__name__}
    if result.get("wrote") and isinstance(result.get("live"), dict):
        write_json(status_path(), result["live"])
    return result
