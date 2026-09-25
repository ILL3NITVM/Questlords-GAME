const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
const base = 'http://127.0.0.1:' + (process.argv[2] || 8192);
const routes = ['/404.html', '/offline.html', '/', '/desk/', '/desk/bitcoin/', '/desk/dogecoin/', '/desk/xrp/', '/desk/litecoin/', '/learn/', '/how-it-works/', '/quadcom/', '/data/', '/glossary/', '/catalog/'];
const b = await chromium.launch({ channel: 'chromium', args: ['--use-angle=swiftshader'] });
for (const [w, h] of [[390, 844], [1280, 800]]) for (const r of routes) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, serviceWorkers: 'block' }); const p = await ctx.newPage();
  const fails = new Set(), errs = [];
  p.on('response', x => { if (x.status() >= 400 && x.url().startsWith(base)) fails.add(x.status() + ' ' + x.url().replace(base, '')); });
  p.on('pageerror', e => errs.push(e.message.slice(0, 120)));
  p.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|ERR_|WebSocket|tunnel/.test(m.text())) errs.push(m.text().slice(0, 120)); });
  await p.goto(base + r, { waitUntil: 'load' }); await p.waitForTimeout(r.includes('desk') ? 4000 : 800);
  const info = await p.evaluate(() => {
    const docW = document.documentElement.scrollWidth, vw = innerWidth;
    const small = new Set(); let tiny = 0, lowC = 0;
    const lum = c => { const m = c.match(/[\d.]+/g); if (!m) return 1; const [R, G, B] = m.slice(0, 3).map(v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }); return .2126 * R + .7152 * G + .0722 * B; };
    for (const el of document.querySelectorAll('body *')) {
      if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
      const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || !el.getClientRects().length) continue;
      const fs = parseFloat(cs.fontSize); if (fs < 9) { tiny++; small.add(fs); }
      const L1 = lum(cs.color), L2 = 0.0015; if ((L1 + .05) / (L2 + .05) < 4.5) lowC++;
    }
    const imgsNoAlt = [...document.images].filter(i => !i.hasAttribute('alt')).length;
    return { hscroll: docW > vw + 1, tiny, sizes: [...small].sort((a, b) => a - b).slice(0, 6), lowContrast: lowC, imgsNoAlt, title: document.title, desc: !!document.querySelector('meta[name=description]'), lang: document.documentElement.lang, h1: document.querySelectorAll('h1').length, skin: document.documentElement.dataset.qcTexture || null, glimmer: !!window.GLIMMER };
  });
  console.log(w, r, JSON.stringify(info), '\n   fails:', [...fails].join(' | ') || '-', '\n   errors:', errs.slice(0, 4).join(' | ') || '-');
  await ctx.close();
}
await b.close();
