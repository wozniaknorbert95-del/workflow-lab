"""Conductor loop: handoff → Cloud API → live JSON. Not the tick."""
from __future__ import annotations

import os
import time
from typing import Any

from hermes_conductor.cloud import (
    CloudClient,
    RUN_ACTIVE,
    RUN_TERMINAL,
    busy_or_error,
    extract_ids,
    recover_agent_by_name,
    run_snapshot,
    tests_from_stream,
)
from hermes_conductor.verdict import tool_d
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
# QUI-163: Hermes owns the session after create (S2→S6), not one prompt.
FINAL_PHASES = ("done", "hitl", "failed")
MAX_EVENTS = 12


def _env_num(name: str, default: float) -> float:
    try:
        n = float(os.environ.get(name) or default)
    except (TypeError, ValueError):
        n = default
    return n if n > 0 else default


def watch_sec() -> float:
    return _env_num("CONDUCTOR_WATCH_SEC", 15)


def verify_sec() -> float:
    """Max wait for required checks after the run ends, then HITL."""
    return _env_num("CONDUCTOR_VERIFY_SEC", 2700)


def auto_pr_for(mode: str, repo: str) -> bool:
    """buduj = PR. testuj on the platform = PR as proof (no auto-merge there).

    workflow-lab testuj stays off: D-AUTOMERGE would merge a non-draft PR.
    """
    if mode == "buduj":
        return True
    return mode == "testuj" and repo == PLATFORM_REPO


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


def _mode_rules(mode: str, repo: str = "") -> str:
    if mode == "testuj":
        if auto_pr_for(mode, repo):
            return (
                "Tryb testuj: dowód w PR, bez merge. Po zakończeniu runu Cursor sam otworzy PR "
                "(autoCreatePR) — nie otwieraj PR ręcznie, wystarczy commit i push gałęzi. "
                "W tytule PR: NIE SCALAĆ."
            )
        return "Tryb testuj: dowód bez merge (autoCreatePR off — workflow-lab auto-merguje PR)."
    if mode == "ulepszaj":
        return "Tryb ulepszaj: jedna propozycja / draft — zero kodu, zero PR."
    return "Tryb buduj: wdróż issue, otwórz PR po zmianie."


def _ac_items(handoff: dict[str, Any]) -> list[tuple[str, str]]:
    """(id, text) pairs. Same ids in brief, seed and tool D."""
    out: list[tuple[str, str]] = []
    for i, line in enumerate(_ac_lines(handoff)[:20]):
        aid = line.split(":", 1)[0].strip() if ":" in line else f"AC-{i + 1}"
        if not aid.startswith("AC"):
            aid = f"AC-{i + 1}"
        text = line if line.startswith(aid) else f"{aid}: {line}"
        out.append((aid[:80], text))
    return out


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
    items = _ac_items(handoff)
    ac_block = (
        "\n".join(f"- {text}" for _, text in items)
        if items
        else "- (brak checklisty w handoff — czytaj Linear URL / kryteria w dor_excerpts)"
    )
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
        f"{_mode_rules(mode, repo)}\n"
        f"{playbook}\n"
        f"AC do domknięcia:\n{ac_block}\n"
        "Raport końcowy (ostatnie linie odpowiedzi): jedna linia na AC `AC-n: PASS|FAIL|UNKNOWN — dowód`, "
        "potem `WYNIK: PASS|PARTIAL|STOP`. Hermes weryfikuje to narzędziem D (PR + CI)."
        f"{issue_part}"
        f"{dor_part}"
        f"{steer_part}"
    )


def _ac_seed(handoff: dict[str, Any], *, fail_first: bool) -> list[dict[str, str]]:
    kind = _brief_kind(handoff)
    if kind == "lab_probe":
        return [{"id": "AC-1", "verdict": "FAIL" if fail_first else "UNKNOWN"}]
    items = _ac_items(handoff)
    if not items:
        return [{"id": "AC-1", "verdict": "UNKNOWN"}]
    return [{"id": aid, "verdict": "UNKNOWN"} for aid, _ in items]


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
    phase: str = "",
    verdict: str = "",
    d: list[str] | None = None,
    run_status: str = "",
    pr_url: str = "",
    branch: str = "",
    events: list[dict[str, str]] | None = None,
    watch_at: float = 0.0,
    finished_at: float = 0.0,
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
            "run_status": run_status,
            "pr_url": pr_url,
            "branch": branch,
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
            "phase": phase,
            "verdict": verdict,
            "d": list(d or [])[:10],
            "events": list(events or [])[-MAX_EVENTS:],
            "watch_at": float(watch_at or 0),
            "finished_at": float(finished_at or 0),
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


def _ev(text: str) -> dict[str, str]:
    return {"at": now_iso(), "text": str(text)[:160]}


def _events(cond: dict[str, Any], *texts: str) -> list[dict[str, str]]:
    out = [e for e in (cond.get("events") or []) if isinstance(e, dict)]
    out.extend(_ev(t) for t in texts if t)
    return out[-MAX_EVENTS:]


def _followup_text(handoff: dict[str, Any], steer: str, n: int) -> str:
    mode = work_mode(handoff.get("work_mode"))
    repo = str(handoff.get("repo") or "workflow-lab").strip() or "workflow-lab"
    return (
        f"FOLLOW-UP Hermesa (ta sama sesja, {n}/{max_followups()}), issue {handoff.get('issue_id')}.\n"
        f"Narzędzie D: {steer}\n"
        f"{_mode_rules(mode, repo)}\n"
        "Trzymaj kontrakt /autopilot — nie zaczynaj od zera. Zakazy bez zmian (zero deploy, SSH, sekretów, push main).\n"
        "Zakończ raportem: jedna linia na AC `AC-n: PASS|FAIL|UNKNOWN — dowód`, potem `WYNIK: PASS|PARTIAL|STOP`."
    )


def _report(verdict: str, reasons: list[str], pr_url: str, nxt: str) -> str:
    why = reasons[0] if reasons else "brak uwag"
    pr = f" PR: {pr_url}." if pr_url else ""
    return f"D {verdict or 'UNKNOWN'}: {why}.{pr} Do laptopa: {nxt}"[:800]


def _watch(
    *,
    handoff: dict[str, Any],
    prev: dict[str, Any],
    cli: CloudClient,
    agent_id: str,
    run_id: str,
    run_url: str,
    followups: int,
    ops: dict[str, Any] | None,
    auto_pr: bool,
) -> dict[str, Any] | None:
    """S2→S6 after create: watch run → PR → CI → tool D → follow-up | done | HITL.

    None = Cloud run state unreadable → caller keeps legacy behaviour.
    """
    cond = prev.get("conductor") if isinstance(prev.get("conductor"), dict) else {}
    agent_prev = prev.get("agent") if isinstance(prev.get("agent"), dict) else {}
    now = time.time()
    if now - float(cond.get("watch_at") or 0) < watch_sec():
        return {"ok": True, "state": "unchanged", "wrote": False, "live": prev}
    rid = run_id
    if not rid:
        ag = cli.get_agent(agent_id)
        body = ag.get("body") if isinstance(ag.get("body"), dict) else {}
        rid = str(body.get("latestRunId") or "")[:80] if ag.get("ok") else ""
    snap = run_snapshot(cli.get_run(agent_id, rid)) if rid else {}
    if not snap:
        return None
    issue = str(handoff.get("issue_id") or "")
    status = snap["status"]
    pr_url = snap.get("pr_url") or str(agent_prev.get("pr_url") or "")
    branch = snap.get("branch") or str(agent_prev.get("branch") or "")
    texts: list[str] = []
    if status != str(agent_prev.get("run_status") or ""):
        texts.append(f"run {status}")
    if pr_url and pr_url != str(agent_prev.get("pr_url") or ""):
        texts.append(f"S3 PR {pr_url}")
    prev_ac = [x for x in (cond.get("ac") or []) if isinstance(x, dict)] or _ac_seed(handoff, fail_first=False)
    tests = list(prev.get("tests") or [])
    common: dict[str, Any] = {
        "agent_id": agent_id,
        "run_id": rid,
        "run_url": run_url,
        "run_status": status,
        "pr_url": pr_url,
        "branch": branch,
        "watch_at": now,
    }

    if status in RUN_ACTIVE:
        blob = _live(
            handoff,
            **common,
            tests=tests,
            followups=followups,
            ac=prev_ac,
            phase="watching",
            events=_events(cond, *texts),
            report=f"Hermes prowadzi: run {status} — czekam na koniec (S2).",
        )
        return {"ok": True, "state": "watching", "wrote": True, "live": blob}

    if not tests and str(cond.get("phase") or "") == "watching":
        tests = _tests(cli, agent_id, rid)  # once, at the run end (stream may block up to 15 s)
    finished_at = float(cond.get("finished_at") or 0) or now
    ops_live = (ops or {}).get("live") if isinstance(ops, dict) else None
    res = tool_d(
        run={**snap, "pr_url": pr_url},
        ops_live=ops_live if isinstance(ops_live, dict) else None,
        issue=issue,
        ac_ids=[str(x.get("id") or "AC-1") for x in prev_ac],
        auto_pr=auto_pr,
    )
    pr_url = res.get("pr_url") or pr_url
    common["pr_url"] = pr_url
    action = res["action"]
    verdict = res["verdict"]
    reasons = list(res.get("reasons") or [])
    ac = res.get("ac") or prev_ac

    def out(phase: str, report: str, state: str, *extra: str, **kw: Any) -> dict[str, Any]:
        last_phase = str(cond.get("phase") or "")
        evs = list(texts) + ([f"D {verdict}: {'; '.join(reasons)[:120]}"] if phase != last_phase else []) + list(extra)
        blob = _live(
            handoff,
            **{**common, **kw.pop("common", {})},
            tests=tests,
            followups=kw.pop("followups", followups),
            ac=kw.pop("ac", ac),
            phase=phase,
            verdict=verdict,
            d=reasons,
            events=_events(cond, *evs),
            finished_at=kw.pop("finished_at", finished_at),
            report=report,
        )
        return {"ok": True, "state": state, "wrote": True, "live": blob, "d": res}

    if action == "wait":
        if now - finished_at > verify_sec():
            reasons.append(f"CI nie wróciło w {int(verify_sec() // 60)} min")
            return out("hitl", _report("UNKNOWN", reasons, pr_url, "sprawdź checki PR (HITL)."), "hitl")
        return out("verify", f"Run {status} · czekam na CI (S4) przed werdyktem D.", "verify")

    if action == "followup":
        limit = max_followups()
        if followups >= limit:
            reasons.append(f"limit follow-up {limit} wyczerpany")
            return out("hitl", _report("FAIL", reasons, pr_url, "HITL — przejmij lokalnie (/start)."), "hitl")
        cli.unarchive(agent_id)
        resp = cli.followup_run(agent_id, _followup_text(handoff, str(res.get("steer") or ""), followups + 1))
        if not resp.get("ok"):
            why = busy_or_error(resp)
            return out("verify", f"Follow-up padł ({why}) — ponowię w kolejnym kroku.", "verify", f"follow-up padł: {why}")
        _new_id, new_run, _new_url = extract_ids(resp)
        return out(
            "watching",
            f"D FAIL → follow-up {followups + 1}/{limit} na tej samej sesji: {reasons[0] if reasons else ''}"[:800],
            "followup",
            f"follow-up {followups + 1}/{limit}: {str(res.get('steer') or '')[:100]}",
            common={"run_id": new_run or rid, "run_status": "CREATING"},
            followups=followups + 1,
            ac=[{"id": str(x.get("id") or "AC-1"), "verdict": "UNKNOWN"} for x in prev_ac],
            finished_at=0.0,
        )

    if action == "hitl":
        return out("hitl", _report(verdict, reasons, pr_url, "HITL — decyzja Dowódcy."), "hitl")

    nxt = "nic (testuj = bez merge)." if work_mode(handoff.get("work_mode")) == "testuj" else "deploy — Zasada 11."
    if verdict != "PASS":
        nxt = "sprawdź AC (brak dowodu) — " + nxt
    return out("done", _report(verdict, reasons, pr_url, nxt), "done")


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
    repo = str(handoff.get("repo") or "workflow-lab").strip() or "workflow-lab"
    auto_pr = auto_pr_for(mode, repo)

    if agent_id and same_cmd and same_issue and run_url:
        cond = prev.get("conductor") if isinstance(prev.get("conductor"), dict) else {}
        phase = str(cond.get("phase") or "")
        if phase in FINAL_PHASES:
            return {"ok": True, "state": "unchanged", "wrote": False, "live": prev}
        if phase:
            watched = _watch(
                handoff=handoff,
                prev=prev,
                cli=cli,
                agent_id=agent_id,
                run_id=run_id,
                run_url=run_url,
                followups=followups,
                ops=ops,
                auto_pr=auto_pr,
            )
            if watched is not None:
                return watched
        # Legacy (pre-QUI-163 live / Cloud run state unreadable): stream + AC FAIL follow-up.
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
            # After steer: FAIL → UNKNOWN until tool D sees evidence (never painted PASS).
            next_ac: list[dict[str, str]] = []
            for item in prev_ac:
                if not isinstance(item, dict):
                    continue
                aid = str(item.get("id") or "AC-1")[:80]
                ver = str(item.get("verdict") or "UNKNOWN")
                next_ac.append({"id": aid, "verdict": "UNKNOWN" if ver == "FAIL" else ver})
            if not next_ac:
                next_ac = [{"id": "AC-1", "verdict": "UNKNOWN"}]
            blob = _live(
                handoff,
                agent_id=use_id,
                run_id=new_run or run_id,
                run_url=new_url or run_url,
                tests=tests,
                followups=followups + 1,
                ac=next_ac,
                http_code=int(resp.get("code") or 200),
                phase="watching",
                events=_events(cond, f"follow-up {followups + 1}/{max_followups()} (AC FAIL)"),
                report="Follow-up wysłany na tej samej sesji — czekam na wynik runu.",
            )
            return {"ok": True, "state": "followup", "wrote": True, "live": blob}
        # Enrich tests after early-create write (stream on next tick). FAIL paints FAIL; never PASS.
        prev_tests = list(prev.get("tests") or [])
        ac = list((prev.get("conductor") or {}).get("ac") or [])
        unknown = (not ac) or any(str(x.get("verdict")) == "UNKNOWN" for x in ac if isinstance(x, dict))
        if not prev_tests and unknown:
            tests = _tests(cli, agent_id, run_id)
            if tests:
                failed = any(t.get("verdict") == "FAIL" for t in tests)
                seed = ac if ac else _ac_seed(handoff, fail_first=False)
                painted = [
                    {
                        "id": str(x.get("id") or "AC-1")[:80],
                        "verdict": "FAIL" if failed else str(x.get("verdict") or "UNKNOWN"),
                    }
                    for x in seed
                    if isinstance(x, dict)
                ] or [{"id": "AC-1", "verdict": "FAIL" if failed else "UNKNOWN"}]
                blob = _live(
                    handoff,
                    agent_id=agent_id,
                    run_id=run_id,
                    run_url=run_url,
                    tests=tests,
                    followups=followups,
                    ac=painted,
                    phase=phase,
                    events=list(cond.get("events") or []),
                    report="Padło: testy FAIL — follow-up gdy budżet."
                    if failed
                    else "Strumień odczytany; AC bez dowodu = UNKNOWN (czekam na narzędzie D).",
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
        phase="watching",
        events=[_ev(f"Hermes: sesja Cloud utworzona ({mode}, autoCreatePR={'on' if auto_pr else 'off'})")],
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
