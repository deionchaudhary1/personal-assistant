// Minimal pass-through service worker. This app is a live local API, not
// cached data, so there is no offline story — the worker exists only to
// satisfy Chrome's PWA installability check. No fetch handler: the browser
// hits the network directly, exactly as if no worker were installed.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});
