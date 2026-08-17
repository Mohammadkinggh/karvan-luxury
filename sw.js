const CACHE_NAME = 'karvan-v1';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './assets/js/tailwind.cdn.js',
  './assets/js/lucide.min.js',
  './assets/js/three.min.js',
  './assets/js/confetti.browser.min.js'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((resp) => resp || fetch(e.request))
  );
});
