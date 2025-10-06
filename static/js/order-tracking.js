// Kitchen Dashboard - Order Tracking (WebSocket disabled for production)
console.log('Kitchen order tracking initialized');

document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh every 30 seconds to get new orders
    setInterval(function() {
        window.location.reload();
    }, 30000);
    
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
