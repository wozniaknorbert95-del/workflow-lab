# Phone loop watchdog (Fala C4)

Timer **poza** `.github/workflows` (T4). Wzorzec: akademia-push na VPS Akademii.

## Cisza = alarm

- TTL na krok: domyślnie **15 min** (`ttl_minutes` z `phone-loop-status.py`)
- Brak raportu supervisora → `SUPERVISOR_SILENCE` (gorsze niż FAIL)

## systemd (szablon na VPS)

Pliki w `/etc/systemd/system/` (nie commituj sekretów):

- `hermes-phone-loop.service` — uruchamia `phone-loop-status.py` + `hermes-operator-brief.py`
- `hermes-phone-loop.timer` — co 5 min

## DoD e2e (engineer_loop_e2e)

1. Syntetyczne issue lab (zero danych tenanta)
2. Telefon: kroki W-06
3. Log Engineera: S1→S6 zgodne z GitHub
4. `main` labu squash + CI odpaliło testy
5. Osobny PR **akademia**: `ENGINEER_LOOP_E2E=true` + karta AKTYWNY W LABIE

Bez e2e — karta Akademii zostaje **PARTIAL / SETUP**.
