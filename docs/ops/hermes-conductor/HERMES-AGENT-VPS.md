# Hermes Agent (Nous Research) na VPS — prowadzący sesję S0–S6

**Status:** DESIGN (QUI-163, re-scope 2026-10-19). Zero zmian kodu/VPS w tym pliku.
**Hierarchia:** `HERMES-ROLE-CONTRACT.md` (hermes-ops-nous) → ten plik → `CONDUCTOR.md` / `SOUL.md` / `TOOLSET.md`.

## Po ludzku

Na laptopie Dowódca używa **Hermes Agent** (Nous Research, v0.20.0) — agenta LLM, który sam myśli i woła narzędzia.
Na VPS **nie ma Hermes Agent**. Jest kontener `hermes-conductor` = obraz `python:3.12-slim` + nasza pętla Python
(`scripts/hermes-conductor-loop.py`). Szablony `SOUL.md`/`CONDUCTOR.md`/`TOOLSET.md` są kopiowane do
`/var/lib/hermes-conductor` i montowane jako `HERMES_HOME`, ale **żaden kod ich nie czyta** — leżą dla agenta,
którego nigdy nie zainstalowano. Stąd „Hermes nie prowadzi sesji”: decyzje są w `loop.py`, nie w modelu.

Cel: ten sam Hermes Agent co na laptopie, na VPS, z rolą z `SOUL.md`, procedurą `CONDUCTOR.md` jako skill,
a nasz kod (`hermes_conductor`, `hermes_ops`) jako **narzędzia** (MCP), z guardrailami wymuszonymi w kodzie narzędzi.

## 1. Stan faktyczny (dowody z repo, 2026-10-19)

| Element | Laptop | VPS (z repo) |
| --- | --- | --- |
| Runtime | Hermes Agent v0.20.0, `%LOCALAPPDATA%\hermes\hermes-agent`, `hermes.cmd` (CLI, sesje interaktywne) | `docs/ops/Dockerfile.hermes-conductor`: `python:3.12-slim` + `hermes_conductor` + `hermes_ops`; brak Hermes Agent |
| LLM | `config.yaml`: `model.provider: nvidia`, `model.default: nvidia/nemotron-3-super-120b-a12b`; `.env`: `NVIDIA_API_KEY`, `NVIDIA_BASE_URL` (SET) | **brak** — `grep openai/anthropic/openrouter/litellm/chat.completions/HERMES_LLM` w workflow-lab = 0 trafień; `HERMES-ENGINEER-SECRETS.md` nie ma zmiennych modelu |
| Rola | `SOUL.md` = domyślny tekst Nous (nie rola conductora); wiedza o projekcie w `memories/MEMORY.md`, `USER.md`, skill `akademia-dev`, `AGENTS.md` repo | `SOUL.md`/`CONDUCTOR.md`/`TOOLSET.md` w `/var/lib/hermes-conductor` (`install-hermes-conductor-docs.sh`) — **martwe** (0 odczytów w kodzie) |
| Narzędzia | toolsety `terminal, file, web, browser, code_execution, delegation, memory, skills, todo, cronjob…`; **0 `mcp_servers`**; GitHub przez `gh`/skill `github` | Python: `cloud.py` (`POST /v1/agents`, follow-up, stream), `phone_loop_github`, Linear read |
| Decyzje | model (LLM) | `scripts/hermes_conductor/loop.py` (deterministycznie) |
| Wyzwalacz | człowiek w CLI | `/ops` Start → `ops-cmd.json` → tick (`hermes-ops.service`) → `write_handoff()` → `hermes-conductor-handoff.json` → pętla co 3 s |

Akademia (`hermes-ops-nous/host/progress_vault.py`, `ACADEMY_HERMES_*`) to emerytowany czat kursu (410), **nie** Nous conductor.

## 2. Luka (root cause)

Brakuje **runtime'u agenta**, nie promptu. Rola i procedura istnieją; brakuje:
1. Hermes Agent na VPS (deploy) + klucz LLM (tylko Dowódca).
2. Kod conductora jako narzędzia (MCP) zamiast pętli decyzyjnej.
3. Wyzwalacz: handoff z `/ops` budzi agenta.
4. Guardraile w kodzie narzędzi (nie tylko w prompcie) + odcięte toolsety `terminal/file/browser`.

## 3. Architektura docelowa (minimalna)

```
/ops Start → ops-cmd.json → tick → hermes-conductor-handoff.json      (bez zmian)
        ↓
Hermes Agent gateway (docker nousresearch/hermes-agent, HERMES_HOME=/opt/data)
  cron "hermes-conductor" every 1m
    script ops-gate.py  → {"wakeAgent": false}   gdy nic się nie zmieniło (0 tokenów)
                        → {"wakeAgent": true, "context": {handoff, session}} gdy nowy cmd_id
                          albo zmiana stanu runu/PR/CI albo heartbeat 10 min
    skill hermes-conductor (= CONDUCTOR.md), SOUL.md (= rola), continuity=true
    enabled_toolsets: [hermes_ops]            ← tylko nasze MCP; bez terminal/file/web/browser
        ↓ MCP stdio: python3 /wl/scripts/hermes_tools_mcp.py  (stdlib, reuse hermes_conductor + hermes_ops)
  ops_write_status → hermes-conductor-live.json → hermes-ops-conductor.path → tick → ops-status.json → HUD
```

Stan sesji (agentId, runId, faza, follow-upy, PR) trzyma **narzędzie** w `/opt/akademia/data/hermes-agent-session.json`,
nie pamięć modelu. Każdy tick agenta = krótka tura: przeczytaj stan → zdecyduj jeden krok → zapisz status.

### 3.1 Narzędzia (MCP `hermes_ops`)

| Tool | Co | Guard w kodzie |
| --- | --- | --- |
| `ops_session` | handoff + stan sesji + pauza z `ops-cmd.json` | read-only |
| `cloud_create_agent(issue_id, brief)` | `POST /v1/agents`; `autoCreatePR` liczy kod (testuj na platformie = true) | 1 `agentId`/issue; slot zajęty / paused ⇒ refuse; brak `CURSOR_API_KEY` ⇒ refuse |
| `cloud_status(agent_id)` | `GET /v1/agents/{id}` + `/runs/{runId}` → status, `prUrl`, `result` (z #116 `run_snapshot`) | read-only |
| `cloud_followup(agent_id, prompt)` | `POST /runs` na tym samym agencie | licznik ≤ `OPS_CONDUCTOR_MAX_FOLLOWUPS` (3) ⇒ potem refuse+HITL; 409 ⇒ `busy` |
| `github_pr_ci(pr_url)` | stan PR + required checks (`gates`/`validate`), pending = UNKNOWN (z #116 `checks_from_runs`) | read-only |
| `tool_d(issue_id)` | werdykt D liczony w kodzie (z #116 `verdict.tool_d`): PR + S4 + `AC-n: PASS` dla każdego AC | model **nie** podaje werdyktu; tylko go czyta |
| `linear_report(issue_id, body_pl)` | jeden komentarz-raport | tylko komentarz; brak klucza ⇒ refuse (no-op) |
| `ops_write_status(phase, report_pl, events)` | zapis `hermes-conductor-live.json` (schemat `conductor_adapter`) | `verdict`/`d` dokleja kod z ostatniego `tool_d`, nie model |
| `github_merge(pr_url)` | squash merge | tylko `work_mode=buduj` **i** `tool_d`=PASS (przeliczone w środku) **i** checks zielone **i** brak `hitl:*`/`no-automerge`/`blocked`/R7 |
| `ops_hitl(reason)` | faza `hitl` + raport | zawsze dozwolone |

### 3.2 Guardraile

- `testuj`: `github_merge` zawsze refuse. `ulepszaj`: `cloud_create_agent` refuse (tylko propozycja w raporcie).
- Follow-up max 3 / issue, potem HITL. UNKNOWN nigdy PASS (werdykt tylko z `tool_d`).
- Toolsety: cron agenta = `[hermes_ops]`. Brak `terminal`, `file`, `code_execution`, `browser`, `delegation` ⇒ brak SSH/deploy/patch/`workflow_dispatch` technicznie, nie tylko w prompcie.
- `hermes pause` / `/ops` Pause ⇒ gate `wakeAgent:false` + narzędzia mutujące refuse. Stop kontenera = kill switch.
- Jeden mózg: stary `hermes-conductor.service` **wyłączony** przy cutover (inaczej podwójny S2).
- Sekrety tylko w `/opt/hermes-agent/.env` (chmod 600); `config.yaml` ma tylko nazwy; MCP dostaje klucze przez `env`.

### 3.3 Model

Ten sam co laptop: `provider: nvidia`, `nvidia/nemotron-3-super-120b-a12b`, zmienne `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`
(Hermes wymaga ≥64K kontekstu — spełnione). Uwaga: `PLAN-LLM-TRYBY-2026-10-18.md` (D5) odradza NVIDIA dla danych prywatnego
repo („may train”); alternatywa: `OPENROUTER_API_KEY` + model z planu. Decyzja Dowódcy — narzędzia są niezależne od modelu.

## 4. Atomy (QUI-163)

- **A0** — ten dokument (docs, branch `docs/qui-163-hermes-agent-vps`).
- **A1** — `scripts/hermes_tools_mcp.py` + `scripts/hermes_tools/` (reuse z PR #116: `cloud.get_run/run_snapshot`, `verdict.tool_d`, `checks_from_runs`, slot-hold w `orchestrator.py`) + testy MCP (guardy: merge w testuj, follow-up>3, D bez dowodu). CI zielone, `no-automerge`.
- **A2** — profil `docs/ops/hermes-agent/`: `config.yaml.example` (bez sekretów), `skills/hermes-conductor/SKILL.md`, `scripts/ops-gate.py`, `hermes-agent.service.example`, `scripts/install-hermes-agent-vps.sh` (bez kluczy) + test CI: brak sekretów, `enabled_toolsets == [hermes_ops]`.
- **A3** — Dowódca: instalacja VPS + klucze + cutover + dogfood re-run QUI-161 (testuj) → potem 1 issue `buduj` labu.

## 5. Rollback

`systemctl disable --now hermes-agent` → `systemctl enable --now hermes-conductor` (obraz `hermes-conductor:local` bez zmian).
Repo: `git revert` merge-commitów A1/A2.
