const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
import { execSync } from 'node:child_process';
const b = await chromium.launch({ channel: 'chromium' }); const c = await b.newContext({ viewport: { width: 390, height: 844 } }); const p = await c.newPage();
await p.goto('http://127.0.0.1:8192/'); await p.evaluate(() => navigator.serviceWorker.ready); await p.goto('http://127.0.0.1:8192/glossary/'); await p.waitForTimeout(800);
execSync("for p in $(ps -eo pid,args | awk '/http.server 8192/ && !/awk/ {print $1}'); do kill $p; done");
await p.waitForTimeout(500);
for (const u of ['/glossary/', '/desk/bitcoin/?view=vision', '/never-visited/']) { await p.goto('http://127.0.0.1:8192' + u).catch(e => console.log('nav err', e.message.slice(0, 60))); console.log('server down', u.padEnd(28), '→', await p.evaluate(() => document.title)); }
await b.close();
