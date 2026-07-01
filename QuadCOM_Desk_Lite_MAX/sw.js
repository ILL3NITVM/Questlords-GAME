/* QuadCOM Desk Lite MAX — Service Worker
 * Fail-safe cache protocol: the install loop caches each asset individually
 * and traps every fetch, so a missing/unresolvable asset (e.g. icon-512.png
 * not served over a bare python http.server or an offline directory) is
 * bypassed smoothly without ever rejecting the install or blocking the
 * script execution pipeline. */
const CACHE = "quadcom-desk-lite-max-v1";
const CORE = "./index.html";
const ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./sw.js",
  "./icon-512.png"
];

/* Cache one asset at a time; never let a single failure reject the batch. */
async function cacheAsset(cache, url) {
  try {
    const res = await fetch(url, { cache: "no-cache" });
    // Accept opaque (cross-origin) and OK responses; skip hard errors.
    if (res && (res.ok || res.type === "opaque")) {
      await cache.put(url, res.clone());
    }
  } catch (_) {
    /* Asset failed to resolve — bypass smoothly, keep installing. */
  }
}

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    let cache;
    try { cache = await caches.open(CACHE); } catch (_) { cache = null; }
    if (cache) {
      // Granular trapping: settle all, ignore individual rejections.
      await Promise.allSettled(ASSETS.map(url => cacheAsset(cache, url)));
    }
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.allSettled(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    } catch (_) { /* no-op */ }
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
        await Promise.allSettled(ASSETS.map(url => cacheAsset(cache, url)));
      } catch (_) { /* no-op */ }
    })());
  }
});

/* Cache-first with network fallback; every branch is trapped so a failed
 * fetch never surfaces as an uncaught exception. Navigations fall back to
 * the cached shell so the app still boots fully offline. */
self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;

  event.respondWith((async () => {
    try {
      const cached = await caches.match(req);
      if (cached) return cached;
    } catch (_) { /* cache lookup failed — fall through to network */ }

    try {
      const res = await fetch(req);
      if (res && (res.ok || res.type === "opaque")) {
        try {
          const copy = res.clone();
          const cache = await caches.open(CACHE);
          await cache.put(req, copy);
        } catch (_) { /* opportunistic caching failed — ignore */ }
      }
      return res;
    } catch (_) {
      // Offline / asset unavailable: serve the shell for navigations,
      // otherwise a benign empty response so nothing throws.
      if (req.mode === "navigate") {
        const shell = await caches.match(CORE);
        if (shell) return shell;
      }
      const fallback = await caches.match(req);
      if (fallback) return fallback;
      return new Response("", { status: 504, statusText: "offline" });
    }
  })());
});
