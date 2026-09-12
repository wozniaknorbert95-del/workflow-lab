/**
 * B8-T4: Create Grok Bot BADACZ via Playwright + CDP (Grok Bot desktop).
 * Prerequisite: Grok Bot running with --remote-debugging-port=9224
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const EVIDENCE = 'docs/evidence';
mkdirSync(EVIDENCE, { recursive: true });

const BADACZ_JOB = 'Research analyst (non-code)';
const BADACZ_DESC = `You are BADACZ — research analyst for workflow-lab (Workflow Marzen delivery gym).

ROLE: Non-code research only. Never write code, never merge PRs, never ask for secrets.

SOURCES (official only): docs.github.com, docs.gitlab.com, cursor.com/docs, linear.app/docs, github.com/pricing, linear.app/pricing.
Vendor blogs = INFO tier, not FACT.

OUTPUT FORMAT:
1. Facts (bullet) — each with URL + read date (YYYY-MM-DD)
2. Hypotheses (if any) — clearly labeled, separate from facts
3. One recommendation — single sentence, no option menu

HARD STOPS:
- Ambiguous question → one clarifying question, no research
- Production changes, credentials, tenant data → refuse
- Code implementation requests → redirect to Cloud Agent / @cursor on GitHub

CONTEXT: workflow-lab repo = delivery gym for Cursor+Linear+GitHub loop. dsaas-platform-main is out of scope.`;

const SMOKE_QUERY = `Research: GitHub Actions billing for public repositories (workflow-lab is public).
Question: Are standard GitHub-hosted runner minutes free for public repos?
Use official GitHub docs only. Format per BADACZ contract.`;

async function shot(page, name) {
  await page.screenshot({ path: `${EVIDENCE}/${name}`, fullPage: true });
  console.log('screenshot', name);
}

async function bodyText(page) {
  return page.evaluate(() => document.body?.innerText || '');
}

async function completeOnboarding(page) {
  for (let i = 0; i < 15; i++) {
    const body = await bodyText(page);
    if (/Create your first Bot|New Bot/i.test(body) && /Name/i.test(body)) return;
    if (/What will you be working on most/i.test(body)) {
      await page.getByText(/^Engineering$/).first().click();
      await page.getByRole('button', { name: /^Next$/ }).click();
      await page.waitForTimeout(800);
      continue;
    }
    if (/What do you use every day/i.test(body)) {
      const gh = page.getByText(/^GitHub$/).first();
      const cursor = page.getByText(/^Cursor$/).first();
      if (await gh.count()) await gh.click();
      if (await cursor.count()) await cursor.click();
      await page.getByRole('button', { name: /^Next$/ }).click();
      await page.waitForTimeout(800);
      continue;
    }
    const next = page.getByRole('button', { name: /^Next$/ }).first();
    if (await next.count()) {
      await next.click();
      await page.waitForTimeout(800);
    } else break;
  }
}

const browser = await chromium.connectOverCDP('http://127.0.0.1:9224');
const page = browser.contexts()[0]?.pages()[0];
if (!page) throw new Error('No Grok Bot page');

await completeOnboarding(page);
await shot(page, 'b8-t4-grok-03-create-bot.png');

// Fill Name — try placeholder, label, or first text input
const nameField = page.getByPlaceholder(/name/i)
  .or(page.locator('input[type=text]').first())
  .or(page.getByLabel(/^Name$/i));
await nameField.first().click();
await nameField.first().fill('BADACZ');
await page.waitForTimeout(500);

// Expand custom bot if collapsed — click "Create your own" suggestion area
const custom = page.getByText(/Create your own|custom/i).first();
if (await custom.count()) await custom.click({ timeout: 2000 }).catch(() => {});

// Job + description fields
const jobField = page.getByPlaceholder(/job|title|role/i).or(page.locator('textarea').first());
if (await jobField.count()) await jobField.first().fill(BADACZ_JOB);

const descField = page.getByPlaceholder(/description|how/i).or(page.locator('textarea').nth(1));
if (await descField.count()) {
  await descField.first().fill(BADACZ_DESC);
} else {
  const tas = page.locator('textarea');
  if ((await tas.count()) === 1) await tas.first().fill(BADACZ_DESC);
}

await shot(page, 'b8-t4-grok-04-bot-filled.png');

// Click enabled create — not disabled
const createBtn = page.locator('button[aria-label="Create your first Bot"]:not([disabled])');
if (await createBtn.count()) {
  await createBtn.click();
} else {
  await page.getByRole('button', { name: /^Get started$/i }).click({ timeout: 5000 }).catch(() => {});
  await page.getByRole('button', { name: /Create/i }).filter({ hasNot: page.locator('[disabled]') }).first().click({ timeout: 5000 }).catch(() => {});
}

await page.waitForTimeout(3000);
await shot(page, 'b8-t4-grok-05-bot-created.png');

// Chat smoke
const chatInput = page.locator('textarea').last();
if (await chatInput.count()) {
  await chatInput.fill(SMOKE_QUERY);
  await page.keyboard.press('Enter');
  console.log('Waiting 60s for BADACZ response...');
  await page.waitForTimeout(60000);
  await shot(page, 'b8-t4-grok-06-smoke-response.png');
}

const final = await bodyText(page);
writeFileSync(`${EVIDENCE}/b8-t4-grok-smoke-transcript.txt`, final, 'utf8');
console.log('Transcript saved. Preview:\n', final.slice(-2500));

await browser.close();
console.log('B8-T4 complete');
