// Renders assets/og-card.jpg (1200x630, JPEG: the engraved seal compresses 4x better than PNG), the link-preview card for quadcom.live, from the site's own
// assets: the GENESIS seal, the official mark and the monospace system type. No live values.
//   PLAYWRIGHT=/path/to/playwright/index.mjs node site/tools/build-og-card.mjs
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import { writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import os from 'node:os';
const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const a = f => pathToFileURL(path.join(site, 'assets', f)).href;
const html = `<!doctype html><html><head><style>
html,body{margin:0;width:1200px;height:630px;background:#040504;overflow:hidden}
body{position:relative;font-family:ui-monospace,SFMono-Regular,Menlo,"DejaVu Sans Mono",monospace;color:#ece6d3}
.seal{position:absolute;right:-150px;top:-135px;width:900px;height:900px;background:url(${a('textures/genesis/seal.svg')}) 0 0/100% 100%;opacity:.5}
.field{position:absolute;inset:0;background:url(${a('textures/genesis/intaglio.svg')}) 0 0/96px 24px;opacity:.9}
.fade{position:absolute;inset:0;background:linear-gradient(90deg,#040504 0,#040504 38%,rgba(4,5,4,.55) 62%,rgba(4,5,4,.1))}
.frame{position:absolute;inset:22px;border:1px solid rgba(217,180,95,.5)}
.c{position:absolute;width:30px;height:30px;background-size:100% 100%}
.tl{left:22px;top:22px;background-image:url(${a('textures/genesis/corner-tl.svg')})}.tr{right:22px;top:22px;background-image:url(${a('textures/genesis/corner-tr.svg')})}
.bl{left:22px;bottom:22px;background-image:url(${a('textures/genesis/corner-bl.svg')})}.br{right:22px;bottom:22px;background-image:url(${a('textures/genesis/corner-br.svg')})}
.copy{position:absolute;left:84px;top:84px;width:760px}
.mark{width:120px;height:120px;display:block;margin:0 0 26px -6px}
h1{margin:0;font-size:86px;letter-spacing:.1em;line-height:1;font-weight:800;color:#ece6d3}
.tag{margin:18px 0 0;font-size:25px;letter-spacing:.34em;color:#d9b45f}
.rule{margin:34px 0 26px;height:10px;width:560px;background:url(${a('textures/genesis/node.svg')}) 12.5% 50%/9px 9px no-repeat,url(${a('textures/genesis/node.svg')}) 37.5% 50%/9px 9px no-repeat,url(${a('textures/genesis/node.svg')}) 62.5% 50%/9px 9px no-repeat,url(${a('textures/genesis/node.svg')}) 87.5% 50%/9px 9px no-repeat,linear-gradient(rgba(217,180,95,.5),rgba(217,180,95,.5)) 0 50%/100% 1px no-repeat}
.sub{font-size:22px;line-height:1.45;color:#b9b3a1;letter-spacing:.03em}
.url{position:absolute;left:84px;bottom:62px;font-size:22px;letter-spacing:.24em;color:#d9b45f}
</style></head><body><div class="field"></div><div class="seal"></div><div class="fade"></div>
<div class="frame"></div><i class="c tl"></i><i class="c tr"></i><i class="c bl"></i><i class="c br"></i>
<div class="copy"><img class="mark" src="${a('quadcom-logo-640.png')}" alt=""><h1>QUADCOM</h1><p class="tag">EVER NEXT PHASE</p><div class="rule"></div>
<div class="sub">A 2000-PicoProcessor market machine.<br>Four live desks. Observation, never fabrication.</div></div>
<div class="url">QUADCOM.LIVE</div></body></html>`;
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
// Rendered from a temporary file: a file:// page may load the file:// assets, an about:blank page may not.
const dir = mkdtempSync(path.join(os.tmpdir(), 'qc-og-'));
writeFileSync(path.join(dir, 'card.html'), html);
await p.goto(pathToFileURL(path.join(dir, 'card.html')).href, { waitUntil: 'load' });
const broken = await p.evaluate(() => [...document.images].filter(i => !i.naturalWidth).length);
if (broken) throw new Error(`${broken} image(s) failed to load`);
await p.waitForTimeout(300);
await p.screenshot({ path: path.join(site, 'assets', 'og-card.jpg'), type: 'jpeg', quality: 86 });
await b.close();
rmSync(dir, { recursive: true, force: true });
console.log('assets/og-card.jpg 1200x630');
