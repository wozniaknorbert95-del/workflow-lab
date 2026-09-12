import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const SMOKE = `Research task (official docs only):
For public GitHub repositories like wozniaknorbert95-del/workflow-lab — are standard GitHub-hosted runner minutes free?
Format: Facts (URL + date 2026-09-12) → Hypotheses (if any) → One recommendation. No code.`;

const browser = await chromium.connectOverCDP('http://127.0.0.1:9224');
const page = browser.contexts()[0].pages()[0];

// Ensure BADACZ chat open
await page.getByText(/^BADACZ$/).first().click({ timeout: 5000 }).catch(() => {});
await page.waitForTimeout(1500);

// Discover input type
const inputInfo = await page.evaluate(() => {
  const ta = document.querySelectorAll('textarea');
  const ce = document.querySelectorAll('[contenteditable=true]');
  return {
    textareaCount: ta.length,
    textareaPlaceholders: [...ta].map((t) => t.placeholder),
    ceCount: ce.length,
    ceTags: [...ce].map((e) => e.tagName + (e.getAttribute('data-placeholder') || e.getAttribute('aria-label') || '')),
  };
});
console.log('inputs:', inputInfo);

const input = page.locator('[contenteditable=true]').last()
  .or(page.locator('textarea').last());

await input.click({ timeout: 10000 });
await input.fill(SMOKE);
await page.keyboard.press('Enter');
console.log('Query sent, waiting 90s...');
await page.waitForTimeout(90000);

await page.screenshot({ path: 'docs/evidence/b8-t4-grok-07-smoke-response.png', fullPage: true });
const text = await page.evaluate(() => document.body.innerText);
writeFileSync('docs/evidence/b8-t4-grok-smoke-transcript.txt', text, 'utf8');
console.log('\n--- RESPONSE TAIL ---\n', text.slice(-4000));
await browser.close();
