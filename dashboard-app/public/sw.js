// Minimal service worker: caches NOTHING (case data is confidential); every request goes to the network as usual.
// No fetch listener: an empty one only adds a hop to every request; current Chrome/Edge install a PWA without it
// (manifest + registered service worker are enough).
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
