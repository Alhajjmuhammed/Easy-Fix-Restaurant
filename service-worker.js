// Restaurant Ordering System - Service Worker
// Version 1.0.0 - Development Mode Disabled

// Check if we're in development mode
const isDevelopment = self.location.hostname === 'localhost' || 
                     self.location.hostname === '127.0.0.1' ||
                     self.location.port !== '';

console.log('Service Worker: Development mode:', isDevelopment);

// If in development, immediately unregister and skip all caching
if (isDevelopment) {
    console.log('🚫 Service Worker: Development mode - Skipping all caching and unregistering');
    
    // Unregister this service worker immediately
    self.addEventListener('install', event => {
        console.log('🚫 Service Worker: Development - Skipping installation');
        self.skipWaiting();
    });
    
    self.addEventListener('activate', event => {
        console.log('🚫 Service Worker: Development - Unregistering self');
        event.waitUntil(
            self.registration.unregister().then(() => {
                console.log('✅ Service Worker: Successfully unregistered in development mode');
                return self.clients.claim();
            })
        );
    });
    
    // Don't cache anything in development
    self.addEventListener('fetch', event => {
        // Just let all requests go through normally without caching
        return;
    });
    
} else {
    // PRODUCTION MODE - Normal service worker behavior
    console.log('✅ Service Worker: Production mode - Normal operation');

const CACHE_NAME = 'restaurant-ordering-v1.0.0';
const urlsToCache = [
    // Only cache essential static assets in development
    '/static/images/icon-192x192.png',
    '/static/images/icon-512x512.png',
    // Bootstrap and external resources
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Install event - cache resources
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching files');
                return cache.addAll(urlsToCache.map(url => {
                    return new Request(url, {
                        credentials: 'same-origin'
                    });
                })).catch(error => {
                    console.error('Service Worker: Failed to cache some resources', error);
                    // Continue even if some resources fail to cache
                });
            })
            .then(() => {
                console.log('Service Worker: Installation complete');
                return self.skipWaiting(); // Force activation
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('Service Worker: Activation complete');
            return self.clients.claim(); // Take control immediately
        })
    );
});

// Fetch event - serve cached content when offline  
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Skip WebSocket requests
    if (event.request.url.startsWith('ws://') || event.request.url.startsWith('wss://')) {
        return;
    }

    // DEVELOPMENT MODE: Skip caching HTML pages to allow live updates
    if (event.request.url.includes('localhost') || event.request.url.includes('127.0.0.1')) {
        if (event.request.destination === 'document' || 
            event.request.url.includes('/cashier/') ||
            event.request.url.includes('/accounts/') ||
            event.request.url.includes('.html')) {
            console.log('Service Worker: Development mode - fetching fresh content');
            return; // Let browser handle normally
        }
    }

    // Skip requests with query parameters that suggest dynamic content
    const url = new URL(event.request.url);
    if (url.search && (url.search.includes('_') || url.search.includes('timestamp'))) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then(response => {
            // Return cached version or fetch from network
            if (response) {
                console.log('Service Worker: Serving from cache', event.request.url);
                return response;
            }

            console.log('Service Worker: Fetching from network', event.request.url);
            return fetch(event.request).then(response => {
                // Don't cache if not a valid response
                if (!response || response.status !== 200 || response.type !== 'basic') {
                    return response;
                }

                // Clone the response
                const responseToCache = response.clone();

                // Cache the response for future use (only external resources in dev mode)
                if (!event.request.url.includes('localhost') && !event.request.url.includes('127.0.0.1')) {
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseToCache);
                    });
                }

                return response;
            }).catch(error => {
                console.log('Service Worker: Network request failed', error);
                
                // Return offline page for navigation requests
                if (event.request.destination === 'document') {
                    return caches.match('/offline/') || 
                           new Response('Offline - Please check your connection', {
                               status: 503,
                               statusText: 'Service Unavailable',
                               headers: new Headers({
                                   'Content-Type': 'text/html'
                               })
                           });
                }
                
                // Return a generic offline response for other requests
                return new Response('Offline', {
                    status: 503,
                    statusText: 'Service Unavailable'
                });
            });
        })
    );
});

// Background sync for order placement
self.addEventListener('sync', event => {
    if (event.tag === 'background-order-sync') {
        console.log('Service Worker: Background sync for orders');
        event.waitUntil(syncOrders());
    }
});

async function syncOrders() {
    try {
        // Get pending orders from IndexedDB
        const pendingOrders = await getPendingOrders();
        
        for (const order of pendingOrders) {
            try {
                const response = await fetch('/orders/place/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': order.csrfToken
                    },
                    body: JSON.stringify(order.data),
                    credentials: 'same-origin'
                });

                if (response.ok) {
                    // Remove from pending orders
                    await removePendingOrder(order.id);
                    console.log('Service Worker: Order synced successfully');
                } else {
                    console.error('Service Worker: Failed to sync order', response.status);
                }
            } catch (error) {
                console.error('Service Worker: Error syncing order', error);
            }
        }
    } catch (error) {
        console.error('Service Worker: Error in background sync', error);
    }
}

// Push notification handling
self.addEventListener('push', event => {
    console.log('Service Worker: Push notification received');
    
    let data = {};
    if (event.data) {
        data = event.data.json();
    }

    const options = {
        body: data.body || 'Your order status has been updated',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/icon-192x192.png',
        data: data.url || '/',
        actions: [
            {
                action: 'view',
                title: 'View Order'
            },
            {
                action: 'close',
                title: 'Close'
            }
        ],
        tag: data.tag || 'order-update',
        renotify: true,
        requireInteraction: false,
        vibrate: [200, 100, 200]
    };

    event.waitUntil(
        self.registration.showNotification(
            data.title || 'Order Update',
            options
        )
    );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow(event.notification.data)
        );
    } else if (event.action === 'close') {
        // Just close the notification
        return;
    } else {
        // Default action - open the app
        event.waitUntil(
            clients.matchAll().then(clientList => {
                if (clientList.length > 0) {
                    return clientList[0].focus();
                }
                return clients.openWindow('/');
            })
        );
    }
});

// Message handling from main thread
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (event.data && event.data.type === 'CACHE_ORDER') {
        // Cache order for background sync
        cacheOrderForSync(event.data.order);
    }
});

// Helper functions for IndexedDB operations
async function getPendingOrders() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('restaurant-orders', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['pending-orders'], 'readonly');
            const store = transaction.objectStore('pending-orders');
            const getRequest = store.getAll();
            
            getRequest.onsuccess = () => resolve(getRequest.result || []);
            getRequest.onerror = () => reject(getRequest.error);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('pending-orders')) {
                db.createObjectStore('pending-orders', { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

async function removePendingOrder(id) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('restaurant-orders', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['pending-orders'], 'readwrite');
            const store = transaction.objectStore('pending-orders');
            const deleteRequest = store.delete(id);
            
            deleteRequest.onsuccess = () => resolve();
            deleteRequest.onerror = () => reject(deleteRequest.error);
        };
    });
}

async function cacheOrderForSync(order) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('restaurant-orders', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['pending-orders'], 'readwrite');
            const store = transaction.objectStore('pending-orders');
            const addRequest = store.add(order);
            
            addRequest.onsuccess = () => resolve();
            addRequest.onerror = () => reject(addRequest.error);
        };
    });
}

console.log('Service Worker: Loaded');

} // End of production mode block