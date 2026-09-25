const CACHE='quadcom-genesis-public-v53';
const CORE=['/','/qc-site.css','/qc-site.js','/manifest.json','/assets/quadcom-official-logo.png','/assets/bitcoin.png','/assets/favicon-32.png','/assets/apple-touch-icon.png',
'/learn/','/how-it-works/','/quadcom/','/data/','/glossary/','/desk/bitcoin/','/desk/bitcoin/glimmer.js','/desk/bitcoin/glimmer-vision.js',
'/assets/textures/aurum-brushed.png','/assets/textures/obsidian-grain.png','/assets/textures/carbon-weave.png','/assets/textures/glass-sheen.png','/assets/textures/quad-lattice.png',
...['mandala','corner-tl','corner-tr','corner-bl','corner-br','filigree-band','starburst','kaleido-tile'].map(n=>`/assets/textures/regalia/${n}.png`)];
// One missing file must not abort the whole install, and only good same-origin responses are cached.
const warm=()=>caches.open(CACHE).then(c=>Promise.allSettled(CORE.map(u=>c.add(u))));
const keep=(req,res)=>{if(res&&res.ok&&res.type==='basic'&&!res.redirected){const x=res.clone();caches.open(CACHE).then(c=>c.put(req,x)).catch(()=>{})}return res};
self.addEventListener('install',e=>e.waitUntil(warm().then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;const u=new URL(e.request.url);if(u.origin!==location.origin)return;
if(e.request.mode==='navigate'){e.respondWith(fetch(e.request).then(r=>keep(e.request,r)).catch(()=>caches.match(e.request,{ignoreSearch:true}).then(r=>r||caches.match('/'))));return;}
e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(n=>keep(e.request,n))));});
self.addEventListener('message',e=>{if(e.data&&String(e.data.type||'').startsWith('QUADCOM_PREWARM'))e.waitUntil(warm())});
