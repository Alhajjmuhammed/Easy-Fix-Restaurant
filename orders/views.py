from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
import json
import uuid

from .models import Order, OrderItem
from .forms import TableSelectionForm, OrderForm, OrderStatusForm, CancelOrderForm
from restaurant.models import TableInfo, Product, MainCategory
from accounts.models import User

def select_table(request):
    """Customer selects table number before ordering"""
    if request.method == 'POST':
        form = TableSelectionForm(request.POST)
        if form.is_valid():
            table_number = form.cleaned_data['table_number']
            request.session['selected_table'] = table_number
            messages.success(request, f'Table {table_number} selected. You can now browse the menu.')
            return redirect('orders:browse_menu')
    else:
        form = TableSelectionForm()
    
    return render(request, 'orders/select_table.html', {'form': form})

def browse_menu(request):
    """Browse menu and add items to cart"""
    # Check if table is selected
    if 'selected_table' not in request.session:
        messages.warning(request, 'Please select your table number first.')
        return redirect('orders:select_table')
    
    table_number = request.session['selected_table']
    categories = MainCategory.objects.filter(is_active=True).prefetch_related(
        'subcategories__products'
    )
    
    # Get cart from session
    cart = request.session.get('cart', {})
    cart_count = sum(item['quantity'] for item in cart.values())
    cart_total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    
    context = {
        'categories': categories,
        'table_number': table_number,
        'cart': cart,
        'cart_count': cart_count,
        'cart_total': cart_total,
    }
    
    return render(request, 'orders/browse_menu.html', context)

@require_POST
def add_to_cart(request):
    """Add item to cart via AJAX"""
    if 'selected_table' not in request.session:
        return JsonResponse({'success': False, 'message': 'Please select a table first.'})
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id, is_available=True)
        
        # Check stock
        if product.available_in_stock < quantity:
            return JsonResponse({
                'success': False, 
                'message': f'Only {product.available_in_stock} items available in stock.'
            })
        
        # Get or create cart in session
        cart = request.session.get('cart', {})
        
        if str(product_id) in cart:
            # Update existing item
            new_quantity = cart[str(product_id)]['quantity'] + quantity
            if new_quantity > product.available_in_stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot add more. Only {product.available_in_stock} items available.'
                })
            cart[str(product_id)]['quantity'] = new_quantity
        else:
            # Add new item
            cart[str(product_id)] = {
                'name': product.name,
                'price': str(product.price),
                'quantity': quantity,
                'image': product.image.url if product.image else None,
            }
        
        request.session['cart'] = cart
        request.session.modified = True
        
        # Calculate cart totals
        cart_count = sum(item['quantity'] for item in cart.values())
        cart_total = sum(float(item['price']) * item['quantity'] for item in cart.values())
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart!',
            'cart_count': cart_count,
            'cart_total': cart_total,
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred.'})

@require_POST
def remove_from_cart(request):
    """Remove item from cart via AJAX"""
    try:
        data = json.loads(request.body)
        product_id = str(data.get('product_id'))
        
        cart = request.session.get('cart', {})
        
        if product_id in cart:
            del cart[product_id]
            request.session['cart'] = cart
            request.session.modified = True
            
            # Calculate cart totals
            cart_count = sum(item['quantity'] for item in cart.values())
            cart_total = sum(float(item['price']) * item['quantity'] for item in cart.values())
            
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart.',
                'cart_count': cart_count,
                'cart_total': cart_total,
            })
        
        return JsonResponse({'success': False, 'message': 'Item not found in cart.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred.'})

@require_POST
def update_cart_quantity(request):
    """Update item quantity in cart via AJAX"""
    try:
        data = json.loads(request.body)
        product_id = str(data.get('product_id'))
        quantity = int(data.get('quantity'))
        
        if quantity <= 0:
            return JsonResponse({'success': False, 'message': 'Quantity must be greater than 0.'})
        
        product = get_object_or_404(Product, id=product_id)
        
        if quantity > product.available_in_stock:
            return JsonResponse({
                'success': False,
                'message': f'Only {product.available_in_stock} items available.'
            })
        
        cart = request.session.get('cart', {})
        
        if product_id in cart:
            cart[product_id]['quantity'] = quantity
            request.session['cart'] = cart
            request.session.modified = True
            
            # Calculate cart totals
            cart_count = sum(item['quantity'] for item in cart.values())
            cart_total = sum(float(item['price']) * item['quantity'] for item in cart.values())
            item_total = float(cart[product_id]['price']) * quantity
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count,
                'cart_total': cart_total,
                'item_total': item_total,
            })
        
        return JsonResponse({'success': False, 'message': 'Item not found in cart.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred.'})

def view_cart(request):
    """View cart contents"""
    if 'selected_table' not in request.session:
        messages.warning(request, 'Please select your table number first.')
        return redirect('orders:select_table')
    
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.info(request, 'Your cart is empty.')
        return redirect('orders:browse_menu')
    
    # Calculate totals
    cart_items = []
    cart_total = 0
    
    for product_id, item in cart.items():
        item_total = float(item['price']) * item['quantity']
        cart_total += item_total
        cart_items.append({
            'product_id': product_id,
            'name': item['name'],
            'price': float(item['price']),
            'quantity': item['quantity'],
            'total': item_total,
            'image': item.get('image'),
        })
    
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'table_number': request.session['selected_table'],
    }
    
    return render(request, 'orders/view_cart.html', context)

@login_required
def place_order(request):
    """Place order from cart"""
    if 'selected_table' not in request.session:
        messages.warning(request, 'Please select your table number first.')
        return redirect('orders:select_table')
    
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('orders:browse_menu')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Get table
                    table = get_object_or_404(TableInfo, tbl_no=request.session['selected_table'])
                    
                    # Create order
                    order = Order.objects.create(
                        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
                        table_info=table,
                        ordered_by=request.user,
                        special_instructions=form.cleaned_data['special_instructions'],
                        status='pending'
                    )
                    
                    # Create order items
                    total_amount = 0
                    for product_id, item in cart.items():
                        product = get_object_or_404(Product, id=product_id)
                        
                        # Check stock again
                        if product.available_in_stock < item['quantity']:
                            raise Exception(f'Insufficient stock for {product.name}')
                        
                        # Create order item
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=item['quantity'],
                            unit_price=product.price
                        )
                        
                        # Update stock
                        product.available_in_stock -= item['quantity']
                        product.save()
                        
                        total_amount += float(item['price']) * item['quantity']
                    
                    # Update order total
                    order.total_amount = total_amount
                    order.save()
                    
                    # Clear cart and table selection
                    del request.session['cart']
                    del request.session['selected_table']
                    request.session.modified = True
                    
                    messages.success(request, f'Order {order.order_number} placed successfully!')
                    return redirect('orders:order_confirmation', order_id=order.id)
                    
            except Exception as e:
                messages.error(request, f'Error placing order: {str(e)}')
                return redirect('orders:view_cart')
    else:
        form = OrderForm()
    
    # Calculate cart total for display
    cart_total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    
    context = {
        'form': form,
        'cart': cart,
        'cart_total': cart_total,
        'table_number': request.session['selected_table'],
    }
    
    return render(request, 'orders/place_order.html', context)

@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, ordered_by=request.user)
    return render(request, 'orders/order_confirmation.html', {'order': order})

@login_required
def my_orders(request):
    """View customer's orders"""
    orders = Order.objects.filter(ordered_by=request.user).select_related(
        'table_info', 'confirmed_by'
    ).prefetch_related('order_items__product').order_by('-created_at')
    
    return render(request, 'orders/my_orders.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    """View order details"""
    order = get_object_or_404(Order, id=order_id, ordered_by=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})

def order_list(request):
    """Placeholder for order list - will be used by staff"""
    return render(request, 'orders/order_list.html')

def create_order(request):
    """Placeholder for create order - redirect to table selection"""
    return redirect('orders:select_table')

@login_required
def kitchen_dashboard(request):
    """Kitchen staff dashboard to manage orders"""
    if not request.user.is_kitchen_staff():
        messages.error(request, 'Access denied. Kitchen staff privileges required.')
        return redirect('restaurant:home')
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'pending')
    
    # Base queryset
    orders = Order.objects.select_related('table_info', 'ordered_by', 'confirmed_by').prefetch_related('order_items__product').order_by('-created_at')
    
    # Apply status filter
    if status_filter == 'active':
        orders = orders.filter(status__in=['pending', 'confirmed', 'preparing'])
    elif status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    # Get order counts for different statuses
    pending_count = Order.objects.filter(status='pending').count()
    confirmed_count = Order.objects.filter(status='confirmed').count()
    preparing_count = Order.objects.filter(status='preparing').count()
    ready_count = Order.objects.filter(status='ready').count()
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'preparing_count': preparing_count,
        'ready_count': ready_count,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'orders/kitchen_dashboard.html', context)

@login_required
@require_POST
def confirm_order(request, order_id):
    """Kitchen staff confirms a pending order"""
    if not request.user.is_kitchen_staff():
        return JsonResponse({'success': False, 'message': 'Access denied.'})
    
    try:
        order = get_object_or_404(Order, id=order_id, status='pending')
        
        order.status = 'confirmed'
        order.confirmed_by = request.user
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order {order.order_number} confirmed successfully!',
            'new_status': order.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred.'})

@login_required
@require_POST
def update_order_status(request, order_id):
    """Update order status"""
    if not request.user.is_kitchen_staff():
        return JsonResponse({'success': False, 'message': 'Access denied.'})
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['confirmed', 'preparing', 'ready', 'served']:
            return JsonResponse({'success': False, 'message': 'Invalid status.'})
        
        order = get_object_or_404(Order, id=order_id)
        
        # Validate status transitions
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['ready', 'cancelled'],
            'ready': ['served', 'cancelled'],
            'served': [],
            'cancelled': []
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            return JsonResponse({'success': False, 'message': 'Invalid status transition.'})
        
        order.status = new_status
        if new_status == 'confirmed' and not order.confirmed_by:
            order.confirmed_by = request.user
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order {order.order_number} updated to {order.get_status_display()}!',
            'new_status': order.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred.'})

@login_required
def cancel_order(request, order_id):
    """Cancel an order with reason"""
    if not request.user.is_kitchen_staff():
        messages.error(request, 'Access denied. Kitchen staff privileges required.')
        return redirect('orders:kitchen_dashboard')
    
    order = get_object_or_404(Order, id=order_id)
    
    if order.status in ['served', 'cancelled']:
        messages.error(request, 'Cannot cancel this order.')
        return redirect('orders:kitchen_dashboard')
    
    if request.method == 'POST':
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Restore product stock
                for item in order.order_items.all():
                    product = item.product
                    product.available_in_stock += item.quantity
                    product.save()
                
                # Update order
                order.status = 'cancelled'
                order.reason_if_cancelled = form.cleaned_data['reason']
                order.save()
                
                messages.success(request, f'Order {order.order_number} cancelled successfully.')
                return redirect('orders:kitchen_dashboard')
    else:
        form = CancelOrderForm()
    
    return render(request, 'orders/cancel_order.html', {'form': form, 'order': order})

@login_required
def kitchen_order_detail(request, order_id):
    """Detailed view of order for kitchen staff"""
    if not request.user.is_kitchen_staff():
        messages.error(request, 'Access denied. Kitchen staff privileges required.')
        return redirect('restaurant:home')
    
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/kitchen_order_detail.html', {'order': order})

@login_required
def customer_care_dashboard(request):
    """Customer care dashboard placeholder"""
    if not request.user.is_customer_care():
        messages.error(request, 'Access denied. Customer care privileges required.')
        return redirect('restaurant:home')
    
    return render(request, 'orders/customer_care_dashboard.html')
