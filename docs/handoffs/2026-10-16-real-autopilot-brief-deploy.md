# Handoff — Real Autopilot Brief DEPLOY (2026-10-16)

**GO Dowódcy:** pełne GO zamknięcie sesji  
**Lab PR:** [#112](https://github.com/wozniaknorbert95-del/workflow-lab/pull/112) → `main` `65f771b`  
**Nous PR:** [#23](https://github.com/wozniaknorbert95-del/hermes-ops-nous/pull/23) → `main` `b157fb7`

## VPS

| Check | Wynik |
| --- | --- |
| `/opt/workflow-lab` | `65f771b` |
| Image `hermes-conductor:local` | `90e149ecc633` |
| `hermes-conductor.service` | active |
| `CURSOR_API_KEY` | SET |
| Szablony `/var/lib/hermes-conductor` | CONDUCTOR.md z `brief_kind` |
| Host `issue_brief` resolve QUI-43/131 | DOGFOOD_PASS |
| Docker `_brief` real / lab_probe | DOCKER_BRIEF_OK / DOCKER_PROBE_OK |

Komenda: `bash scripts/install-hermes-conductor-vps.sh` po `git pull` main.

## Produkt

Następny Start QUI-43 (platforma) → Cloud prompt ma być **real Autopilot** (`autopilot.md`, repo `dsaas-platform-main`, AC z Linear) — **bez** `conductor-lab-probe`.  
Smoke QUI-131 → nadal probe.

## Rollback

```bash
docker tag hermes-conductor:rollback-YYYYMMDDTHHMM hermes-conductor:local
systemctl restart hermes-conductor
```

## NEXT (po tej sesji)

1. Żywy Start QUI-43 z telefonu — wzrokowy check promptu w Cloud (1×).
2. Zero dalszego polishu HUD jako „naprawy silnika”.
