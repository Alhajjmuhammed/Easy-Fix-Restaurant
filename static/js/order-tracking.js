// Kitchen Dashboard - Order Tracking (WebSocket disabled for production)
console.log('Kitchen order tracking initialized');

document.addEventListener('DOMContentLoaded', function() {
    // Only auto-refresh on kitchen dashboard, not other pages
    const isKitchenDashboard = window.location.pathname.includes('/kitchen/') || 
                              document.querySelector('[data-kitchen-dashboard]');
    
    if (isKitchenDashboard) {
        // Auto-refresh every 2 minutes (120 seconds) for kitchen dashboard only
        setInterval(function() {
            window.location.reload();
        }, 120000);
        console.log('Auto-refresh enabled for kitchen dashboard (every 2 minutes)');
    }
    
    // Handle status update buttons
    const confirmButtons = document.querySelectorAll('[data-action="confirm"]');
    const cancelButtons = document.querySelectorAll('[data-action="cancel"]');
    
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            console.log('Order confirmed');
        });
    });
    
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            console.log('Order cancelled');
        });
    });
});
