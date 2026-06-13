/* =========================================================================
   Service Worker — VoiceForge PWA (IDEA-21)
   Strategy: Cache-first for static assets, network-first for API calls.
   ========================================================================= */

const CACHE_NAME = "voiceforge-v1";

const PRECACHE = [
  "/",
  "/login",
  "/register",
  "/static/css/styles.css",
  "/static/js/api.js",
  "/static/js/app.js",
  "/static/js/auth.js",
  "/static/manifest.json",
];

/* ── Install: pre-cache shell ────────────────────────────────────────────── */
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

/* ── Activate: delete old caches ─────────────────────────────────────────── */
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

/* ── Fetch: cache-first for assets, network-first for /api ──────────────── */
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // Never cache API calls or audio blobs
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/audio")) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Cache-first for static assets
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((response) => {
        if (response.ok && e.request.method === "GET") {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return response;
      });
    })
  );
});
