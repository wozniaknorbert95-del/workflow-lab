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
