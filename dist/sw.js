const CACHE_NAME = 'gcp-explorer-pwa-1793251273';
const PRECACHE_URLS = [
  './',
  './index.html',
  './regions.html',
  './models.html',
  './pricing-sla.html',
  './capabilities.html',
  './pops.html',
  './whatsnew.html',
  './arch.html',
  './faqs.html',
  './manifest.webmanifest',
  './assets/icon.svg',
  './assets/style.css',
  './assets/app.js',
  './data/matrix_data.js',
  './data/mobile_catalog.json'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS).catch(() => {}))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request)
      .then((networkResp) => {
        if (networkResp && networkResp.status === 200) {
          const copy = networkResp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return networkResp;
      })
      .catch(() => caches.match(event.request, { ignoreSearch: true }).then((cached) => cached || caches.match('./index.html')))
  );
});
