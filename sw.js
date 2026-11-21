/* CHAPTER / service worker: the app opens like an app and still opens offline.
   The page itself is fetched fresh when online (so updates arrive at once) and kept as a fallback.
   Accounts (/api) and books (/proxy) are never cached here: the server and IndexedDB handle those. */
const CACHE = 'chapter-shell-v4';
const SHELL = ['/index.html', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png', '/icons/icon-maskable-512.png', '/icons/apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('chapter-shell-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;            // fonts, CDNs: browser cache
  if (url.pathname === '/' || url.pathname === '/index.html') {
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        const response = await fetch(req);
        if (response.ok && (response.headers.get('Content-Type') || '').includes('text/html')) {
          await cache.put('/index.html', response.clone()).catch(() => {});
        }
        return response;
      } catch (error) {
        const saved = await cache.match('/index.html');
        if (saved) return saved;
        throw error;
      }
    })());
    return;
  }
  if (SHELL.includes(url.pathname)) {
    e.respondWith(caches.open(CACHE).then(cache => cache.match(url.pathname)).then(hit => hit || fetch(req)));
  }
});
