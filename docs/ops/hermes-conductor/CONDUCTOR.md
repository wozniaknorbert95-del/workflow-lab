# CONDUCTOR — procedura 6 kroków

Obowiązkowa. Pominięcie narzędzia D = nie wolno ogłosić PASS.

1. **Zczytaj** Linear: 6 pól, lista AC (checkbox / numerowane), etykiety, `repo`. DoR dziurawe → refuse, nie startuj Cursora. Handoff: `url`, `ac[]`, `dor_excerpts` (sanitized), `brief_kind`, `issue_json` (ISSUE-JSON v1, QUI-153).
2. **Brief** dla Cloud API:
   - `brief_kind=real` (default): repo z handoff + AC/DoR excerpts + playbook `.cursor/commands/autopilot.md` + `work_mode`. **Nie** szablon `conductor-lab-probe.md`.
   - Repo `dsaas-platform-main` (QUI-153): brief niesie blok `ISSUE-JSON v1` (id, title, status, labels, estimate, project, repo, `description` = oczyszczony skrót DoR: blok metadanych + kryteria akceptacji + rollback, ≤2500 znaków; nigdy surowy opis). Agent zapisuje go do `tmp/issue-<id>.json` i uruchamia `python scripts/session-preflight.py <id> --issue-json tmp/issue-<id>.json`. `LANE=HERMES` → `/start` (przejęcie: `### Stan sesji` z opisu PR). UNKNOWN/LOCAL/BLOCKED/STOP → STOP-LINEAR w tej turze; STOP ma pierwszeństwo przed AC. Brak danych w Linear = pusty JSON = STOP (fail-closed, B6a). Brief nie odwołuje się do `.cursor/context-state.md` (gitignored, w Cloud go nie ma).
   - `brief_kind=lab_probe` (smoke QUI-129/130/131, label `lab-smoke`, albo `OPS_CONDUCTOR_LAB_PROBE=1` / `CONDUCTOR_LAB_PROBE_ISSUES`): slice probe w `workflow-lab`.
3. **Sesja:** utwórz albo follow-up na **tym samym** `agentId`. Follow-up = steer (domknij FAIL AC), nie powtórka probe. Zapisz `run_url` do `hermes-conductor-live.json`.
4. **Strumień:** tool_call → `live.tests[]` (cmd, excerpt, PASS|FAIL|UNKNOWN). Puste w RUNNING = UNKNOWN testów.
5. **Narzędzie D** (mandatory): DoR, każdy punkt AC, required checks, dirty PR, R7/HITL. FAIL D → follow-up (limit `OPS_CONDUCTOR_MAX_FOLLOWUPS`) albo HITL. J (treść AC / UX) **tylko po** D.
6. **Raport** `live.conductor.report_pl`: zrobione · do laptopa · padło · następny pin. Tryb `ulepszaj` = jeden draft issue, zero kodu. Tryb `testuj` = nie merge.

Wejście: `hermes-conductor-handoff.json` (pisze tick). Wyjście: `hermes-conductor-live.json` (czyta tick). Python tick **nie** startuje sesji Cloud.

Take over / Pause: cancel active run, archive agenta, zero nowego follow-up. Nie Start next przy stale lock (QUI-88).
