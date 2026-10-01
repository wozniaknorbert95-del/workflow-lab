# CONDUCTOR — procedura 6 kroków

Obowiązkowa. Pominięcie narzędzia D = nie wolno ogłosić PASS.

1. **Zczytaj** Linear: 6 pól, lista AC (checkbox / numerowane), etykiety, `repo`. DoR dziurawe → refuse, nie startuj Cursora.
2. **Brief** dla Cloud API: AC, DoD ids z kanonu których plików issue dotyczy, zakazy (zero deploy/SSH/sekretów), `work_mode` (`buduj` | `testuj` | `ulepszaj`).
3. **Sesja:** utwórz albo follow-up na **tym samym** `agentId`. Zapisz `run_url` do `hermes-conductor-live.json`.
4. **Strumień:** tool_call → `live.tests[]` (cmd, excerpt, PASS|FAIL|UNKNOWN). Puste w RUNNING = UNKNOWN testów.
5. **Narzędzie D** (mandatory): DoR, każdy punkt AC, required checks, dirty PR, R7/HITL. FAIL D → follow-up (limit `OPS_CONDUCTOR_MAX_FOLLOWUPS`) albo HITL. J (treść AC / UX) **tylko po** D.
6. **Raport** `live.conductor.report_pl`: zrobione · do laptopa · padło · następny pin. Tryb `ulepszaj` = jeden draft issue, zero kodu. Tryb `testuj` = nie merge.

Wejście: `hermes-conductor-handoff.json` (pisze tick). Wyjście: `hermes-conductor-live.json` (czyta tick). Python tick **nie** startuje sesji Cloud.

Take over / Pause: cancel active run, archive agenta, zero nowego follow-up. Nie Start next przy stale lock (QUI-88).
