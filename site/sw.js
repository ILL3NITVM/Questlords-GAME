const CACHE='quadcom-genesis-public-v57';
const CORE=['/','/404.html','/offline.html','/qc-site.css?v=57','/qc-site.js?v=57','/assets/icons.svg','/assets/textures/genesis/seal-watermark.svg','/assets/textures/genesis/intaglio.svg','/assets/textures/genesis/intaglio-dense.svg','/assets/textures/genesis/corner-tl.svg','/assets/textures/genesis/corner-tr.svg','/assets/textures/genesis/corner-bl.svg','/assets/textures/genesis/corner-br.svg','/assets/textures/genesis/band.svg','/assets/textures/genesis/band-quiet.svg','/assets/textures/genesis/pip.svg','/assets/textures/genesis/node.svg','/assets/textures/genesis/seal.svg','/assets/textures/genesis/bezel.svg','/manifest.json','/assets/quadcom-official-logo.png','/assets/quadcom-logo-96.png','/assets/quadcom-logo-640.png','/assets/bitcoin.png','/assets/favicon-32.png','/assets/apple-touch-icon.png',
'/learn/','/how-it-works/','/quadcom/','/data/','/glossary/','/catalog/','/desk/','/desk/bitcoin/','/desk/dogecoin/','/desk/xrp/','/desk/litecoin/','/assets/dogecoin.png','/assets/xrp.png','/assets/litecoin.png','/desk/bitcoin/glimmer.js','/desk/bitcoin/glimmer-vision.js',
'/assets/textures/aurum-brushed.png','/assets/textures/obsidian-grain.png','/assets/textures/carbon-weave.png','/assets/textures/glass-sheen.png','/assets/textures/quad-lattice.png',
...['mandala','corner-tl','corner-tr','corner-bl','corner-br','filigree-band','starburst','kaleido-tile'].map(n=>`/assets/textures/regalia/${n}.png`)];
// One missing file must not abort the whole install, and only good same-origin responses are cached.
const warm=()=>caches.open(CACHE).then(c=>Promise.allSettled(CORE.map(u=>c.add(u))));
const keep=(req,res)=>{if(res&&res.ok&&res.type==='basic'&&!res.redirected){const x=res.clone();caches.open(CACHE).then(c=>c.put(req,x)).catch(()=>{})}return res};
self.addEventListener('install',e=>e.waitUntil(warm().then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;const u=new URL(e.request.url);if(u.origin!==location.origin)return;
if(e.request.mode==='navigate'){e.respondWith(fetch(e.request).then(r=>keep(e.request,r)).catch(()=>caches.match(e.request,{ignoreSearch:true}).then(r=>r||caches.match('/offline.html'))));return;}
// Stale-while-revalidate: answer from cache at once, refresh it in the background, so a deploy reaches returning visitors on their next load.
e.respondWith(caches.match(e.request).then(r=>{const net=fetch(e.request).then(n=>keep(e.request,n));if(r){e.waitUntil(net.catch(()=>{}));return r}return net}));});
self.addEventListener('message',e=>{if(e.data&&String(e.data.type||'').startsWith('QUADCOM_PREWARM'))e.waitUntil(warm())});
