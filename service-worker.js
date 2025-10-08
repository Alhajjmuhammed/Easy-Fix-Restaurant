// Restaurant Ordering System - Service Worker
// Version 1.0.1 - COMPLETELY DISABLED
// Service worker disabled to prevent auto-reload issues

console.log('🚫 Service Worker: DISABLED - No caching, no reloading');

// Immediately unregister and skip all functionality
self.addEventListener('install', event => {
    console.log('🚫 Service Worker: Installation skipped (disabled)');
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    console.log('🚫 Service Worker: Activation skipped (disabled)');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            // Delete ALL caches
            return Promise.all(
                cacheNames.map(cacheName => {
                    console.log('🗑️ Deleting cache:', cacheName);
                    return caches.delete(cacheName);
                })
            );
        }).then(() => {
            console.log('✅ All caches cleared');
            return self.clients.claim();
        })
    );
});

// Don't intercept any fetches - let browser handle everything normally
self.addEventListener('fetch', event => {
    // Just pass through - no caching at all
    return;
});

console.log('✅ Service Worker: Loaded in disabled mode - no auto-reload');

// No additional functionality needed - service worker is completely disabled