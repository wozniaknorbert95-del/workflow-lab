# W0 — GitLab CE human-stop (Commander)

Do this on the VPS yourself. Staff does not SSH/deploy (Zasada 11).
Source: `akademia/ops/workflow-marzen/05-GITLAB-CE-SELFHOSTED.md` §1–4.

Until this list is green, lab `origin` stays GitHub (`DECISIONS.md` D-W0-ORIGIN).

## Stop conditions

- VPS RAM **< 4 GB** → do not install CE; keep GitHub origin.
- Same Docker Compose as dsaas/jadzia-core runtime → **no**. Separate compose, separate ports (80/443/2222). Collision with Caddy/nginx = blocker before `up`.

## Checklist

- [ ] Pin image version (never `:latest`); record digest in this file
- [ ] Backup taken **before** first “done”
- [ ] `https://gitlab.<domain>` with valid cert
- [ ] root password changed; **2FA on**
- [ ] public signup **OFF**
- [ ] Runner registered; **hello pipeline green on that runner**
- [ ] This project `main` protected; merge only via MR
- [ ] Cutover decision written as `D-W0-CE-CUTOVER` in `DECISIONS.md`

## After cutover

Run `docs/W2-CLOUD-AGENTS.md` §5 token test (15 min). PASS → Cloud Agents on CE. FAIL → CE stays local origin; Cloud Agents stay on this GitHub repo as a **copy**, not dual-push.
