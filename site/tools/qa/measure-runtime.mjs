// Runtime audit for EVER NEXT's self-feedback: what the desk actually does in a browser, per skin and
// viewport, written to ever-next/runtime.json for tools/build-ever-next.py. Measured, not grepped:
//   - infinite animations that are running (document.getAnimations())
//   - visible text rendered below 7px (computed font size, visible elements only)
//   PLAYWRIGHT=... node tools/qa/measure-runtime.mjs 8192        (from site/, site served on that port)
import { writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const port = process.argv[2] || '8192';
const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
const b = await chromium.launch();
const out = { page: '/desk/bitcoin/', animations: {}, tinyText: {} };
for (const skin of ['genesis', 'regalia', 'aurum', 'off']) for (const [w, h] of [[390, 844], [1280, 800]]) {
  const c = await b.newContext({ viewport: { width: w, height: h }, serviceWorkers: 'block', deviceScaleFactor: 2 });
  await c.addInitScript(k => { try { localStorage.setItem('quadcom-v57-skin', k); } catch (_) {} }, skin);
  const p = await c.newPage();
  await p.goto(`http://localhost:${port}/desk/bitcoin/?${w < 800 ? 'qc_sim=iphone13&' : ''}view=core`); await p.waitForTimeout(3500);
  const r = await p.evaluate(() => {
    const names = [...new Set(document.getAnimations().filter(a => a.playState === 'running' && a.effect?.getTiming().iterations === Infinity)
      .map(a => a.animationName || a.id || 'unnamed'))].sort();
    const sizes = [];
    for (const el of document.querySelectorAll('body *')) {
      if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
      const cs = getComputedStyle(el), r = el.getBoundingClientRect();
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0 || !r.width || !r.height || el.closest('[aria-hidden="true"],.qc-sr-only')) continue;
      if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) continue;
      // Rendered size includes any CSS zoom/scale applied by the desk's viewport fitting.
      const scale = r.width / Math.max(1, el.offsetWidth || r.width);
      const px = +(parseFloat(cs.fontSize) * (isFinite(scale) && scale > 0 ? scale : 1)).toFixed(2);
      if (px < 7) sizes.push(px);
    }
    return { skin: document.documentElement.dataset.qcTexture, names, tiny: sizes.length, min: sizes.length ? Math.min(...sizes) : null };
  });
  out.animations[`${skin} ${w}x${h}`] = r.names;
  if (skin === 'genesis') out.tinyText[`${w}x${h}`] = { count: r.tiny, minPx: r.min };
  console.log(skin.padEnd(8), `${w}x${h}`.padEnd(9), 'applied', r.skin, 'infinite', r.names.join(',') || '-', 'text<7px', r.tiny, r.min ?? '');
  await c.close();
}
await b.close();
writeFileSync(path.join(site, 'ever-next', 'runtime.json'), JSON.stringify(out, null, 1) + '\n');
console.log('ever-next/runtime.json');
