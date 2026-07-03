/* QuadCOM Desk Lite MAX — Stack Service Worker
 * Fail-safe cache protocol: every asset (including the full ES-module graph)
 * is cached individually with per-asset trapping, so a single unresolvable file
 * never rejects install or blocks the pipeline. Cache-first with a navigation
 * fallback to the shell keeps the app fully offline-capable. */
const CACHE = "quadcom-stack-v4";
const CORE = "./index.html";
const ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./sw.js",
  "./icon-512.png",
  "./styles/theme.css",
  "./styles/app.css",
  "./src/config.js",
  "./src/util.js",
  "./src/main.js",
  "./src/core/store.js",
  "./src/data/feed.js",
  "./src/data/simFeed.js",
  "./src/data/liveFeed.js",
  "./src/data/wallet.js",
  "./src/data/simWallet.js",
  "./src/data/instruments.js",
  "./src/data/liveWallet.js",
  "./src/engines/account.js",
  "./src/engines/council.js",
  "./src/engines/governor.js",
  "./src/engines/execution.js",
  "./src/engines/autopilot.js",
  "./src/engines/analytics.js",
  "./src/engines/session.js",
  "./src/audit.js",
  "./src/reports.js",
  "./src/copykit.js",
  "./src/ui/chart.js",
  "./src/ui/components.js",
  "./src/ui/render.js",
  "./src/ui/router.js",
  "./src/ui/gateway.js",
  "./src/ui/toast.js",
  "./src/ui/theme.js",
  "./src/ui/sparkline.js",
  "./src/ui/pages.js",
  "./src/ui/live.js",
  "./src/ui/views/desk.js",
  "./src/ui/views/exec.js",
  "./src/ui/views/council.js",
  "./src/ui/views/gov.js",
  "./src/ui/views/more.js"
];

async function cacheAsset(cache, url) {
  try {
    const res = await fetch(url, { cache: "reload" });
    if (res && (res.ok || res.type === "opaque")) await cache.put(url, res.clone());
  } catch (_) { /* asset unresolvable — bypass smoothly */ }
}

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    let cache = null;
    try { cache = await caches.open(CACHE); } catch (_) {}
    if (cache) await Promise.allSettled(ASSETS.map(u => cacheAsset(cache, u)));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.allSettled(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    } catch (_) {}
    await self.clients.claim();
  })());
});

self.addEventListener("message", event => {
  const data = event.data || {};
  if (data.type === "SKIP_WAITING") self.skipWaiting();
  if (data.type === "SOFT_RELOAD_CACHE") {
    event.waitUntil((async () => {
      try {
        await caches.delete(CACHE);
        const cache = await caches.open(CACHE);
        await Promise.allSettled(ASSETS.map(u => cacheAsset(cache, u)));
      } catch (_) {}
    })());
  }
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  event.respondWith((async () => {
    try {
      const cached = await caches.match(req, { ignoreSearch: true });
      if (cached) return cached;
    } catch (_) {}
    try {
      const res = await fetch(req);
      if (res && (res.ok || res.type === "opaque")) {
        try { const copy = res.clone(); const cache = await caches.open(CACHE); await cache.put(req, copy); } catch (_) {}
      }
      return res;
    } catch (_) {
      if (req.mode === "navigate") {
        const shell = await caches.match(CORE);
        if (shell) return shell;
      }
      const fb = await caches.match(req);
      if (fb) return fb;
      return new Response("", { status: 504, statusText: "offline" });
    }
  })());
});
