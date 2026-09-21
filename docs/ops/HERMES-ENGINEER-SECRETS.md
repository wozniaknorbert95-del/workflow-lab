# Hermes Engineer — sekrety VPS (Fala C2)

**Zasada:** nigdy kopiuj keyring `gh` z laptopa. Osobny fine-grained PAT tylko na VPS.

## PAT GitHub — write (Hermes Ops, 2026-09-21)

- Env: `GITHUB_OPS_WRITE` (chmod **600**, nie w git). Fine-grained, **oba** repo: `workflow-lab` + `dsaas-platform-main`.
- Scope: Pull requests **read+write** (merge squash), Issues **write** (komentarz `@cursor`). **Bez** Actions write, **bez** `workflow_dispatch` production.
- Kanarek: merge zielonego PR w teście policy = **200 allow**; `workflow_dispatch` deploy **nie istnieje** w orchestratorze (`has_workflow_dispatch_deploy() is False`).
- Rotacja: 90 dni. Blast radius = dwa repo — świadomie.

Env kolejki: `LINEAR_OPS_READ` (kolejka, bez treści opisu do LLM). `GITHUB_ENGINEER_READ` = status (może być ten sam App). Capy: `OPS_MAX_CONCURRENT=1`, `OPS_MAX_RUNS_PER_DAY=8`.

**Zero deploy z timera.** Zasada 11.


## Linear (read, redakcja)

- Do LLM Engineera: **tylko** id issue, etykiety, status checków (liczby/id)
- Treść opisu issue: domyślnie **OFF** (T1 prompt injection)

## Fail-closed

Brak tokena → status **UNKNOWN** + alarm supervisora. **Nie** udawaj zielonego kroku 4.

## Instalacja (Dowódca, ~3 min)

1. **Nie** używaj `gh auth token` (`gho_…`) — ma merge **200** → verify **FAIL**.
2. Otwórz prefilled formularz (sudo GitHub = kod z maila w przeglądarce):

   ```powershell
   cd workflow-lab
   .\scripts\open-engineer-pat-prefill.ps1
   ```

3. **Repository access:** tylko `workflow-lab` (+ opcjonalnie `akademia`). Permissions już w URL: Contents/PR/Checks/Actions **Read**.
4. **Generate token** → skopiuj `github_pat_…` (jednorazowo).
5. Wgraj na VPS + kanarek:

   ```powershell
   $sec = Read-Host -AsSecureString "github_pat_ (read-only)"
   .\scripts\push-engineer-pat-to-vps.ps1 -SecureToken $sec
   ```

   Oczekiwane: `PASS: merge blocked HTTP 403` (lub 404/405/422).
