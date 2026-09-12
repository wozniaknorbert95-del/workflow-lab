# DECISIONS.md — workflow-lab

One page. Newest first. Every irreversible choice lives here.

## D-F4-SLACK-PARK (2026-09-12) — Slack odłożony (Batch 8 scope cut)

**Decyzja Dowódcy:** Slack **nie** podpinamy w tej fazie. Uznany za zbędny — Linear mobile + GitHub mobile + Cursor wystarczą.

**Plan impact:** Faza 4 master planu — punkt „SLACK podpięty” → **PARKED** do przyszłej sesji. Nie blokuje W-06 PASS ani Batch 8.

**Zamienniki:** Linear notyfikacje, GitHub mobile, Grok Bot PM (B8-T5), Automations na eventach GitHub.

**Revisit:** gdy pojawi się potrzeba kanału gaduły dla zespołu >1 osoba lub zewnętrznych integracji.

## D-W6-PHONE (2026-09-12) — W-06 PASS (phone loop closed)

**Verdict:** PASS. Full loop from phone without laptop.

**Flow:**
1. Linear mobile — [QUI-10](https://linear.app/quietforge/issue/QUI-10/w-06-phone-loop-batch-7) (In Progress, delegate Cursor)
2. `@cursor` trigger → Cloud Agent `bc-2aeab115` → branch `cursor/w6-phone-loop-4fbb`
3. [PR #34](https://github.com/wozniaknorbert95-del/workflow-lab/pull/34) auto-opened, CI `validate` SUCCESS
4. **GitHub mobile squash merge** by Commander `2026-09-12T13:43:06Z` → `b8e261a`

**Deliverable:** README line `Mobile loop (W-06): verified 2026-09-12 from phone.`

**GitHub issue:** #32 closed by PR #34.

## D-W3-BUGBOT (2026-09-12) — Bugbot UI root cause (Batch 5 B5-T2)

**Finding:** Integrations API showed `bugBotEnabled: true` for `workflow-lab`, but **Automations → Bugbot** had global **Enable Bugbot OFF** and coverage **0/0 enabled (0%)** for `wozniaknorbert95-del` GitHub.

**URL:** https://cursor.com/automations/from-cursor/bugbot

**Why zero PR comments:** Bugbot never ran — not a repo-config bug; global automation disabled + onboarding not completed.

**Human-stop:** Enabling Bugbot requires **Usage-Based Billing** modal (~**$1.20/review** estimated). Commander must click **Enable Usage-Based Billing** at own risk/budget.

**Evidence:** `docs/evidence/b5-t2-bugbot-before.png`, `docs/evidence/b5-t2-bugbot-billing-gate.png`

**Rekomendacja R1:** Accept spend for lab smoke (1–2 PRs) OR defer Bugbot comment gate and proceed W-06 (Batch 7) — Bugbot nie blokuje phone loop.

## D-W6-SETUP (2026-09-12) — W-06 issue + runbook (Batch 7 B7-T0)

**Status:** SETUP PASS. Execution = Commander phone (human-stop merge).

**Issue:** [#32](https://github.com/wozniaknorbert95-del/workflow-lab/issues/32) — Linear mobile → Cloud Agent → GitHub mobile merge.

**Runbook:** `docs/W6-PHONE-LOOP.md` · tracker `docs/BATCH-07.md`.

## D-F2-EXIT (2026-09-12) — Faza 2 Memory AI closed (Batch 04)

**Verdict:** PASS.

**Deliverables:** [PR #28](https://github.com/wozniaknorbert95-del/workflow-lab/pull/28) ARCHITECTURE + PRODUCT + 2 skills + A1 audit. [PR #25](https://github.com/wozniaknorbert95-del/workflow-lab/pull/25) TESTING.md. Skills 3/3 in `.cursor/skills/`.

**Bugbot code smoke:** Issue #29 → agent `bc-1a1f68ac` → [PR #30](https://github.com/wozniaknorbert95-del/workflow-lab/pull/30) auto-PR, `greet(123)` regression test. Bugbot comment still PARTIAL → Batch 5 B5-T2.

**A1 score:** 9.2/10 — `docs/A1-AUDIT-2026-09-12.md`.

## D-F3-EXIT (2026-09-12) — Faza 3 Cloud Agents closed (Batch 03)

**Verdict:** PASS with Bugbot comment PARTIAL.

**Smoke (post-OAuth auto-PR):** Issue #23 → agent `bc-fc7682c1` → [PR #25](https://github.com/wozniaknorbert95-del/workflow-lab/pull/25) `TESTING.md` — **first MR auto-opened by Cloud Agent** without `gh` fallback. Merged `4089638`.

**Cloud MR scorecard:** #14 (W-05), #19 (CA-1), #20 (CA-3), #25 (F3 smoke) — 4/4 code merged without manual fixes.

**Bugbot:** enabled in Integrations API; zero PR comments on lab MRs to date → Batch 4 B4-T5.

**Cost:** `D-W3-COST` — $0 marginal per MR on Pro+ included quota.

## D-W3-GITHUB-OAUTH (2026-09-12) — stale OAuth fix (Integrations Connect)

**Symptom:** Integrations → GitHub → *Failed to load GitHub settings*; `POST /api/dashboard/get-github-installations` → **500 internal error**. Cloud Agent git worked (App 161116895) but auto-PR/Bugbot failed.

**Root cause:** Corrupt **User OAuth** record on Cursor backend after repeated reinstall/reconnect cycles during W-05 (GitHub **App** ≠ Integrations **OAuth** — two paths).

**Fix:** `POST /api/dashboard/disconnect-github` (removed 1 stale link) → Add Provider → GitHub → reconnect. **Verified 2026-09-12 ~13:01 UTC:** API 200, `githubConnected: true`, user `wozniaknorbert95-del`, install **161116895**, `workflow-lab` with `bugBotEnabled: true`.

**If recurrence:** incognito + revoke Cursor on github.com/settings/applications → reconnect; else Cursor support manual flush ([forum thread](https://forum.cursor.com/t/support-failed-to-load-github-settings/160868)).

## D-W3-COST (2026-09-12) — F3 Cloud Agent cost baseline (Batch 1)

| Run | Agent | PR | CI run | $ marginal |
|-----|-------|-----|--------|------------|
| W-05 | `bc-c187d412` | [#14](https://github.com/wozniaknorbert95-del/workflow-lab/pull/14) | [34693117577](https://github.com/wozniaknorbert95-del/workflow-lab/actions/runs/34693117577) | $0 (included Pro+) |
| CA-1 | `bc-54ca70ec` | [#19](https://github.com/wozniaknorbert95-del/workflow-lab/pull/19) | [34694052944](https://github.com/wozniaknorbert95-del/workflow-lab/actions/runs/34694052944) | $0 (included) |
| CA-3 | `bc-4b9bb898` | [#20](https://github.com/wozniaknorbert95-del/workflow-lab/pull/20) | [34694054897](https://github.com/wozniaknorbert95-del/workflow-lab/actions/runs/34694054897) | $0 (included) |

**Plan:** `docs/ROADMAP-MASTER.md` · current batch `docs/BATCH-01.md`.

## D-W9-USAGE (2026-09-12) — first Cloud Agent delivery cost baseline

**Plan:** Pro+ · On-Demand Unlimited enabled.

**First delivery:** W-05 agent `bc-c187d412` → [PR #14](https://github.com/wozniaknorbert95-del/workflow-lab/pull/14) (CI run [34693117577](https://github.com/wozniaknorbert95-del/workflow-lab/actions/runs/34693117577)).

**Usage snapshot** ([cursor.com/dashboard/usage](https://cursor.com/dashboard/usage), 2026-09-12): **96.8M tokens** included (session total incl. infra retries), **on-demand $0**. Models: `composer-2.5-fast`, `cursor-grok-4.6-high`.

**$/MR (W-05):** **$0 marginal** on included Pro+ quota. Revisit when first **on-demand** MR posts a dollar line on invoice.

## D-W01-PROTECT (2026-09-12) — native branch protection ON

**Status:** PASS (was PARTIAL on private Free).

**Applied 2026-09-12** after [D-W01-PUBLIC](DECISIONS.md): `main` requires PR + required status check **`validate`** (strict). API: `PUT .../branches/main/protection`.

**Evidence:** public repo + protection enabled; push direct to `main` blocked.

## D-W5-CLOUD (2026-09-12) — W-05 PASS (Cloud Agent loop closed)

**Status:** PASS. Cloud Agent delivered W-05 test; human merged PR #14.

**Deliverable:** [PR #14](https://github.com/wozniaknorbert95-del/workflow-lab/pull/14) — `greet("Cloud") === "hello Cloud"` in `src/hello.test.js` only. CI `validate` SUCCESS. Squash-merged `8239f41` 2026-09-12.

**Agent:** `bc-c187d412` (@cursor retry #15 on issue #5). Branch `cursor/greet-cloud-test-bfd7` (`c3feca9`). PR opened via `gh` fallback — agent `ManagePullRequest` failed (*connected GitHub account cannot access this repository*); code delivery intact.

**Root causes fixed (infra, staff PRs — not W-05 test code):**
1. **SSL clone fail** — build `bld-1310fd83`: `CAfile: none` → [PR #12](https://github.com/wozniaknorbert95-del/workflow-lab/pull/12) `ca-certificates` + `GIT_SSL_CAINFO` in `.cursor/Dockerfile`.
2. **exec-daemon fail** — agent `bc-86a1db80`: `curl: command not found` → [PR #13](https://github.com/wozniaknorbert95-del/workflow-lab/pull/13) add `curl` to Dockerfile.
3. **PR API OAuth** — **resolved 2026-09-12:** Commander connected Cursor to org **`wozniaknorbert95-del`** ([Integrations → GitHub](https://cursor.com/dashboard/integrations?highlight=source-control)). W-05 used `gh` fallback before this; next `@cursor` run should auto-open PRs.

**Prior failures (historical):** retries #6–#14 checkout FAIL until #12+#13 merged; App reinstall **161116895** (All repos); [PR #10](https://github.com/wozniaknorbert95-del/workflow-lab/pull/10) dockerfile path fix.

**Forbidden (held):** implementing `greet("Cloud")` on laptop to fake W-05 — test came from Cloud Agent branch only.

## D-W01-PUBLIC (2026-09-12) — lab repo public for Cloud + protection path

**Decision:** `wozniaknorbert95-del/workflow-lab` visibility = **public** (2026-09-12). Lab has synthetic code only; no tenant data.

**Why:** private repo + GitHub Free blocked native branch protection (D-W01-PROTECT) and Cloud Agent checkout persisted after App/ billing fixes. Public unblocks both paths when Cursor infra is green.

**Revisit:** if lab must be private again → GitHub Pro + re-verify Cloud Agent checkout before flip.

## D-W3-LINEAR (2026-09-12) — workspace Quietforge is CO

**Decision:** Command & control for this lab is Linear workspace **Quietforge** (`https://linear.app/quietforge`), team `QUI`, project `workflow-lab`. Labels `agent` / `review` / `blocked`. Six-field body lives in the project document + GitHub issue template.

**Why not `quietforge-ops`:** Commander already signed up; the slug is `quietforge`. Recreating a second workspace would split the board.

**C7:** no dsaas / ENT-* issues on this project. GitHub integration is account-wide today (Linear Reviews also lists other repos). Narrow the GitHub app later if the Reviews inbox is noisy.

**Evidence:** project https://linear.app/quietforge/project/workflow-lab-93ba13d2e4b6 · issue QUI-5 · MCP user `wozniaknorbert95@gmail.com`.

W-03 PASS. GitHub Issues remain the Cloud Agent seed (Cursor origin = GitHub).

## D-W4-LOOP (2026-09-12) — first laptop loop closed

https://github.com/wozniaknorbert95-del/workflow-lab/pull/1 squash-merged (`4ea746d`). W-04 PASS. `.gitlab-ci.yml` is on `main` for future CE cutover; origin remains GitHub.

## D-W0-ORIGIN (2026-09-12) — GitHub is lab origin until GitLab CE exists

**Decision:** `origin` of this repo is **GitHub** (account `wozniaknorbert95-del`). GitLab CE self-hosted remains the **target** origin from handbook D1 (07.09.2026), not the current fact.

**Why:** Installing GitLab CE (HTTPS, 2FA, signup OFF, runner, hello pipeline, backup) is a Commander human-stop (VPS, Zasada 11). Staff must not guess Cloud Agents against an unproven CE. Handbook v3.1 allows this exit: *GitHub-origin in DECISIONS.md*.

**Forbidden:** two remotes pushing the same lab (`origin` GitHub + GitLab). Dual-origin is a lie about SoT.

**When CE is proven** (`docs/W0-GITLAB-CE-CHECKLIST.md` all boxes + hello CI green on *our* runner): add D-W0-CE-CUTOVER here, change *only then* `origin` to GitLab, leave GitHub as Cloud Agents plan B **copy** (not dual-push).

**Cloud Agents today:** official GitHub integration. CE token test (handbook `05` §5) waits for cutover day.

## D-STACK (2026-09-12) — Node 20, npm, zero extra deps

Lab is a loop trainer, not a product clone of dsaas-platform. Commands in `AGENTS.md` = CI = `package.json` scripts. No pnpm, no TypeScript, no dsaas canon copy.

## D-C7 (2026-09-12) — this repo is never dsaas

Do not implement QuietForge / ENT-* / Kokpit here. Do not paste `dsaas-platform-main/AGENTS.md` into this file. Platform work stays on GitHub repo `dsaas-platform-main`.
