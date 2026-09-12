# PRODUCT.md — workflow-lab

One page. **Who** uses this and **what success looks like**.

## Job to be done

Commander trains the full loop — idea → issue → agent → MR → CI → review → merge — **without opening `dsaas-platform-main`** and eventually **from a phone**.

## User

- **Commander (Dowódca)** — merges, spend limits, architecture gates.
- **Agents (local + Cloud)** — execute issues; never merge.
- **Not in scope:** QuietForge tenants, Kokpit owners, paying customers.

## Success criteria (scoreboard)

Tracked in `docs/DOD-WORKFLOW.md`. Current state (2026-09-12):

| Milestone | Status | Meaning |
| --- | --- | --- |
| W-04 Laptop loop | PASS | Manual MR → green CI → merge |
| W-05 Cloud Agent MR | PASS | Agent opens PR, CI green, human merges |
| F3 Cloud wave | PASS | ≥3 cloud MRs, auto-PR post-OAuth (#25), `$/MR` recorded |
| F2 Memory AI | IN PROGRESS | Docs + skills so agents ask zero convention questions |
| W-06 Phone loop | **PASS** | QUI-10 → PR #34 → mobile merge `b8e261a` (2026-09-12) |

**Product win for F2:** a new agent reads `ARCHITECTURE.md` + `PRODUCT.md` + `TESTING.md` and completes a size-S issue without asking where tests live or which commands CI runs.

## Journey (happy path)

1. Create issue in Linear or GitHub (`agent` label, 6-field body).
2. `@cursor` or local agent picks it up on `feat/*` or `cursor/*`.
3. Agent runs lint → test → build before PR.
4. CI `validate` mirrors local commands.
5. Bugbot/Security (when enabled) review before Commander.
6. Commander squash-merges; irreversible choices → `DECISIONS.md`.

## Metrics we care about

| Metric | Source | Target |
| --- | --- | --- |
| CI pass rate | GitHub Actions | 100% on `main` |
| Cloud MR without manual code fix | `DECISIONS.md` D-F3-EXIT | ≥2/3 (achieved 4/4) |
| `$/MR` marginal | Cursor usage dashboard | Known; $0 on Pro+ included quota |
| Agent convention questions | subjective per issue | → 0 after F2 complete |

## Non-goals

- Features for paying customers or a seventh Kokpit department.
- Replacing Linear as long-term CO (see `docs/LINEAR.md`).
- Deploying or configuring `dsaas-platform-main` from this repo.
- Live marketing / Demand OS (separate ecosystem rule).
- Storing secrets, tenant data, or `.env` values in git.

## Boundaries

| This lab | Elsewhere |
| --- | --- |
| Loop gym, synthetic `greet` | DSaaS platform canon + runtime |
| `docs/DOD-WORKFLOW.md` W-* criteria | `kanon/` in platform repo |
| Academy workflow lessons | Separate school repo |
| GitHub origin (today) | GitLab CE on VPS (F0, Commander human-stop) |

## When F2 is done

Batch 4 exit: `ARCHITECTURE.md`, `PRODUCT.md`, `TESTING.md`, `DECISIONS.md` current; **3 skills** in `.cursor/skills/`; A1 audit filed. Then Batch 5+ (Bugbot code smoke, mobile loop prep).
