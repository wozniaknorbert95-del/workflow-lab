# DECISIONS.md — workflow-lab

One page. Newest first. Every irreversible choice lives here.

## D-W5-CLOUD (2026-09-12) — W-05 BLOCKED on Cursor checkout/build

**Status:** FAIL (not PASS). Cloud Agent cannot open a `cursor/*` PR.

**Symptom:** every `@cursor` on GitHub issue #5 ends with `Couldn't check out the repository` (cursor[bot]). Agent workspace may edit files locally (`Worked`) but Git panel shows **No pushed changes** — 0 open PRs.

**Retries (issue #5):** #6 `bc-86e070d2` · #7 `bc-c6bd0185` · #8 `bc-787c46b3` · #9 after env fix — all checkout FAIL. Earlier: billing block (retries #3–#5, fixed via On-Demand Unlimited + github-bg-connected **Setup complete**).

**Environment:** `6d364999-ae9a-11f1-bf4b-42ffb4d10ea7` — **0 successful builds** (all Manual/Recurring **Failure**, mostly Draft). Dashboard still shows Install Script **Not defined** despite PR #8.

**Infra fixes applied (staff, not W-05 test):** repo visibility → **public** (D-W01-PUBLIC) · PR #8 env.json install script · GitHub App **All repositories** · `workflow-lab` confirmed in Cursor installation API (107664687).

**Single fix (Commander):** GitHub → Applications → Cursor → **Uninstall** → reinstall → **All repositories** → cursor.com/github-bg-connected **Connect GitHub** → Cloud Agents → delete `workflow-lab` environment → **Trigger New Build** (non-draft) until **Success** → `@cursor` retry on #5 → merge PR (human). If still FAIL: Cursor support with agent id `bc-787c46b3`.

**Forbidden:** implementing `greet("Cloud")` on laptop to fake W-05.

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

## D-W01-PROTECT (2026-09-12) — native branch protection blocked

GitHub API `branch-protection` on `main` returned **403**: private repos on Free cannot use classic protection. W-01 stays PARTIAL. Compensation: AGENTS.md (never push `main`) + merge-only-via-PR practice (PR #1). Revisit when Pro or public.

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
