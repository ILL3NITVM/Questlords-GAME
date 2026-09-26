// EVER NEXT: composer integrity (node) and page behaviour (Playwright).
//   node tools/qa/ever-next.mjs 8192        (from site/, with the site served on that port)
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const ax = JSON.parse(readFileSync(path.join(site, 'ever-next/axes.json'), 'utf8'));
const ctx = {}; vm.createContext(ctx); vm.runInContext(readFileSync(path.join(site, 'ever-next/core.js'), 'utf8'), ctx);
const feed = ctx.QCEverNext.create(ax);
const fail = m => { console.log('FAIL', m); process.exitCode = 1; };
if (feed.total !== ax.perPass) fail(`composer total ${feed.total} != builder perPass ${ax.perPass}`);
if (feed.pairs !== ax.pairs.length) fail(`pairs ${feed.pairs} != ${ax.pairs.length}`);
const ids = new Set(); let bad = 0, maxLen = 0;
for (let i = 0; i < feed.total; i++) { const it = feed.item(i); ids.add(it.id); if (/\{|\}|undefined|null/.test(it.text + it.bar)) bad++; maxLen = Math.max(maxLen, it.text.length); }
if (ids.size !== feed.total) fail(`ids not unique: ${ids.size} of ${feed.total}`);
if (bad) fail(`${bad} items with unfilled placeholders`);
const firstMeasured = [...feed.order.slice(0, ax.evidence.length ? 5 : 0)].every(i => feed.item(i).evidence);
if (!firstMeasured) fail('feed does not start with measured items');
const sweep = feed.select({ aspect: 'contrast', depth: '0' }, null, 'surface');
const polish = feed.select({ surface: 'quote', depth: '0' }, null, 'aspect');
const c1 = feed.compose(feed.select({}, null), 8, 42), c2 = feed.compose(feed.select({}, null), 8, 42);
if (JSON.stringify(c1) !== JSON.stringify(c2)) fail('compose is not deterministic for a seed');
if (new Set(c1.map(i => feed.item(i).aspect.id)).size !== c1.length) fail('compose repeats an aspect');
const narrow = feed.compose(feed.select({ aspect: 'precision' }, null), 5, 7);
if (narrow.length !== 5) fail(`compose under a single-aspect facet returned ${narrow.length} of 5`);
const td = feed.today(new Date(2026, 8, 26));
if (td.length !== 5 || new Set(td.map(i => feed.item(i).aspect.id)).size !== 5) fail('today is not five distinct aspects');
console.log(`composer: ${feed.total.toLocaleString('en-US')} items per pass, ${feed.pairs} pairings, ids unique, longest item ${maxLen} chars`);
console.log(`sweep contrast@OBSERVE ${sweep.length} · polish quote@OBSERVE ${polish.length} · compose(8,42) ${c1.map(i => feed.item(i).id).join(' ')}`);

const port = process.argv[2];
if (port) {
  const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
  const b = await chromium.launch(); const c = await b.newContext({ serviceWorkers: 'block', viewport: { width: 390, height: 844 } });
  const p = await c.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(`http://localhost:${port}/ever-next/`); await p.waitForSelector('[data-en-controls]:not([hidden])');
  const st = async () => p.evaluate(() => ({ n: document.querySelectorAll('.qc-en-item').length, count: document.querySelector('.qc-en-count').textContent, first: document.querySelector('.qc-en-id')?.textContent }));
  console.log('feed', await st());
  await p.click('[data-more]'); await p.waitForTimeout(100); console.log('more', (await st()).n);
  await p.click('[data-mode="today"]'); console.log('today', await st());
  await p.click('[data-mode="sweep"]'); console.log('sweep', await st());
  await p.selectOption('[data-f="aspect"]', 'precision'); console.log('sweep precision', await st());
  await p.click('[data-mode="compose"]'); await p.fill('[data-f="seed"]', '42'); await p.dispatchEvent('[data-f="seed"]', 'change'); console.log('compose', await st());
  await p.click('[data-reset]'); await p.fill('[data-f="q"]', 'contrast'); await p.waitForTimeout(400); console.log('search contrast', await st());
  await p.click('[data-reset]'); await p.click('.qc-en-item [data-set="surface"]'); console.log('chip → surface', await p.inputValue('[data-f="surface"]'), (await st()).count);
  await p.click('.qc-en-item [data-mark="done"]'); const id = await p.getAttribute('.qc-en-item', 'data-id');
  await p.reload(); await p.waitForSelector('[data-en-controls]:not([hidden])'); await p.selectOption('[data-f="status"]', 'done');
  console.log('mark persists', await st(), 'expected', id);
  // endless: run past the end of a small result set in FEED mode
  await p.click('[data-reset]'); await p.selectOption('[data-f="surface"]', 'quote'); await p.selectOption('[data-f="aspect"]', 'precision'); await p.selectOption('[data-f="depth"]', '0');
  const small = await st(); await p.click('[data-more]'); console.log('endless', small.n, '→', (await st()).n, await p.textContent('[data-more]'), (await p.$$eval('.qc-en-id', a => a.at(-1).textContent)));
  await p.click('[data-reset]'); await p.screenshot({ path: 'ever-next.png' });
  console.log('errors', errs); await b.close();
}
