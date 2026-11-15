// Dev helper: screenshot the preview server with headless Chromium.
// node scripts/shot.mjs out.png [width] [height] [steps...]
// steps: "click:<selector>", "wait:<ms>", "key:<Key>", "eval:<js>", "goto:<hash>"
import { chromium } from 'playwright-core';
import { readdirSync } from 'node:fs';
import { homedir } from 'node:os';

const [out, w = '1440', h = '900', ...steps] = process.argv.slice(2);
const cache = homedir() + '/Library/Caches/ms-playwright';
const shell = readdirSync(cache).filter((d) => d.startsWith('chromium_headless_shell')).sort().pop();
const exe = `${cache}/${shell}/chrome-headless-shell-mac-arm64/chrome-headless-shell`;
const browser = await chromium.launch({ executablePath: exe, args: (process.env.GL ?? '--use-angle=metal --ignore-gpu-blocklist').split(' ') });
const mobile = +w < 600;
// RM=1 asks for reduced motion
const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile, reducedMotion: process.env.RM ? 'reduce' : 'no-preference' });
const logs = [];
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
// headless GPU start-up is flaky; reload until WebGL comes up
for (let tries = 0; tries < 5; tries++) {
  await page.goto(process.env.URL ?? 'http://127.0.0.1:4317/', { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  if (!(await page.$('.fatal'))) break;
  console.log('webgl failed, retrying');
}
for (const s of steps) {
  const [k, ...rest] = s.split(':');
  const v = rest.join(':');
  if (k === 'click') await page.click(v, { timeout: 8000 });
  else if (k === 'wait') await page.waitForTimeout(+v);
  else if (k === 'key') await page.keyboard.press(v);
  else if (k === 'eval') console.log('eval:', await page.evaluate(v));
  else if (k === 'goto') await page.evaluate((hash) => (location.hash = hash), v);
  else if (k === 'shot') await page.screenshot({ path: v });
}
await page.screenshot({ path: out, ...(out.endsWith('.jpg') ? { type: 'jpeg', quality: 70 } : {}) });
console.log(logs.filter((l) => !l.includes('GPU stall')).slice(0, 30).join('\n'));
await browser.close();
