import { chromium } from 'playwright';

const browser = await chromium.connectOverCDP('http://127.0.0.1:9224');
for (const ctx of browser.contexts()) {
  for (const page of ctx.pages()) {
    console.log('PAGE:', page.url(), await page.title());
    const text = await page.evaluate(() => document.body?.innerText?.slice(0, 4000) || '');
    console.log('TEXT:\n', text);
    await page.screenshot({ path: 'docs/evidence/b8-t4-grok-bot-ui.png', fullPage: true });
  }
}
await browser.close();
