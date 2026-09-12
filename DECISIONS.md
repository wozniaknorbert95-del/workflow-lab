# DECISIONS.md — workflow-lab

One page. Newest first. Every irreversible choice lives here.

## D-W5-CLOUD (2026-09-12) — W-05 BLOCKED on GitHub-issue @cursor checkout

**Status:** FAIL (not PASS). Cloud Agent cannot open a `cursor/*` PR from GitHub issue #5.

**Symptom:** every `@cursor` on issue #5 ends in ~5s with `Couldn't check out the repository` (cursor[bot]). 0 open PRs.

**Retries (issue #5):** #6–#9 · #10 (post reinstall) · #11 (post PR #10 + OAuth) · #12 (post env clone OK) — all checkout FAIL. Latest: **`bc-3f35426d`** (#12, 2026-09-12 11:45 UTC).

**Split root cause (2026-09-12 13:42+):**
- **Environment build clone:** OK — `bld-7ee8ac2a` cloned `workflow-lab` @ `d767abe` ([build log](https://cursor.com/dashboard/cloud-agents/builds/bld-20260912-7ee8ac2a-c9da-4b51-9690-2ef8fe2778ad)). Docker step then **Terminal failure** (Cursor infra).
- **GitHub issue @cursor:** still FAIL checkout — uses **background-agent** path, not environment build path.
- **Integrations GitHub:** shows *Connect as wozniaknorbert95-del to 1 organization* (GitLab shows *Connected as*). Likely missing org OAuth link.
- **github-bg-connected:** *Setup complete* (Connect GitHub ✓).

**Infra applied (staff, not W-05 test):** App reinstall **161116895** (All repos) · [PR #10](https://github.com/wozniaknorbert95-del/workflow-lab/pull/10) dockerfile `.cursor/Dockerfile` · dashboard install script `npm run lint && npm test`.

**Single fix (Commander — human OAuth):** [Integrations → Source Control → GitHub](https://cursor.com/dashboard/integrations?highlight=source-control) → complete **Connect to organization `wozniaknorbert95-del`** (OAuth popup; Reconnect alone insufficient). Then `@cursor` #13 on issue #5 → merge PR. If still FAIL: Cursor support — agent `bc-3f35426d`, install `161116895`, note env clone OK but @cursor checkout FAIL.

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
