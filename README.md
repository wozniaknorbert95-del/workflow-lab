# workflow-lab

Gym for the Workflow Marzeń loop. **Not** the QuietForge platform. **Not** the Academy.

**Status (2026-09-12):** **Fully working** — laptop loop (W-04) + Cloud Agent loop (W-05) + Linear C&C (W-03). Scoreboard: `docs/DOD-WORKFLOW.md`.

- **Mobile loop (W-06):** verified 2026-09-12 from phone.
- Commands (truth): see **Komendy** below (`AGENTS.md` §2)
- Why GitHub not GitLab CE yet: `DECISIONS.md` → D-W0-ORIGIN
- Linear CO: `docs/LINEAR.md` → D-W3-LINEAR
- DoD scoreboard: `docs/DOD-WORKFLOW.md`
- CE install (Commander only): `docs/W0-GITLAB-CE-CHECKLIST.md`
- Morning ritual: `docs/MORNING-RITUAL.md` (10 minutes after daily digest)
- Evening ritual: `docs/EVENING-RITUAL.md` (5-minute shutdown checklist)
- Weekly security sweep: `.github/workflows/weekly-security-sweep.yml` → `agent` issue

## Komendy

```
install:     (none — no runtime dependencies)
test:        npm test
lint:        npm run lint
build:       npm run build
```

There is no `typecheck` script. Do not invent one.

Node 20+. No dependencies.

Academy (school) lives in a separate repo. Platform lives in `dsaas-platform-main`. Do not mix.
