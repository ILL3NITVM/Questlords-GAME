// Proves each desk accepts its own market's live ticks: a fake Coinbase websocket streams ticker
// messages for the desk's product id at a realistic price, and the desk must go LIVE on them.
// A desk that rejected them (wrong product id, Bitcoin-sized integrity band) would stay on its seed price.
const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
const SITE = process.env.SITE || 'http://127.0.0.1:8192';
const b = await chromium.launch({ channel: 'chromium', args: ['--use-angle=swiftshader'] });
for (const [slug, product, base] of [['bitcoin', 'BTC-USD', 84123.45], ['dogecoin', 'DOGE-USD', 0.21234], ['xrp', 'XRP-USD', 2.6123], ['litecoin', 'LTC-USD', 101.37]]) {
  const c = await b.newContext({ viewport: { width: 844, height: 390 }, serviceWorkers: 'block' });
  await c.addInitScript(([product, base]) => {
    class FakeWS extends EventTarget {
      constructor(url) { super(); this.url = url; this.readyState = 0; setTimeout(() => { this.readyState = 1; this.onopen?.({}); this.dispatchEvent(new Event('open')); }, 50); }
      send(msg) {
        const sub = JSON.parse(msg); if (sub.type !== 'subscribe') return;
        this.subscribed = sub.product_ids;
        let seq = 1000, p = base;
        this.timer = setInterval(() => {
          p = p * (1 + (Math.sin(seq / 7) * 0.0004));
          const m = { type: 'ticker', product_id: product, price: String(p), sequence: seq++, side: seq % 2 ? 'buy' : 'sell', last_size: '1.5', time: new Date().toISOString() };
          const ev = { data: JSON.stringify(m) }; this.onmessage?.(ev);
        }, 120);
      }
      close() { clearInterval(this.timer); this.readyState = 3; }
    }
    window.WebSocket = FakeWS;
    window.__subscribed = () => window.__lastWS?.subscribed;
  }, [product, base]);
  const p = await c.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message.slice(0, 80)));
  await p.goto(`${SITE}/desk/${slug}/?view=core`); await p.waitForTimeout(9000);
  const r = await p.evaluate(() => { const t = window.__quadcomTelemetry?.() || {}; return { price: document.getElementById('price').textContent, meta: document.getElementById('priceMeta')?.textContent, source: t.realtime?.source ?? null, ticks: t.realtime?.ticks, invalid: t.realtime?.invalid, hist: t.hist }; });
  console.log(slug.padEnd(9), product.padEnd(9), JSON.stringify(r), errs.join('|'));
  await c.close();
}
await b.close();
