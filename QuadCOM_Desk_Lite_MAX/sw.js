const CACHE = "quadcom-desk-lite-max-revamp-v4";
const ASSETS = ["./", "./index.html", "./manifest.json", "./sw.js", "./icon-512.png"];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.allSettled(ASSETS.map(async url => {
      try {
        const response = await fetch(url, { cache: "reload" });
        if (response && response.ok) {
          await cache.put(url, response);
        }
      } catch (_) {
        // Asset caching is opportunistic so one missing file never breaks install.
      }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  event.respondWith((async () => {
    const cached = await caches.match(event.request, { ignoreSearch: true });
    if (cached) return cached;
    try {
      const response = await fetch(event.request);
      if (response && response.ok && event.request.method === "GET") {
        const cache = await caches.open(CACHE);
        cache.put(event.request, response.clone()).catch(() => {});
      }
      return response;
    } catch (_) {
      if (event.request.mode === "navigate") {
        return (await caches.match("./index.html")) || (await caches.match("./"));
      }
      return new Response("", { status: 204, statusText: "cached runtime miss" });
    }
  })());
});
