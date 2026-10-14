// sw.js — app shell keshi (offline ochilishi uchun)
const CACHE = "mmtri-davomat-v1";
const ASSETS = [
  "./",
  "./index.html",
  "./style.css?v=1",
  "./app.js?v=1",
  "./logo.png",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// API so'rovlarini keshламaymiz (doim yangi).
// Qolgani: TARMOQ-BIRINCHI — yangilanishlar darhol ko'rinadi,
// offline bo'lganda esa keshdagi nusxa ishlaydi.
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.includes("/api/")) {
    return; // tarmoqdan (default)
  }
  e.respondWith(
    fetch(e.request)
      .then((resp) => {
        if (resp && resp.ok && e.request.method === "GET") {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
        }
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});
