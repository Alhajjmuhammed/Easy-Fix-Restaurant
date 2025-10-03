// Development Cache Cleaner - Disables all PWA caching for development// Development Cache Cleaner - Disables all PWA caching for development

// This file prevents service worker and cache issues during development// This script runs instead of PWA manager during development



(function() {(function() {

    'use strict';    'use strict';

        

    console.log('🔧 Development Mode: Cache Cleaner Active');    console.log('🔧 Development Mode: Cache Cleaner Active');

        

    // Check if we're in development mode    // Check if we're in development

    const isDevelopment = window.location.hostname === 'localhost' ||     const isDevelopment = window.location.hostname === 'localhost' || 

                         window.location.hostname === '127.0.0.1' ||                          window.location.hostname === '127.0.0.1' ||

                         window.location.hostname === '';                         window.location.port !== '';

        

    if (!isDevelopment) {    if (!isDevelopment) {

        console.log('Production mode detected - Cache cleaner disabled');        console.log('Production mode detected - Cache cleaner disabled');

        return;        return;

    }    }

        

    // Clear all service workers and caches immediately    // Clear all service workers and caches immediately

    async function clearAllCaches() {    async function clearAllPWAData() {

        try {        try {

            // 1. Unregister all service workers            // 1. Unregister all service workers

            if ('serviceWorker' in navigator) {            if ('serviceWorker' in navigator) {

                const registrations = await navigator.serviceWorker.getRegistrations();                const registrations = await navigator.serviceWorker.getRegistrations();

                console.log('🗑️ Unregistering', registrations.length, 'service workers');                console.log('🗑️ Found', registrations.length, 'service worker registrations');

                                

                for (const registration of registrations) {                for (const registration of registrations) {

                    console.log('🗑️ Unregistering SW:', registration.scope);                    console.log('🗑️ Unregistering:', registration.scope);

                    await registration.unregister();                    await registration.unregister();

                }                }

            }            }

                        

            // 2. Clear all caches            // 2. Clear all caches

            if ('caches' in window) {            if ('caches' in window) {

                const cacheNames = await caches.keys();                const cacheNames = await caches.keys();

                console.log('🗑️ Clearing', cacheNames.length, 'caches');                console.log('🗑️ Clearing', cacheNames.length, 'caches');

                                

                for (const cacheName of cacheNames) {                for (const cacheName of cacheNames) {

                    console.log('🗑️ Deleting cache:', cacheName);                    console.log('🗑️ Deleting cache:', cacheName);

                    await caches.delete(cacheName);                    await caches.delete(cacheName);

                }                }

            }            }

                        

            console.log('✅ Development cache cleaner: All caches cleared');            // 3. Clear localStorage PWA data

                        if ('localStorage' in window) {

        } catch (error) {                localStorage.removeItem('pwa-installed');

            console.warn('⚠️ Cache clearing error:', error);                localStorage.removeItem('pwa-version');

        }            }

    }            

                // 4. Clear sessionStorage

    // Run immediately            if ('sessionStorage' in window) {

    clearAllCaches();                sessionStorage.clear();

                }

    // Override caches API to prevent any caching during development            

    if ('caches' in window) {            console.log('✅ Development Mode: All PWA data cleared');

        const originalOpen = caches.open;            

        caches.open = function() {        } catch (error) {

            console.log('🚫 Cache.open() blocked in development mode');            console.error('❌ Error clearing PWA data:', error);

            return Promise.resolve({        }

                match: () => Promise.resolve(undefined),    }

                add: () => Promise.resolve(),    

                addAll: () => Promise.resolve(),    function showDevNotification() {

                put: () => Promise.resolve(),        const notification = document.createElement('div');

                delete: () => Promise.resolve(true),        notification.innerHTML = `

                keys: () => Promise.resolve([])            <div style="position: fixed; top: 10px; right: 10px; z-index: 10000; 

            });                        background: #dc3545; color: white; padding: 15px; border-radius: 8px;

        };                        font-family: Arial, sans-serif; font-size: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">

    }                <strong>🚫 PWA DISABLED</strong><br>

                    Development Mode Active<br>

    // Block service worker registration in development                <small>No caching - Changes appear immediately</small>

    if ('serviceWorker' in navigator) {            </div>

        const originalRegister = navigator.serviceWorker.register;        `;

        navigator.serviceWorker.register = function() {        document.body.appendChild(notification);

            console.log('🚫 Service Worker registration blocked in development mode');        

            return Promise.reject(new Error('Service Worker blocked in development'));        // Remove notification after 5 seconds

        };        setTimeout(() => {

    }            if (notification.parentNode) {

                    notification.parentNode.removeChild(notification);

    // Disable application cache if present            }

    if ('applicationCache' in window) {        }, 5000);

        window.applicationCache.addEventListener('checking', function() {    }

            console.log('🚫 Application Cache blocked in development mode');    

        });    // Run immediately when script loads

    }    clearAllPWAData();

        

    // Add visual indicator for development mode    // Also run when page becomes visible (tab switching)

    const indicator = document.createElement('div');    document.addEventListener('visibilitychange', function() {

    indicator.innerHTML = '🔧 DEV MODE';        if (!document.hidden) {

    indicator.style.cssText = `            clearAllPWAData();

        position: fixed;        }

        top: 10px;    });

        right: 10px;    

        background: #ff4444;    // Prevent any new service worker registration

        color: white;    if ('serviceWorker' in navigator) {

        padding: 5px 10px;        // Override the register method to prevent new registrations

        border-radius: 3px;        const originalRegister = navigator.serviceWorker.register;

        font-family: monospace;        navigator.serviceWorker.register = function() {

        font-size: 12px;            console.log('🚫 Service Worker registration blocked in development mode');

        z-index: 9999;            return Promise.reject(new Error('Service Worker registration disabled for development'));

        opacity: 0.8;        };

    `;    }

        

    // Add indicator when DOM is ready    console.log('🔧 Development Cache Cleaner initialized');

    if (document.readyState === 'loading') {})();
        document.addEventListener('DOMContentLoaded', () => {
            document.body.appendChild(indicator);
        });
    } else {
        document.body.appendChild(indicator);
    }
    
    console.log('🔧 Development Cache Cleaner initialized');
})();