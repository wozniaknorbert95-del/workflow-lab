# Hermes Engineer — sekrety VPS (Fala C2)

**Zasada:** nigdy kopiuj keyring `gh` z laptopa. Osobny fine-grained PAT tylko na VPS.

## PAT GitHub (read-only)

- Scope: Contents **read**, Pull requests **read**, Checks **read**, Actions **read**
- **Bez** merge, **bez** workflow write
- Expiry: 90 dni — rotacja w kalendarzu
- Plik: `/etc/workflow-lab/hermes-engineer.env` (chmod **600**, nie w git)
- Kanarek: `gh api` GET checks OK; `gh pr merge` → **403**

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
