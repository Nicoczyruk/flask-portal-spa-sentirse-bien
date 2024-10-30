self.addEventListener('install', (event) => {
    console.log('[Service Worker] Install event');
    event.waitUntil(
      fetch('/asset-manifest.json')
        .then((response) => response.json())
        .then((assets) => {
          const urlsToCache = [
            '/',
            '/index.html',
            assets['main.js'],
            assets['main.css'],
          ];
          return caches.open('spa-cache-v1').then((cache) => {
            return cache.addAll(urlsToCache);
          });
        })
        .catch((error) => {
          console.error('[Service Worker] Failed to cache assets:', error);
        })
    );
  });
  
  
  self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activate event');
    event.waitUntil(
      caches.keys().then((cacheNames) =>
        Promise.all(
          cacheNames.map((cache) => {
            if (cache !== 'spa-cache-v1') {
              console.log('[Service Worker] Deleting old cache:', cache);
              return caches.delete(cache);
            }
          })
        )
      )
    );
  
    // Forzar que este service worker tome el control inmediatamente
    self.clients.claim();
  });
  
  self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push event recibido:', event);
  
    const data = event.data ? event.data.text() : 'Sin datos en el push';
    const options = {
      body: data,
      icon: '/logo192.png',
      badge: '/logo192.png'
    };
  
    event.waitUntil(
      self.registration.showNotification('Notificación Push', options)
    );
  });