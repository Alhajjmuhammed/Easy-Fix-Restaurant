// Force Service Worker Cleanup Script - ULTRA AGGRESSIVE VERSION
// Add this to all pages that shouldn't auto-reload

(function() {
    'use strict';
    
    console.log('�️ ULTRA AUTO-RELOAD PROTECTION ACTIVATED');
    
    // Unregister ALL service workers
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then(function(registrations) {
            if (registrations.length === 0) {
                console.log('✅ No service workers found');
                return;
            }
            
            for (let registration of registrations) {
                registration.unregister().then(function(success) {
                    if (success) {
                        console.log('✅ Service worker unregistered:', registration.scope);
                    } else {
                        console.log('❌ Failed to unregister service worker:', registration.scope);
                    }
                });
            }
            console.log(`🗑️ Unregistered ${registrations.length} service worker(s)`);
        }).catch(function(error) {
            console.error('❌ Error getting service workers:', error);
        });
    }
    
    // Clear all caches
    if ('caches' in window) {
        caches.keys().then(function(cacheNames) {
            if (cacheNames.length > 0) {
                console.log('🗑️ Clearing', cacheNames.length, 'cache(s)');
                return Promise.all(
                    cacheNames.map(function(cacheName) {
                        console.log('🗑️ Deleting cache:', cacheName);
                        return caches.delete(cacheName);
                    })
                );
            }
        }).then(function() {
            console.log('✅ All caches cleared');
        }).catch(function(error) {
            console.error('❌ Error clearing caches:', error);
        });
    }
    
    // AGGRESSIVE: Block ALL setInterval that might reload (except kitchen and bar pages)
    const originalSetInterval = window.setInterval;
    const originalSetTimeout = window.setTimeout;
    
    const isKitchenPage = window.location.pathname.includes('/kitchen/');
    const isBarPage = window.location.pathname.includes('/bar/');
    
    console.log('🔍 Page check - Path:', window.location.pathname);
    console.log('🔍 Is Kitchen Page:', isKitchenPage);
    console.log('🔍 Is Bar Page:', isBarPage);
    
    if (!isKitchenPage && !isBarPage) {
        console.log('🛡️ Auto-reload protection ENABLED for this page');
    } else {
        console.log('✅ Auto-reload protection DISABLED - Kitchen/Bar page detected');
    }
    
    if (!isKitchenPage && !isBarPage) {
        window.setInterval = function(callback, delay) {
            const callbackStr = callback.toString();
            // Block ANY setInterval with reload
            if (callbackStr.includes('reload') || callbackStr.includes('location')) {
                console.warn('🛡️ BLOCKED setInterval with reload attempt');
                return -1;
            }
            return originalSetInterval.apply(this, arguments);
        };
        
        window.setTimeout = function(callback, delay) {
            const callbackStr = callback.toString();
            // Block ANY setTimeout with reload
            if (callbackStr.includes('reload') && callbackStr.includes('location')) {
                console.warn('🛡️ BLOCKED setTimeout with reload attempt');
                return -1;
            }
            return originalSetTimeout.apply(this, arguments);
        };
        
        console.log('🛡️ setInterval/setTimeout reload protection enabled');
    }
    
    // Remove meta refresh tags
    var metaTags = document.querySelectorAll('meta[http-equiv="refresh"]');
    if (metaTags.length > 0) {
        metaTags.forEach(function(meta) {
            meta.remove();
            console.log('🛡️ Removed meta refresh tag');
        });
    }
    
    // Monitor for new meta refresh tags
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.tagName === 'META' && node.getAttribute('http-equiv') === 'refresh') {
                    console.warn('🛡️ BLOCKED: Attempted to add meta refresh tag');
                    node.remove();
                }
            });
        });
    });
    
    if (document.head) {
        observer.observe(document.head, {
            childList: true,
            subtree: true
        });
    }
    
    console.log('✅ ULTRA Auto-reload protection FULLY ACTIVE');
    console.log('ℹ️  Pages will ONLY reload when you manually press F5 or Ctrl+R');
})();
