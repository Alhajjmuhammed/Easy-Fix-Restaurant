// Real-time WebSocket functionality for order tracking
class OrderTracker {
    constructor(orderId, userId = null, isRestaurant = false) {
        this.orderId = orderId;
        this.userId = userId;
        this.isRestaurant = isRestaurant;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000;
        this.init();
    }

    init() {
        this.connect();
        this.setupEventListeners();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        
        // Show connecting status
        this.showConnectionStatus('connecting');
        
        if (this.isRestaurant) {
            // Restaurant staff connects to restaurant channel
            const ownerId = this.getOwnerId(); // This should be passed from template
            this.socket = new WebSocket(`${protocol}//${host}/ws/restaurant/${ownerId}/`);
        } else {
            // Customer connects to order channel
            this.socket = new WebSocket(`${protocol}//${host}/ws/order/${this.orderId}/`);
        }

        this.socket.onopen = (event) => {
            console.log('WebSocket connection opened');
            this.reconnectAttempts = 0;
            this.showConnectionStatus('connected');
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket connection closed');
            this.showConnectionStatus('disconnected');
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showConnectionStatus('error');
        };
    }

    handleMessage(data) {
        if (data.type === 'order_status_update') {
            this.updateOrderStatus(data.message);
        } else if (data.type === 'new_order' && this.isRestaurant) {
            this.handleNewOrder(data.message);
        } else if (data.type === 'order_cancelled' && this.isRestaurant) {
            this.handleOrderCancellation(data.message);
        }
    }

    updateOrderStatus(message) {
        // Update status badge
        const statusBadge = document.querySelector(`[data-order-id="${message.order_id}"] .order-status`);
        if (statusBadge) {
            statusBadge.textContent = message.status_display;
            statusBadge.className = `order-status badge ${this.getStatusClass(message.status)}`;
        }

        // Update status text
        const statusText = document.querySelector(`[data-order-id="${message.order_id}"] .status-text`);
        if (statusText) {
            statusText.textContent = message.status_display;
        }

        // Show notification
        this.showNotification({
            type: 'status_update',
            title: `Order ${message.order_number} Updated`,
            message: `Status changed to: ${message.status_display}`,
            timestamp: message.timestamp
        });

        // Update progress bar if exists
        this.updateProgressBar(message.order_id, message.status);

        // Play notification sound
        this.playNotificationSound();
    }

    handleNewOrder(message) {
        if (!this.isRestaurant) return;

        // Add new order to the list
        this.addOrderToList(message);

        // Show notification
        this.showNotification({
            type: 'new_order',
            title: 'New Order Received',
            message: `Order ${message.order_number} from ${message.customer}`,
            timestamp: message.timestamp
        });

        // Play notification sound
        this.playNotificationSound();
    }

    handleOrderCancellation(message) {
        if (!this.isRestaurant) return;

        // Update order in the list
        const orderElement = document.querySelector(`[data-order-id="${message.order_id}"]`);
        if (orderElement) {
            orderElement.classList.add('cancelled');
        }

        // Show notification
        this.showNotification({
            type: 'order_cancelled',
            title: 'Order Cancelled',
            message: `Order ${message.order_number} was cancelled`,
            timestamp: message.timestamp
        });
    }

    getStatusClass(status) {
        const statusClasses = {
            'pending': 'bg-warning',
            'confirmed': 'bg-info',
            'preparing': 'bg-primary',
            'ready': 'bg-success',
            'served': 'bg-secondary',
            'cancelled': 'bg-danger'
        };
        return statusClasses[status] || 'bg-secondary';
    }

    updateProgressBar(orderId, status) {
        const progressBar = document.querySelector(`[data-order-id="${orderId}"] .progress-bar`);
        if (!progressBar) return;

        const statusProgress = {
            'pending': 20,
            'confirmed': 40,
            'preparing': 60,
            'ready': 80,
            'served': 100,
            'cancelled': 0
        };

        const progress = statusProgress[status] || 0;
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }

    addOrderToList(orderData) {
        // This would create a new order element in the restaurant dashboard
        const ordersContainer = document.querySelector('.orders-container');
        if (!ordersContainer) return;

        const orderElement = this.createOrderElement(orderData);
        ordersContainer.insertBefore(orderElement, ordersContainer.firstChild);
    }

    createOrderElement(orderData) {
        // Create order card HTML element
        const orderCard = document.createElement('div');
        orderCard.className = 'card order-card mb-3';
        orderCard.setAttribute('data-order-id', orderData.order_id);
        
        orderCard.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Order #${orderData.order_number}</h6>
                <span class="order-status badge ${this.getStatusClass(orderData.status)}">${orderData.status_display}</span>
            </div>
            <div class="card-body">
                <p><strong>Customer:</strong> ${orderData.customer}</p>
                <p><strong>Total:</strong> $${orderData.total_amount}</p>
                <p><strong>Time:</strong> ${new Date(orderData.timestamp).toLocaleString()}</p>
            </div>
        `;
        
        return orderCard;
    }

    showNotification(notification) {
        // Create toast notification
        const toastContainer = document.querySelector('.toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center border-0';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        const bgClass = notification.type === 'new_order' ? 'bg-success' : 
                       notification.type === 'order_cancelled' ? 'bg-danger' : 'bg-info';
        
        toast.classList.add(bgClass, 'text-white');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${notification.title}</strong><br>
                    ${notification.message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Initialize and show toast
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 5000 });
            bsToast.show();
            
            // Remove toast after it's hidden
            toast.addEventListener('hidden.bs.toast', () => {
                toast.remove();
            });
        } else {
            // Fallback if Bootstrap is not available
            setTimeout(() => {
                toast.remove();
            }, 5000);
        }
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }

    playNotificationSound() {
        // Play notification sound if available
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(e => console.log('Could not play notification sound:', e));
        } catch (e) {
            console.log('Notification sound not available:', e);
        }
    }

    showConnectionStatus(status) {
        const statusIndicator = document.querySelector('.connection-status');
        if (statusIndicator) {
            // Show the indicator when there's an active connection attempt
            statusIndicator.style.display = 'block';
            
            // Update text and class based on status
            const statusText = {
                'connecting': 'Connecting...',
                'connected': 'Connected',
                'disconnected': 'Disconnected',
                'error': 'Connection Error',
                'failed': 'Connection Failed'
            };
            
            statusIndicator.textContent = statusText[status] || status;
            statusIndicator.className = `connection-status ${status}`;
            
            // Hide the indicator for successful connections after a delay
            if (status === 'connected') {
                setTimeout(() => {
                    statusIndicator.style.display = 'none';
                }, 3000);
            }
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);
        } else {
            console.log('Max reconnection attempts reached');
            this.showConnectionStatus('failed');
        }
    }

    getOwnerId() {
        // This should be passed from the Django template
        const ownerElement = document.querySelector('[data-owner-id]');
        return ownerElement ? ownerElement.getAttribute('data-owner-id') : 'default';
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Utility function to initialize order tracking
function initializeOrderTracking(orderId, userId = null, isRestaurant = false) {
    return new OrderTracker(orderId, userId, isRestaurant);
}

// Auto-initialize if order data is available
document.addEventListener('DOMContentLoaded', function() {
    const orderElement = document.querySelector('[data-order-id]');
    const restaurantElement = document.querySelector('[data-restaurant-view]');
    
    if (orderElement && !restaurantElement) {
        // Customer view - track specific order
        const orderId = orderElement.getAttribute('data-order-id');
        const userId = orderElement.getAttribute('data-user-id');
        window.orderTracker = new OrderTracker(orderId, userId, false);
    } else if (restaurantElement) {
        // Restaurant view - track all orders
        const ownerId = restaurantElement.getAttribute('data-owner-id');
        window.orderTracker = new OrderTracker(null, null, true);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.orderTracker) {
        window.orderTracker.disconnect();
    }
});