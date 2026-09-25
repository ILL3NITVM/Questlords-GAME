const CACHE='quadcom-genesis-public-v52';
const CORE=['/','/qc-site.css','/qc-site.js','/manifest.json','/assets/quadcom-official-logo.png','/assets/bitcoin.png','/learn/','/how-it-works/','/quadcom/','/data/','/glossary/','/desk/bitcoin/'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;const u=new URL(e.request.url);
if(e.request.mode==='navigate'){e.respondWith(fetch(e.request).then(r=>{const x=r.clone();caches.open(CACHE).then(c=>c.put(e.request,x));return r}).catch(()=>caches.match(e.request).then(r=>r||caches.match('/'))));return;}
e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(n=>{if(u.origin===location.origin){const x=n.clone();caches.open(CACHE).then(c=>c.put(e.request,x));}return n;})));});
self.addEventListener('message',e=>{if(e.data&&String(e.data.type||'').startsWith('QUADCOM_PREWARM'))e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)))});
