# TOOLSET — profil conductor (VPS)

Allow:

- Linear **read** (issue, komentarze, etykiety). Write: tylko komentarz raportu + jeden draft w trybie `ulepszaj`.
- GitHub **read** (PR, checks, diff).
- HTTP do Cursor Cloud Agents API (create, follow-up, get, stream, cancel, archive) — **tylko z procesu Nous**, nie z ticka Pythona.
- Browser / artefakt **tylko** weryfikacja UX (tryb testuj).
- Messaging do Dowódcy (P1 Telegram; P0 = status JSON + PWA).

Deny:

- `patch` / swobodny `terminal` na `dsaas-platform-main` i prod.
- Deploy, SSH prod, `workflow_dispatch`, sekrety tenanta, OIDC w URL.
- Drugi koder (subagent, który commituje).
- Malowanie FAIL D na PASS J.
- Tick / `hermes-ops-tick.py` jako drugi starter sesji.

Klucze (`CURSOR_API_KEY`, Linear) tylko na hoście. Nigdy w git.
