const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
const b = await chromium.launch({ channel: 'chromium', args: ['--use-angle=swiftshader'] });
for (const [w, h, sim] of [[390, 844, 1], [844, 390, 1]]) for (const view of ['core', 'fleet', 'all', 'vision']) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, serviceWorkers: 'block', deviceScaleFactor: 2 }); const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message.slice(0, 80)));
  await p.goto(`http://127.0.0.1:8192/desk/bitcoin/?${sim ? 'qc_sim=iphone13&' : ''}view=${view}`); await p.waitForTimeout(3000);
  const r = await p.evaluate(() => { const a = __quadcomVisualAudit(); return { build: document.documentElement.dataset.qcBuild, panels: a.visiblePanels.length, out: a.outside, ovf: a.overflow, hdr: a.headerOverflow, coll: (a.collisions || []).length }; });
  console.log(w + 'x' + h, view.padEnd(6), JSON.stringify(r), errs.join('|'));
  if (view === 'core' || view === 'vision') await p.screenshot({ path: `v53b-${view}-${w}x${h}.png` });
  await ctx.close();
}
await b.close();
