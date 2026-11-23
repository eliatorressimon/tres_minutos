// Guarda una copia de la web para que el botón de emergencia funcione sin conexión.
// La web y los datos se piden primero a la red; si no hay red, se usa la copia.
// Las librerías y las fuentes se sirven de la copia si ya están guardadas.
const CACHE = 'tres-minutos-v1';
const BASICO = ['./', 'index.html', 'datos.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(BASICO)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  const propio = u.origin === location.origin;
  const libreria = /cdn\.jsdelivr\.net|fonts\.(googleapis|gstatic)\.com/.test(u.host);
  if (propio) {
    e.respondWith(fetch(r).then(res => {
      if (res.ok) { const copia = res.clone(); caches.open(CACHE).then(c => c.put(r, copia)); }
      return res;
    }).catch(() => caches.match(r, { ignoreSearch: true }).then(x => x || caches.match('index.html'))));
  } else if (libreria) {
    e.respondWith(caches.match(r).then(x => x || fetch(r).then(res => {
      const copia = res.clone(); caches.open(CACHE).then(c => c.put(r, copia)); return res;
    })));
  }
});
