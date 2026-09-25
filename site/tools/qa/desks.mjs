// Every desk: audit in portrait + landscape, desk bar, price formatting, and storage isolation between desks.
const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
const SITE = process.env.SITE || 'http://127.0.0.1:8192';
const b = await chromium.launch({ channel: 'chromium', args: ['--use-angle=swiftshader'] });
for (const [slug, sym] of [['bitcoin', 'BTC'], ['dogecoin', 'DOGE'], ['xrp', 'XRP'], ['litecoin', 'LTC']]) for (const [w, h] of [[390, 844], [844, 390]]) {
  const c = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2, serviceWorkers: 'block' }); const p = await c.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message.slice(0, 80)));
  await p.goto(`${SITE}/desk/${slug}/?qc_sim=iphone13&view=core`); await p.waitForTimeout(2800);
  const r = await p.evaluate(() => { const a = __quadcomVisualAudit(), bar = document.querySelector('.qcDeskBar'), bs = getComputedStyle(bar), br = bar.getBoundingClientRect(), ck = document.querySelector('.cockpit').getBoundingClientRect();
    return { out: a.outside.length, ovf: a.overflow, hdr: a.headerOverflow, coll: (a.collisions || []).length, marks: a.pass !== undefined ? document.querySelectorAll('.btcIcon').length : 0, tape: document.querySelector('.tapeTitle')?.textContent.trim(), price: document.getElementById('price').textContent, entry: document.getElementById('bestEntry')?.textContent,
      bar: bs.display === 'none' ? 'hidden' : `${Math.round(br.top)}-${Math.round(br.bottom)} active=${bar.querySelector('[aria-current]')?.dataset.asset} cockpitBottom=${Math.round(ck.bottom)}` }; });
  console.log(`${sym.padEnd(4)} ${w}x${h}`, JSON.stringify(r), errs.join('|'));
  if (w === 390) await p.screenshot({ path: `desk-${slug}-portrait.png` });
  await c.close();
}
// Storage isolation: run each desk in turn in ONE browser profile, force its lifecycle save, and record exactly
// which keys it wrote. Each desk must write only its own names, and never modify another desk's state.
const c = await b.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' }); const p = await c.newPage();
const snap = () => p.evaluate(() => Object.fromEntries(Object.keys(localStorage).filter(k => k.startsWith('quadcom') && k !== 'quadcom-v46-skin').map(k => [k, localStorage.getItem(k).length + ':' + [...localStorage.getItem(k)].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) >>> 0, 7)])));
let before = {};
for (const [slug, id] of [['bitcoin', 'btc'], ['dogecoin', 'doge'], ['xrp', 'xrp'], ['litecoin', 'ltc']]) {
  await p.goto(`${SITE}/desk/${slug}/`); await p.waitForTimeout(5000);
  // Leave the desk for a same-origin blank route so its own unload-time saves land before the snapshot.
  await p.goto(`${SITE}/robots.txt`); await p.waitForTimeout(800);
  const now = await snap();
  const wrote = Object.keys(now).filter(k => now[k] !== before[k]);
  const foreign = wrote.filter(k => id === 'btc' ? /-(doge|xrp|ltc)(\.json)?$/.test(k) : !k.endsWith('-' + id));
  console.log(`${id.padEnd(4)} wrote ${wrote.length} key(s): ${wrote.join(' ')}${foreign.length ? '  ✗ FOREIGN: ' + foreign.join(' ') : '  ✓ own keys only'}`);
  before = now;
}
const idb = await p.evaluate(async () => (await indexedDB.databases?.() || []).map(d => d.name).filter(n => n.startsWith('quadcom')).sort());
console.log('IndexedDB databases:', idb.join(' '));
await b.close();
