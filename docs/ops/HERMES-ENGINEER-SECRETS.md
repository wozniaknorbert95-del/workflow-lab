# Hermes Engineer / Ops — sekrety VPS

**Zasada:** nigdy kopiuj keyring `gh` z laptopa (`gho_…`). Osobne fine-grained PAT tylko na VPS.  
**Zasada 2:** nie ustawiaj `GITHUB_OPS_WRITE=$GITHUB_ENGINEER_TOKEN` — osobna tożsamość write (blast radius, rotacja, kanarek read≠write).

## Trzy tożsamości

| Env | Rola | Prefiks | Repo |
|-----|------|---------|------|
| `GITHUB_ENGINEER_TOKEN` | read-only S1–S6 / phone-loop | `github_pat_` | lab (+ opcjonalnie akademia) |
| `GITHUB_OPS_WRITE` | `@cursor` + squash-merge po CI | `github_pat_` | **tylko** `workflow-lab` + `dsaas-platform-main` |
| `LINEAR_OPS_READ` | kolejka Linear (bez opisu issue → LLM) | `lin_api_` | workspace QuietForge |

Rotacja: **90 dni**. Zero deploy z timera (Zasada 11).

## `GITHUB_OPS_WRITE` (Hermes Ops)

- Fine-grained, owner `wozniaknorbert95-del`, expires 90d.
- Permissions: Pull requests **Read and write**, Issues **Read and write**, Contents **Read**, Checks **Read**.
- **Bez** Actions write, **bez** Workflows, **bez** admin.
- Prefill:

  ```powershell
  cd workflow-lab
  .\scripts\open-ops-write-pat-prefill.ps1
  ```

  W UI GitHub dodaj oba repo (URL nie zawsze przenosi listę).

- Kanarek policy w kodzie: merge zielonego PR = allow; `workflow_dispatch` deploy **nie istnieje** (`has_workflow_dispatch_deploy() is False`).
- Verify na VPS: `bash scripts/verify-ops-tokens.sh` (nie merguje losowego PR).

## `LINEAR_OPS_READ`

- Linear **Personal API Key**, read issues/projects w QuietForge.
- Runbook: [OPEN-LINEAR-OPS-KEY.md](OPEN-LINEAR-OPS-KEY.md).
- Bez klucza: tick używa awaryjnie `LINEAR_OPS_QUEUE_FILE` (`data/linear-queue.json`) albo `UNKNOWN` (fail-closed) — nigdy pusta zieleń.

## Timer `/ops`

Osobny unit `hermes-ops.timer` (nie mylić z `hermes-phone-loop.timer`).  
S1–S6 z `phone-loop-status` → `live.steps[]` w tym samym ticku.

```powershell
cd workflow-lab
bash scripts/install-hermes-ops-vps.sh
$lin = Read-Host -AsSecureString "LINEAR_OPS_READ (lin_api_...)"
$gh  = Read-Host -AsSecureString "GITHUB_OPS_WRITE (github_pat_...)"
.\scripts\push-ops-tokens-to-vps.ps1 -SecureLinear $lin -SecureGithub $gh
# na VPS:
ssh root@185.243.54.115 "bash /opt/workflow-lab/scripts/verify-ops-tokens.sh"
```

W `/etc/workflow-lab/hermes-engineer.env` (chmod **600**):

- `LINEAR_OPS_READ` — jak wyżej; po sukcesie tick `source=linear_api`, `reason=vps_timer`.
- `GITHUB_OPS_WRITE` — Run next / merge; bez niego kolejka może żyć, write nie.
- `GITHUB_ENGINEER_TOKEN` — read-only (osobny prefill `open-engineer-pat-prefill.ps1`).
- `OPS_MODE=MANUAL` | `AUTOPILOT` | `SUPERVISED`.
- `OPS_RUN_ALL=0` — Run all tylko gdy świadomie `1`.
- `LINEAR_OPS_QUEUE_FILE=/opt/workflow-lab/data/linear-queue.json` — bootstrap awaryjny.

Cache: `/opt/akademia/data/ops-status.json`. Komenda telefonu: `/opt/akademia/data/ops-cmd.json`.

## Linear → LLM (redakcja)

- Do LLM: **tylko** id issue, etykiety, status checków.
- Treść opisu issue: **OFF** (injection).

## Fail-closed

Brak Linear API i brak pliku kolejki → **UNKNOWN**. Nie udawaj zielonego S4.

## Instalacja ENGINEER (read-only, ~3 min)

1. **Nie** używaj `gh auth token` (`gho_…`).
2. `.\scripts\open-engineer-pat-prefill.ps1`
3. Repo: `workflow-lab` (+ opcjonalnie `akademia`). Permissions: Contents/PR/Checks/Actions **Read**.
4. Generate → `github_pat_…`
5. `.\scripts\push-engineer-pat-to-vps.ps1 -SecureToken $sec`
6. Oczekiwane: `PASS: merge blocked HTTP 403` (lub 404/405/422) z `verify-engineer-pat.sh`.

## Push ops tokens — reguły skryptu

- Odrzuca `gho_` (OAuth laptop).
- Akceptuje `github_pat_` / `ghp_` oraz `lin_api_` (lub Linear key długość ≥ 20).
- Wolno wgrać tylko jeden sekret (`-SecureLinear` albo `-SecureGithub`), drugi może już być na VPS.
- Loguje wyłącznie `len:N`, nigdy wartość.
