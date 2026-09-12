# Grok Bot BADACZ — setup & smoke (B8-T4)

**Role:** Non-code research for `workflow-lab`. **Prompt SoT:** `docs/grok-bots/BADACZ.md`

## Prerequisites

| Item | Status |
|------|--------|
| Cursor Pro+ (Grok Bot included) | ✅ |
| Grok Bot desktop | `C:\Users\FlexGrafik\AppData\Local\Programs\Grok Bot\Grok Bot.exe` |
| Signed in (same Cursor account) | ✅ |

## Manual setup (first time)

1. Dashboard → **Try Grok Bot** → Download (if not installed).
2. Open Grok Bot → onboarding: **Engineering** → tools **GitHub** + **Cursor**.
3. **Create your first Bot:**
   - **Name:** `BADACZ`
   - **Job:** `Research analyst (non-code)`
   - **Description:** paste full block from `docs/grok-bots/BADACZ.md`
4. First chat: send smoke query from `docs/evidence/b8-t4-badacz-smoke-report.md`.

## Automated setup (repeatable)

For Playwright CDP automation (senior ops path):

```powershell
# 1. Start Grok Bot with debug port
Get-Process "Grok Bot" -EA SilentlyContinue | Stop-Process -Force
Start-Process "$env:LOCALAPPDATA\Programs\Grok Bot\Grok Bot.exe" -ArgumentList "--remote-debugging-port=9224"
Start-Sleep -Seconds 8

# 2. From workflow-lab root (playwright installed locally for script)
cd C:\Users\FlexGrafik\FlexGrafik\github\workflow-lab
npm install playwright --no-save
node scripts/grok-bot-setup-badacz.mjs
node scripts/grok-bot-badacz-smoke.mjs
```

## When to use BADACZ vs Cloud Agent

| Need | Tool |
|------|------|
| Pricing, docs, options, competitive research | **BADACZ** (Grok Bot) |
| Code, PR, tests, CI | **Cloud Agent** (@cursor / Automation) |
| Board status, blockers | Grok Bot **PM** (B8-T5, optional) |

## Guardrails (R7)

- No secrets in chat. No merge/deploy. No `dsaas-platform-main` scope.
- Vendor blogs = INFO only; facts need official URL + read date.

## Evidence (2026-09-12)

- `DECISIONS.md` → **D-B8-GROK-BADACZ**
- `docs/evidence/b8-t4-badacz-smoke-report.md`
- Screenshots: `b8-t4-grok-05-bot-created.png`, `b8-t4-grok-07-smoke-response.png`
