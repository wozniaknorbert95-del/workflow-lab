# Adapter ticka (Nous → `/ops`)

Tick w `scripts/hermes-ops-tick.py` **nie** startuje agenta. Po Start/Run next:

1. DoR (`allow_cursor_comment` = etykieta `agent`, nie HITL).
2. Zajmuje slot (`engine=RUNNING`, `live.issue`).
3. Zapisuje `hermes-conductor-handoff.json` (issue, repo, `work_mode`).
4. Kopiuje `hermes-conductor-live.json` (Nous) → `ops-status.json` (`live.agent.run_url`, `live.tests[]`, `live.conductor`).

Bez https `run_url` HUD Akademii zostaje na `picked_up`. Brak pliku Nous ≠ fałszywy RUNNING.

Ścieżki (env):

| Zmienna | Domyślnie |
| --- | --- |
| `HERMES_CONDUCTOR_HANDOFF` | `data/hermes-conductor-handoff.json` |
| `HERMES_CONDUCTOR_STATUS` | `data/hermes-conductor-live.json` |
| `OPS_CONDUCTOR_TTL_SEC` | `900` — RUNNING bez URL → `conductor_timeout` |

Szablony Nous: [`hermes-conductor/`](hermes-conductor/). Kopia na host: `scripts/install-hermes-conductor-docs.sh` (zero Docker, zero `systemctl`, zero sekretów). Start Nous + `CURSOR_API_KEY` = GO Dowódcy, nie ten skrypt.
