# Handoff — Ops tokens live on VPS (2026-09-21)

**Repo:** workflow-lab  
**Gałąź:** `feat/ops-tokens-vps`

## Kanarek (po HITL)

| Sekret | len na VPS |
|--------|------------|
| `LINEAR_OPS_READ` | 48 |
| `GITHUB_OPS_WRITE` | 93 |
| `GITHUB_ENGINEER_TOKEN` | 93 (nietknięty, read-only verify PASS) |

- `verify-ops-tokens.sh`: **PASS** (Linear viewer 200, GitHub WRITE repo+pulls+comment-dry 404, ENGINEER merge blocked 403)
- `/ops/status`: **PAUSED** · `reason=vps_timer` · next **QUI-61** (nie `queue_file`)
- Lokalny plik `%USERPROFILE%\.config\workflow-lab\ops-tokens.env` **usunięty** po pushu

## Tooling dostarczone

- `scripts/open-ops-write-pat-prefill.ps1`
- `docs/ops/OPEN-LINEAR-OPS-KEY.md` + zaktualizowany `HERMES-ENGINEER-SECRETS.md`
- `scripts/push-ops-tokens-to-vps.ps1` (odrzuca `gho_`, partial push)
- `scripts/push-ops-tokens-from-file.ps1` / `hitl-push-ops-tokens.ps1`
- `scripts/verify-ops-tokens.sh`
- `hermes_ops/ops_token_validate.py` + test w `test_hermes_ops.py`

## Rotacja

+90 dni od 2026-09-21 → **2026-12-20** (przypomnienie w kalendarzu Dowódcy).

## Świadomie nie

- Brak sekretów w gicie / czacie / handoffie.
- Nie kopiowano `gh auth` (`gho_`).
- Nie promowano ENGINEER do WRITE.
