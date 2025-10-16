from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from decimal import Decimal
import json
import uuid

from .models import Order, OrderItem, BillRequest
from .forms import TableSelectionForm, OrderForm, OrderStatusForm, CancelOrderForm
from restaurant.models import TableInfo, Product, MainCategory
from accounts.models import User, get_owner_filter, check_owner_permission

# Initialize channel layer for WebSocket communication
channel_layer = get_channel_layer()

def select_table(request):
    """Customer selects table from available tables in restaurant"""
    restaurant = None
    
    # For customer care users, use their assigned restaurant
    if request.user.is_authenticated and request.user.is_customer_care() and request.user.owner:
        restaurant = request.user.owner
        # Set session data for consistency with QR code flow
        request.session['selected_restaurant_id'] = restaurant.id
        request.session['selected_restaurant_name'] = restaurant.restaurant_name
    else:
        # Check if restaurant is selected via QR code or session
        selected_restaurant_id = request.session.get('selected_restaurant_id')
        
        if selected_restaurant_id:
            try:
                restaurant = User.objects.get(id=selected_restaurant_id, role__name='owner')
            except User.DoesNotExist:
                messages.error(request, 'Selected restaurant not found.')
                return redirect('accounts:login')
        else:
            # SECURITY CHECK: Customer must access via QR code or restaurant link
            # Prevent direct access to table selection without scanning QR code
            if request.user.is_authenticated and request.user.is_customer():
                messages.error(request, 'Unauthorized access. Please scan the restaurant QR code to order.')
                return redirect('accounts:login')
            # For non-customer users (staff, admin), allow access
            elif not request.user.is_authenticated:
                messages.warning(request, 'Please scan a restaurant QR code to start ordering.')
                return redirect('accounts:login')
    
    if request.method == 'POST':
        # Handle table selection from visual interface
        selected_table_id = request.POST.get('table_id')
        if selected_table_id:
            try:
                # Get the table by ID and verify it belongs to the restaurant
                if restaurant:
                    table = TableInfo.objects.get(id=selected_table_id, owner=restaurant)
                else:
                    owner_filter = get_owner_filter(request.user)
                    table = TableInfo.objects.get(id=selected_table_id, owner=owner_filter)
                
                if table.is_truly_available():
                    request.session['selected_table'] = table.tbl_no
                    request.session['selected_table_id'] = table.id
                    # Store the restaurant owner for this session
                    if restaurant:
                        request.session['selected_restaurant_owner'] = restaurant.id
                    messages.success(request, f'Table {table.tbl_no} selected. You can now browse the menu.')
                    return redirect('restaurant:menu')
                else:
                    occupying_order = table.get_occupying_order()
                    if occupying_order:
                        messages.error(request, f'Table {table.tbl_no} is currently occupied by Order #{occupying_order.order_number}.')
                    else:
                        messages.error(request, f'Table {table.tbl_no} is currently not available.')
            except TableInfo.DoesNotExist:
                messages.error(request, 'Invalid table selection. Please try again.')
    
    # Get all available tables for the restaurant
    available_tables = []
    if restaurant:
        available_tables = TableInfo.objects.filter(owner=restaurant).order_by('tbl_no')
    elif request.user.is_authenticated:
        owner_filter = get_owner_filter(request.user)
        if owner_filter:
            available_tables = TableInfo.objects.filter(owner=owner_filter).order_by('tbl_no')
    
    context = {
        'available_tables': available_tables,
        'restaurant': restaurant,
        'restaurant_name': request.session.get('selected_restaurant_name', 'Restaurant')
    }
    return render(request, 'orders/select_table.html', context)

def browse_menu(request):
    """Browse menu and add items to cart"""
    # Check if table is selected
    if 'selected_table' not in request.session:
        messages.warning(request, 'Please select your table number first.')
        return redirect('orders:select_table')
    
    table_number = request.session['selected_table']
    
    # Filter categories by user's owner
    try:
        owner_filter = get_owner_filter(request.user)
        if owner_filter:
            categories = MainCategory.objects.filter(
                is_active=True, 
                owner=owner_filter
            ).prefetch_related('subcategories__products').order_by('name')
        else:
            # Administrator can see all categories
            categories = MainCategory.objects.filter(is_active=True).prefetch_related(
                'subcategories__products'
            ).order_by('name')
    except PermissionDenied:
        messages.error(request, 'You are not associated with any restaurant.')
        return redirect('restaurant:home')
    
    # Get cart from session - handle empty cart safely
    cart = request.session.get('cart', {})
    cart_count = 0
    cart_total = 0
    
    if cart:
        try:
            cart_count = sum(item.get('quantity', 0) for item in cart.values() if isinstance(item, dict))
            cart_total = sum(
                float(item.get('price', 0)) * item.get('quantity', 0) 
                for item in cart.values() 
                if isinstance(item, dict)
            )
        except (ValueError, TypeError):
            # Reset cart if there's corrupted data
            cart = {}
            request.session['cart'] = cart
            cart_count = 0
            cart_total = 0
    
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
            # Update existing item with current promotional pricing
            new_quantity = cart[str(product_id)]['quantity'] + quantity
            if new_quantity > product.available_in_stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot add more. Only {product.available_in_stock} items available.'
                })
            
            # Update quantity and recalculate promotional pricing
            current_price = product.get_current_price()
            cart[str(product_id)].update({
                'quantity': new_quantity,
                'price': str(current_price),
                'original_price': str(product.price),
                'has_promotion': product.has_active_promotion(),
            })
        else:
            # Add new item with promotional pricing
            current_price = product.get_current_price()
            cart[str(product_id)] = {
                'name': product.name,
                'price': str(current_price),
                'original_price': str(product.price),
                'has_promotion': product.has_active_promotion(),
                'quantity': quantity,
                'image': product.get_image().url if product.get_image() else None,
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
            # Update quantity and recalculate promotional pricing
            current_price = product.get_current_price()
            cart[product_id].update({
                'quantity': quantity,
                'price': str(current_price),
                'original_price': str(product.price),
                'has_promotion': product.has_active_promotion(),
            })
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
        return redirect('restaurant:menu')  # Redirect to restaurant menu instead
    
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
    
    # Get restaurant owner's tax rate
    try:
        selected_restaurant_id = request.session.get('selected_restaurant_id')
        if selected_restaurant_id:
            restaurant_owner = User.objects.get(id=selected_restaurant_id, role__name='owner')
            tax_rate = float(restaurant_owner.tax_rate)  # Convert decimal to float
        else:
            # Use default tax rate from User model default
            tax_rate = float(Decimal('0.0800'))  # Use same default as model
    except (User.DoesNotExist, TypeError):
        # Use default tax rate from User model default
        tax_rate = float(Decimal('0.0800'))  # Use same default as model
    
    # Calculate tax and final total
    tax_amount = cart_total * tax_rate
    final_total = cart_total + tax_amount
    
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'tax_amount': tax_amount,
        'tax_rate': tax_rate,
        'tax_percentage': int(tax_rate * 100),  # For display purposes
        'final_total': final_total,
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
                    # Get current restaurant - for customer care users, use their assigned restaurant
                    current_restaurant = None
                    
                    if request.user.is_customer_care() and request.user.owner:
                        # Customer care users use their assigned restaurant
                        current_restaurant = request.user.owner
                    else:
                        # Regular customers use QR code session
                        selected_restaurant_id = request.session.get('selected_restaurant_id')
                        if not selected_restaurant_id:
                            messages.error(request, 'Restaurant context not found. Please scan QR code again.')
                            return redirect('orders:select_table')
                        
                        try:
                            current_restaurant = User.objects.get(id=selected_restaurant_id, role__name='owner')
                        except User.DoesNotExist:
                            messages.error(request, 'Selected restaurant not found.')
                            return redirect('orders:select_table')
                    
                    # Get table for the specific restaurant
                    try:
                        table = TableInfo.objects.get(
                            tbl_no=request.session['selected_table'],
                            owner=current_restaurant
                        )
                    except TableInfo.DoesNotExist:
                        messages.error(request, f'Table {request.session["selected_table"]} not found in {current_restaurant.restaurant_name}.')
                        return redirect('orders:select_table')
                    except TableInfo.MultipleObjectsReturned:
                        # This shouldn't happen now, but just in case
                        table = TableInfo.objects.filter(
                            tbl_no=request.session['selected_table'],
                            owner=current_restaurant
                        ).first()
                    
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
                    
                    # Send real-time notification to restaurant staff
                    restaurant_id = current_restaurant.id
                    async_to_sync(channel_layer.group_send)(
                        f'restaurant_{restaurant_id}',
                        {
                            'type': 'new_order',
                            'order_id': str(order.id),
                            'order_number': order.order_number,
                            'table_number': str(table.tbl_no),
                            'customer_name': request.user.get_full_name() or request.user.username,
                            'items_count': len(cart),
                            'total_amount': str(total_amount),
                            'message': f'New order #{order.order_number} from Table {table.tbl_no}',
                            'timestamp': order.created_at.isoformat()
                        }
                    )
                    
                    # Send real-time update to order tracking
                    async_to_sync(channel_layer.group_send)(
                        f'order_{order.id}',
                        {
                            'type': 'order_status_update',
                            'order_id': str(order.id),
                            'status': order.status,
                            'status_display': order.get_status_display(),
                            'message': 'Order placed successfully! Kitchen will start preparing your order soon.',
                            'updated_by': request.user.get_full_name() or request.user.username,
                            'timestamp': order.created_at.isoformat()
                        }
                    )
                    
                    # Clear cart and table selection
                    del request.session['cart']
                    del request.session['selected_table']
                    request.session.modified = True
                    
                    # Store order ID in session for KOT auto-print
                    request.session['new_order_id'] = order.id
                    request.session['print_kot'] = True
                    
                    messages.success(request, f'Order {order.order_number} placed successfully!')
                    return redirect('orders:order_confirmation', order_id=order.id)
                    
            except Exception as e:
                messages.error(request, f'Error placing order: {str(e)}')
                return redirect('orders:view_cart')
    else:
        form = OrderForm()
    
    # Calculate cart total for display
    cart_total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    
    # Get restaurant owner's tax rate
    try:
        selected_restaurant_id = request.session.get('selected_restaurant_id')
        if selected_restaurant_id:
            restaurant_owner = User.objects.get(id=selected_restaurant_id, role__name='owner')
            tax_rate = float(restaurant_owner.tax_rate)  # Convert decimal to float
        else:
            # Use default tax rate from User model default
            tax_rate = float(Decimal('0.0800'))  # Use same default as model
    except (User.DoesNotExist, TypeError):
        # Use default tax rate from User model default
        tax_rate = float(Decimal('0.0800'))  # Use same default as model
    
    # Calculate tax and final total
    tax_amount = cart_total * tax_rate
    final_total = cart_total + tax_amount
    
    context = {
        'form': form,
        'cart': cart,
        'cart_total': cart_total,
        'tax_amount': tax_amount,
        'tax_rate': tax_rate,
        'tax_percentage': int(tax_rate * 100),  # For display purposes
        'final_total': final_total,
        'table_number': request.session['selected_table'],
    }
    
    return render(request, 'orders/place_order.html', context)

@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, ordered_by=request.user)
    
    # Check if we should auto-print KOT
    should_print_kot = request.session.pop('print_kot', False)
    new_order_id = request.session.pop('new_order_id', None)
    
    context = {
        'order': order,
        'should_print_kot': should_print_kot and new_order_id == order.id,
    }
    
    return render(request, 'orders/order_confirmation.html', context)

@login_required
def my_orders(request):
    """View user's orders - customers see restaurant-specific, customer care sees all their orders"""
    # Get current restaurant from session
    selected_restaurant_id = request.session.get('selected_restaurant_id')
    restaurant = None
    
    if selected_restaurant_id:
        try:
            restaurant = User.objects.get(id=selected_restaurant_id, role__name='owner')
        except User.DoesNotExist:
            restaurant = None
    
    # Filter orders by user type
    orders_query = Order.objects.filter(ordered_by=request.user)
    
    if request.user.is_customer() and restaurant:
        # For universal customers, only show orders from current restaurant
        orders_query = orders_query.filter(
            table_info__owner=restaurant
        )
    elif request.user.is_customer() and request.user.owner:
        # For legacy customers tied to specific restaurant
        orders_query = orders_query.filter(
            table_info__owner=request.user.owner
        )
    elif request.user.is_customer_care():
        # For customer care users, show only their orders from their assigned restaurant
        try:
            owner_filter = get_owner_filter(request.user)
            if owner_filter:
                orders_query = orders_query.filter(table_info__owner=owner_filter)
            # If no restaurant assignment, show all their orders
        except PermissionDenied:
            # If no restaurant access, show all their orders
            pass
    
    orders = orders_query.select_related(
        'table_info', 'table_info__owner', 'confirmed_by'
    ).prefetch_related('order_items__product').order_by('-created_at')
    
    context = {
        'orders': orders,
        'restaurant_name': request.session.get('selected_restaurant_name', 'Restaurant'),
        'current_restaurant': restaurant,
        'is_customer_care': request.user.is_customer_care()
    }
    
    return render(request, 'orders/my_orders.html', context)

@login_required
def order_detail(request, order_id):
    """View order details with tracking information"""
    # Allow Customer Care, Owner, and Kitchen Staff to view any order from their restaurant
    if request.user.is_customer_care() or request.user.is_owner() or request.user.is_kitchen_staff():
        owner = get_owner_filter(request.user)
        order = get_object_or_404(Order, id=order_id, table_info__owner=owner)
    else:
        # Regular customers can only view their own orders
        order = get_object_or_404(Order, id=order_id, ordered_by=request.user)
    
    # Define order progress steps with tracking information
    status_progress = [
        {'status': 'pending', 'label': 'Order Placed', 'icon': 'bi-receipt', 'description': 'Your order has been received'},
        {'status': 'confirmed', 'label': 'Order Confirmed', 'icon': 'bi-check-circle', 'description': 'Order confirmed by staff'},
        {'status': 'preparing', 'label': 'Preparing', 'icon': 'bi-hourglass-split', 'description': 'Kitchen is preparing your order'},
        {'status': 'ready', 'label': 'Ready', 'icon': 'bi-bell', 'description': 'Your order is ready for pickup'},
        {'status': 'served', 'label': 'Served', 'icon': 'bi-check2-all', 'description': 'Order has been served'},
    ]
    
    # Determine current step and completion status
    status_order = ['pending', 'confirmed', 'preparing', 'ready', 'served']
    try:
        current_step = status_order.index(order.status)
        completed_steps = current_step + 1 if order.status != 'cancelled' else 0
    except ValueError:
        current_step = -1
        completed_steps = 0
    
    # Payment status info
    payment_progress = {
        'unpaid': {'label': 'Payment Pending', 'icon': 'bi-credit-card', 'class': 'warning'},
        'partial': {'label': 'Partial Payment', 'icon': 'bi-credit-card-2-front', 'class': 'info'},
        'paid': {'label': 'Payment Complete', 'icon': 'bi-check-circle-fill', 'class': 'success'},
    }
    
    # Check for pending bill request for this table
    pending_bill_request = None
    if order.table_info and request.user.is_customer():
        pending_bill_request = BillRequest.objects.filter(
            table_info=order.table_info,
            status='pending'
        ).first()
    
    context = {
        'order': order,
        'status_progress': status_progress,
        'current_step': current_step,
        'completed_steps': completed_steps,
        'payment_info': payment_progress.get(order.payment_status, payment_progress['unpaid']),
        'is_cancelled': order.status == 'cancelled',
        'pending_bill_request': pending_bill_request,
    }
    
    return render(request, 'orders/order_detail.html', context)

@login_required
def track_order(request, order_number):
    """Track order by order number - for customer use"""
    order = get_object_or_404(Order, order_number=order_number, ordered_by=request.user)
    
    # Redirect to the detailed order tracking view
    return redirect('orders:order_detail', order_id=order.id)

@login_required
def order_list(request):
    """Order list with role-based filtering"""
    # Customer care users can only see their own orders
    if request.user.is_customer_care():
        orders = Order.objects.filter(ordered_by=request.user)
    else:
        # Admin, kitchen, owner can see all orders
        orders = Order.objects.all()
    
    # Order by most recent first
    orders = orders.select_related('table_info', 'ordered_by').prefetch_related('order_items__product').order_by('-created_at')
    
    context = {
        'orders': orders,
        'is_customer_care': request.user.is_customer_care(),
    }
    
    return render(request, 'orders/order_list.html', context)

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
    
    # Base queryset filtered by owner
    try:
        owner_filter = get_owner_filter(request.user)
        base_queryset = Order.objects.select_related('table_info', 'ordered_by', 'confirmed_by').prefetch_related('order_items__product')
        
        if owner_filter:
            # Filter orders where the customer belongs to the same owner as kitchen staff
            base_queryset = base_queryset.filter(table_info__owner=owner_filter)
        # If administrator or no owner filter, show all orders
        
    except PermissionDenied:
        messages.error(request, 'You are not associated with any restaurant.')
        return redirect('restaurant:home')
    
    # Only include orders that have at least one kitchen item
    def has_kitchen_items(order):
        return any(item.product.station == 'kitchen' for item in order.order_items.all())
    
    # Get orders by status and filter for kitchen items only
    pending_orders = [order for order in base_queryset.filter(status='pending').order_by('-created_at') if has_kitchen_items(order)]
    confirmed_orders = [order for order in base_queryset.filter(status='confirmed').order_by('-created_at') if has_kitchen_items(order)]
    preparing_orders = [order for order in base_queryset.filter(status='preparing').order_by('-created_at') if has_kitchen_items(order)]
    ready_orders = [order for order in base_queryset.filter(status='ready').order_by('-created_at') if has_kitchen_items(order)]
    served_orders = [order for order in base_queryset.filter(status='served').order_by('-created_at') if has_kitchen_items(order)]
    
    context = {
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'served_orders': served_orders,
        'pending_count': len(pending_orders),
        'confirmed_count': len(confirmed_orders),
        'preparing_count': len(preparing_orders),
        'ready_count': len(ready_orders),
        'served_count': len(served_orders),
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'orders/kitchen_dashboard.html', context)

@login_required
def bar_dashboard(request):
    """Bar staff dashboard to manage bar orders"""
    if not (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'bar'):
        messages.error(request, 'Access denied. Bar staff privileges required.')
        return redirect('restaurant:home')

    # Get filter parameters
    status_filter = request.GET.get('status', 'pending')

    try:
        owner_filter = get_owner_filter(request.user)
        base_queryset = Order.objects.select_related('table_info', 'ordered_by', 'confirmed_by').prefetch_related('order_items__product')
        if owner_filter:
            base_queryset = base_queryset.filter(table_info__owner=owner_filter)
    except PermissionDenied:
        messages.error(request, 'You are not associated with any restaurant.')
        return redirect('restaurant:home')

    # Only include orders that have at least one bar item
    def has_bar_items(order):
        return any(item.product.station == 'bar' for item in order.order_items.all())

    pending_orders = [order for order in base_queryset.filter(status='pending').order_by('-created_at') if has_bar_items(order)]
    confirmed_orders = [order for order in base_queryset.filter(status='confirmed').order_by('-created_at') if has_bar_items(order)]
    preparing_orders = [order for order in base_queryset.filter(status='preparing').order_by('-created_at') if has_bar_items(order)]
    ready_orders = [order for order in base_queryset.filter(status='ready').order_by('-created_at') if has_bar_items(order)]
    served_orders = [order for order in base_queryset.filter(status='served').order_by('-created_at') if has_bar_items(order)]

    context = {
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'served_orders': served_orders,
        'pending_count': len(pending_orders),
        'confirmed_count': len(confirmed_orders),
        'preparing_count': len(preparing_orders),
        'ready_count': len(ready_orders),
        'served_count': len(served_orders),
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'orders/bar_dashboard.html', context)

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
        
        # Mark table as occupied when order is confirmed
        table = order.table_info
        table.is_available = False
        table.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order {order.order_number} confirmed successfully! Table {table.tbl_no} is now occupied.',
            'new_status': order.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred.'})

@login_required
@require_POST
def update_order_status(request, order_id):
    """Update order status"""
    if not (request.user.is_kitchen_staff() or request.user.is_bar_staff()):
        return JsonResponse({'success': False, 'message': 'Access denied.'})
    
    try:
        # Get owner filter for current user
        owner_filter = get_owner_filter(request.user)
        
        # Handle both JSON and form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            new_status = data.get('status')
        else:
            # Handle form data
            new_status = request.POST.get('status')
        
        if new_status not in ['confirmed', 'preparing', 'ready', 'served', 'cancelled']:
            return JsonResponse({'success': False, 'message': 'Invalid status.'})
        
        # Get order with owner filtering
        if owner_filter:
            order = get_object_or_404(Order, id=order_id, table_info__owner=owner_filter)
        else:
            order = get_object_or_404(Order, id=order_id)
        
        # Check if bar staff is trying to update an order without bar items
        if request.user.is_bar_staff():
            has_bar_items = any(item.product.station == 'bar' for item in order.order_items.all())
            if not has_bar_items:
                return JsonResponse({'success': False, 'message': 'Access denied. This order contains no bar items.'})
        
        # Check if kitchen staff is trying to update an order without kitchen items
        if request.user.is_kitchen_staff():
            has_kitchen_items = any(item.product.station == 'kitchen' for item in order.order_items.all())
            if not has_kitchen_items:
                return JsonResponse({'success': False, 'message': 'Access denied. This order contains no kitchen items.'})
        
        # More flexible status transitions for mobile/real-world usage
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['ready', 'cancelled'],
            'ready': ['served', 'cancelled'],
            'served': ['cancelled'],  # Allow cancellation even after served (refunds, etc.)
            'cancelled': []
        }
        
        # Allow kitchen staff and bar staff to change status backwards for corrections
        if request.user.is_kitchen_staff() or request.user.is_bar_staff() or request.user.is_owner():
            valid_transitions.update({
                'confirmed': ['pending', 'preparing', 'cancelled'],
                'preparing': ['confirmed', 'ready', 'cancelled'], 
                'ready': ['preparing', 'served', 'cancelled'],
                'served': ['ready', 'cancelled']  # Allow corrections
            })
        
        if new_status not in valid_transitions.get(order.status, []):
            return JsonResponse({'success': False, 'message': 'Invalid status transition.'})
        
        # Handle cancellation reason
        if new_status == 'cancelled':
            cancel_reason = request.POST.get('cancel_reason', '') if request.content_type != 'application/json' else data.get('cancel_reason', '')
            order.reason_if_cancelled = cancel_reason
        
        order.status = new_status
        if new_status == 'confirmed' and not order.confirmed_by:
            order.confirmed_by = request.user
        
        # Release table if order is cancelled through status change
        if new_status == 'cancelled':
            order.release_table()
            
        order.save()

        # Send real-time notifications
        async_to_sync(channel_layer.group_send)(
            f'order_{order.id}',
            {
                'type': 'order_status_update',
                'message': {
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'status_display': order.get_status_display(),
                    'updated_by': request.user.get_full_name() or request.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )

        # Send notification to restaurant staff
        if order.ordered_by and hasattr(order.ordered_by, 'owner'):
            owner_id = order.ordered_by.owner.id
        else:
            owner_id = 'default'
            
        async_to_sync(channel_layer.group_send)(
            f'restaurant_{owner_id}',
            {
                'type': 'order_status_update',
                'message': {
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'status_display': order.get_status_display(),
                    'customer': order.ordered_by.get_full_name() or order.ordered_by.username,
                    'updated_by': request.user.get_full_name() or request.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )

        # Return appropriate response based on request type
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'message': f'Order {order.order_number} updated to {order.get_status_display()}!',
                'new_status': order.get_status_display()
            })
        else:
            # For form submissions, redirect based on user role
            messages.success(request, f'Order {order.order_number} updated to {order.get_status_display()}!')
            if request.user.is_bar_staff():
                return redirect('orders:bar_dashboard')
            else:
                return redirect('orders:kitchen_dashboard')
        
    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse({'success': False, 'message': 'An error occurred.'})
        else:
            messages.error(request, 'An error occurred while updating the order.')
            if request.user.is_bar_staff():
                return redirect('orders:bar_dashboard')
            else:
                return redirect('orders:kitchen_dashboard')

@login_required
def cancel_order(request, order_id):
    """Cancel an order with reason"""
    if not request.user.is_kitchen_staff():
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'message': 'Access denied. Kitchen staff privileges required.'})
        messages.error(request, 'Access denied. Kitchen staff privileges required.')
        return redirect('orders:kitchen_dashboard')
    
    try:
        owner_filter = get_owner_filter(request.user)
        
        # Get order with owner filtering
        if owner_filter:
            order = get_object_or_404(Order, id=order_id, table_info__owner=owner_filter)
        else:
            order = get_object_or_404(Order, id=order_id)
    except PermissionDenied:
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'message': 'You are not associated with any restaurant.'})
        messages.error(request, 'You are not associated with any restaurant.')
        return redirect('orders:kitchen_dashboard')
    
    if order.status in ['served', 'cancelled']:
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'message': 'Cannot cancel this order.'})
        messages.error(request, 'Cannot cancel this order.')
        return redirect('orders:kitchen_dashboard')
    
    if request.method == 'POST':
        # Handle AJAX request
        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                reason = data.get('reason', '').strip()
                
                if not reason:
                    return JsonResponse({'success': False, 'message': 'Cancellation reason is required.'})
                
                with transaction.atomic():
                    # Restore product stock
                    for item in order.order_items.all():
                        product = item.product
                        product.available_in_stock += item.quantity
                        product.save()
                    
                    # Update order
                    order.status = 'cancelled'
                    order.reason_if_cancelled = reason
                    # Release the table when order is cancelled
                    order.release_table()
                    order.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Order {order.order_number} cancelled successfully.'
                    })
                    
            except Exception as e:
                return JsonResponse({'success': False, 'message': 'An error occurred while cancelling the order.'})
        
        # Handle regular form submission
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
                # Release the table when order is cancelled
                order.release_table()
                order.save()
                
                messages.success(request, f'Order {order.order_number} cancelled successfully.')
                return redirect('orders:kitchen_dashboard')
    else:
        form = CancelOrderForm()
    
    return render(request, 'orders/cancel_order.html', {'form': form, 'order': order})

@login_required
def customer_cancel_order(request, order_id):
    """Allow customers and customer care to cancel pending orders"""
    if not (request.user.is_customer() or request.user.is_customer_care()):
        messages.error(request, 'Access denied. Customer privileges required.')
        return redirect('restaurant:home')
    
    # Get the order - ensure it belongs to the user for customers
    if request.user.is_customer():
        order = get_object_or_404(Order, id=order_id, ordered_by=request.user)
    else:  # Customer care can cancel orders from their restaurant
        try:
            owner_filter = get_owner_filter(request.user)
            if owner_filter:
                order = get_object_or_404(Order, id=order_id, table_info__owner=owner_filter)
            else:
                order = get_object_or_404(Order, id=order_id)
        except PermissionDenied:
            messages.error(request, 'You are not associated with any restaurant.')
            return redirect('restaurant:home')
    
    # Check if order can be cancelled (only pending orders)
    if order.status != 'pending':
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': False, 
                'message': 'Order cannot be cancelled. It has already been confirmed by the kitchen.'
            })
        messages.error(request, 'Order cannot be cancelled. It has already been confirmed by the kitchen.')
        return redirect('orders:my_orders' if request.user.is_customer() else 'orders:customer_care_dashboard')
    
    if request.method == 'POST':
        # Handle AJAX request
        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                reason = data.get('reason', 'Cancelled by customer').strip()
                
                with transaction.atomic():
                    # Restore product stock
                    for item in order.order_items.all():
                        product = item.product
                        product.available_in_stock += item.quantity
                        product.save()
                    
                    # Update order
                    order.status = 'cancelled'
                    order.reason_if_cancelled = reason
                    # Release the table when order is cancelled
                    order.release_table()
                    order.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Order {order.order_number} cancelled successfully.'
                    })
                    
            except Exception as e:
                return JsonResponse({'success': False, 'message': 'An error occurred while cancelling the order.'})
        
        # Handle regular form submission
        reason = request.POST.get('reason', 'Cancelled by customer').strip()
        
        try:
            with transaction.atomic():
                # Restore product stock
                for item in order.order_items.all():
                    product = item.product
                    product.available_in_stock += item.quantity
                    product.save()
                
                # Update order
                order.status = 'cancelled'
                order.reason_if_cancelled = reason if reason else 'Cancelled by customer'
                # Release the table when order is cancelled
                order.release_table()
                order.save()
                
                messages.success(request, f'Order {order.order_number} cancelled successfully.')
                return redirect('orders:my_orders' if request.user.is_customer() else 'orders:customer_care_dashboard')
        except Exception as e:
            messages.error(request, 'An error occurred while cancelling the order.')
    
    context = {
        'order': order,
        'can_cancel': order.status == 'pending',
        'is_customer_care': request.user.is_customer_care()
    }
    
    return render(request, 'orders/customer_cancel_order.html', context)

@login_required
def kitchen_order_detail(request, order_id):
    """Detailed view of order for kitchen staff"""
    if not request.user.is_kitchen_staff():
        messages.error(request, 'Access denied. Kitchen staff privileges required.')
        return redirect('restaurant:home')
    
    try:
        owner_filter = get_owner_filter(request.user)
        
        # Get order with owner filtering
        if owner_filter:
            order = get_object_or_404(Order, id=order_id, table_info__owner=owner_filter)
        else:
            order = get_object_or_404(Order, id=order_id)
    except PermissionDenied:
        messages.error(request, 'You are not associated with any restaurant.')
        return redirect('orders:kitchen_dashboard')
        
    return render(request, 'orders/kitchen_order_detail.html', {'order': order})

@login_required
def customer_care_dashboard(request):
    """Customer care dashboard with orders placed by this customer care user from their restaurant only"""
    if not request.user.is_customer_care():
        messages.error(request, 'Access denied. Customer care privileges required.')
        return redirect('restaurant:home')
    
    # Set restaurant context for customer care users
    if request.user.owner:
        request.session['selected_restaurant_id'] = request.user.owner.id
        request.session['selected_restaurant_name'] = request.user.owner.restaurant_name
    
    try:
        # Get customer care user's assigned restaurant
        owner_filter = get_owner_filter(request.user)
        
        if owner_filter:
            # Get orders placed BY this customer care user from their assigned restaurant only
            user_orders = Order.objects.filter(
                ordered_by=request.user,
                table_info__owner=owner_filter
            )
        else:
            # If no restaurant assignment, show all their orders
            user_orders = Order.objects.filter(ordered_by=request.user)
            
    except PermissionDenied:
        messages.error(request, 'You are not associated with any restaurant.')
        return redirect('restaurant:home')
    
    # Calculate statistics for today
    today = timezone.now().date()
    today_orders = user_orders.filter(created_at__date=today)
    
    stats = {
        'total_orders': today_orders.count(),
        'pending_orders': today_orders.filter(status__in=['pending', 'confirmed']).count(),
        'completed_orders': today_orders.filter(status='served').count(),
        'cancelled_orders': today_orders.filter(status='cancelled').count(),
    }
    
    # Get recent orders (last 10) placed by this customer care user from their restaurant
    recent_orders = user_orders.select_related(
        'table_info', 'table_info__owner', 'confirmed_by'
    ).prefetch_related(
        'order_items__product'
    ).order_by('-created_at')[:10]
    
    # Get pending bill requests from the same restaurant
    pending_bill_requests = []
    if owner_filter:
        pending_bill_requests = BillRequest.objects.filter(
            table_info__owner=owner_filter,
            status='pending'
        ).select_related('table_info', 'requested_by').order_by('-created_at')
    
    context = {
        'stats': stats,
        'recent_orders': recent_orders,
        'pending_bill_requests': pending_bill_requests,
        'user': request.user,
        'restaurant': owner_filter if owner_filter else None,
        'restaurant_name': owner_filter.restaurant_name if owner_filter else 'Restaurant',
    }
    
    return render(request, 'orders/customer_care_dashboard.html', context)


@login_required
def customer_care_payments(request):
    """Customer Care payment processing interface - separate from cashier dashboard"""
    if not (request.user.is_customer_care() or request.user.is_owner()):
        messages.error(request, "Access denied. Customer Care or Owner role required.")
        return redirect('accounts:profile')
    
    owner = get_owner_filter(request.user)
    
    # Get table filter from request
    table_filter = request.GET.get('table', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset for orders
    orders = Order.objects.filter(table_info__owner=owner)
    
    # Apply filters
    if table_filter:
        orders = orders.filter(table_info__tbl_no__icontains=table_filter)
    
    if status_filter:
        orders = orders.filter(payment_status=status_filter)
    
    # Prefetch related data
    from django.db.models import Prefetch
    orders = orders.select_related('table_info', 'ordered_by').prefetch_related(
        Prefetch('order_items', queryset=OrderItem.objects.select_related('product')),
        'payments'
    ).order_by('-created_at')
    
    # Get all tables for dropdown
    tables = TableInfo.objects.filter(owner=owner).order_by('tbl_no')
    
    # Get products for waste recording modal
    products = Product.objects.filter(
        main_category__owner=owner,
        is_available=True
    ).select_related('main_category')
    
    context = {
        'orders': orders,
        'tables': tables,
        'products': products,
        'table_filter': table_filter,
        'status_filter': status_filter,
        'user': request.user,
        'is_customer_care': True,  # Flag to identify this is customer care interface
    }
    
    return render(request, 'orders/customer_care_payments.html', context)


@login_required
def customer_care_receipt(request, payment_id):
    """Generate receipt for Customer Care - separate from cashier"""
    if not (request.user.is_customer_care() or request.user.is_owner()):
        messages.error(request, "Access denied. Customer Care or Owner role required.")
        return redirect('accounts:profile')
    
    from cashier.models import Payment
    from decimal import Decimal
    
    owner = get_owner_filter(request.user)
    payment = get_object_or_404(
        Payment, 
        id=payment_id, 
        order__table_info__owner=owner
    )
    
    # Get the order with all related data
    order = payment.order
    
    # Calculate change and remaining balance
    change_amount = payment.amount - order.get_total() if payment.payment_method == 'cash' and payment.amount > order.get_total() else Decimal('0.00')
    remaining_balance = order.get_total() - payment.amount if payment.amount < order.get_total() else Decimal('0.00')
    
    context = {
        'payment': payment,
        'order': order,
        'user': request.user,  # Current user viewing the receipt
        'change_amount': change_amount,
        'remaining_balance': remaining_balance,
        'is_customer_care_interface': True,  # Flag for template
    }
    
    return render(request, 'orders/customer_care_receipt.html', context)


@login_required
def customer_care_reprint_receipt(request, payment_id):
    """Reprint receipt for Customer Care"""
    if not (request.user.is_customer_care() or request.user.is_owner()):
        messages.error(request, "Access denied. Customer Care or Owner role required.")
        return redirect('accounts:profile')
    
    from cashier.models import Payment
    from decimal import Decimal
    
    owner = get_owner_filter(request.user)
    payment = get_object_or_404(
        Payment, 
        id=payment_id, 
        order__table_info__owner=owner
    )
    
    # Add a message indicating this is a reprint
    messages.info(request, f"Reprinting receipt #{payment.id:06d}")
    
    # Get the order with all related data
    order = payment.order
    
    # Calculate change and remaining balance
    change_amount = payment.amount - order.get_total() if payment.payment_method == 'cash' and payment.amount > order.get_total() else Decimal('0.00')
    remaining_balance = order.get_total() - payment.amount if payment.amount < order.get_total() else Decimal('0.00')
    
    context = {
        'payment': payment,
        'order': order,
        'user': request.user,
        'is_reprint': True,
        'change_amount': change_amount,
        'remaining_balance': remaining_balance,
        'is_customer_care_interface': True,
    }
    
    return render(request, 'orders/customer_care_receipt.html', context)


@login_required
def customer_care_receipt_management(request):
    """Manage receipts for Customer Care - search and reprint by order number or date"""
    if not (request.user.is_customer_care() or request.user.is_owner()):
        messages.error(request, "Access denied. Customer Care or Owner role required.")
        return redirect('accounts:profile')
    
    from cashier.models import Payment
    from restaurant.models import Product
    from django.db.models import Q
    
    owner = get_owner_filter(request.user)
    
    # Get search parameters
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset for payments
    payments = Payment.objects.filter(
        order__table_info__owner=owner,
        is_voided=False
    ).select_related(
        'order', 'order__table_info', 'processed_by'
    ).order_by('-created_at')
    
    # Apply filters
    if search_query:
        payments = payments.filter(
            Q(order__order_number__icontains=search_query) |
            Q(id=search_query if search_query.isdigit() else 0)
        )
    
    if date_from:
        payments = payments.filter(created_at__date__gte=date_from)
    
    if date_to:
        payments = payments.filter(created_at__date__lte=date_to)
    
    # Limit results for performance
    payments = payments[:50]
    
    context = {
        'payments': payments,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'user': request.user,
    }
    
    return render(request, 'orders/customer_care_receipt_management.html', context)

@login_required
def view_receipt(request, order_id):
    """View receipt for a paid order"""
    # Get the order - ensure user has permission to view it
    if request.user.is_customer():
        order = get_object_or_404(Order, id=order_id, ordered_by=request.user)
    elif request.user.is_customer_care():
        try:
            owner_filter = get_owner_filter(request.user)
            if owner_filter:
                order = get_object_or_404(Order, id=order_id, table_info__owner=owner_filter)
            else:
                order = get_object_or_404(Order, id=order_id)
        except PermissionDenied:
            messages.error(request, 'You are not associated with any restaurant.')
            return redirect('orders:my_orders')
    else:
        messages.error(request, 'Access denied.')
        return redirect('orders:my_orders')
    
    # Check if order is paid
    if order.payment_status != 'paid':
        messages.error(request, 'Receipt is only available for paid orders.')
        return redirect('orders:my_orders')
    
    # Get payment information
    payments = order.payments.filter(is_voided=False).select_related('processed_by').order_by('created_at')
    
    # Calculate totals
    subtotal = order.get_subtotal()
    tax_amount = order.get_tax_amount()
    discount_amount = order.get_total_discount()
    total_amount = order.total_amount
    
    context = {
        'order': order,
        'payments': payments,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'discount_amount': discount_amount,
        'total_amount': total_amount,
        'restaurant_name': order.table_info.owner.restaurant_name,
        'restaurant_owner': order.table_info.owner,
    }
    
    return render(request, 'orders/receipt.html', context)


@login_required
def print_kot(request, order_id):
    """
    Generate Kitchen Order Ticket (KOT) for kitchen staff
    
    KOT is printed when:
    - Order is placed by customer or customer care
    - Kitchen staff needs to reprint order details
    - Order is confirmed and needs kitchen preparation
    
    Accessible by: Kitchen staff, Customer care, Cashier, Owner, Administrator
    """
    # Get the order
    order = get_object_or_404(Order, id=order_id)
    
    # Permission check - only staff can print KOT
    if not (request.user.is_kitchen_staff() or 
            request.user.is_customer_care() or 
            request.user.is_cashier() or
            request.user.is_owner() or 
            request.user.is_administrator()):
        messages.error(request, 'Access denied. Staff privileges required to print KOT.')
        return redirect('orders:my_orders')
    
    # Check owner permission (ensure user can access this restaurant's order)
    try:
        if not request.user.is_administrator():
            owner_filter = get_owner_filter(request.user)
            if owner_filter and order.table_info.owner != owner_filter:
                messages.error(request, 'Access denied. This order belongs to a different restaurant.')
                return redirect('orders:kitchen_dashboard')
    except Exception:
        messages.error(request, 'Permission error. Please contact administrator.')
        return redirect('orders:kitchen_dashboard')
    
    # Context for KOT template
    context = {
        'order': order,
        'now': timezone.now(),
    }
    
    return render(request, 'orders/kot.html', context)


@login_required  
def reprint_kot(request, order_id):
    """
    Reprint Kitchen Order Ticket for existing order
    Same as print_kot but with a different message for tracking
    """
    order = get_object_or_404(Order, id=order_id)
    
    # Permission check
    if not (request.user.is_kitchen_staff() or 
            request.user.is_customer_care() or 
            request.user.is_cashier() or
            request.user.is_owner() or 
            request.user.is_administrator()):
        messages.error(request, 'Access denied. Staff privileges required.')
        return redirect('orders:my_orders')
    
    # Add reprint message
    messages.info(request, f'Reprinting KOT for Order #{order.order_number}')
    
    context = {
        'order': order,
        'now': timezone.now(),
        'is_reprint': True,
    }
    
    return render(request, 'orders/kot.html', context)


@login_required
def print_bot(request, order_id):
    """
    Generate Bar Order Ticket (BOT) for bar staff
    
    BOT is printed when:
    - Order contains bar items
    - Bar staff needs to prepare drinks
    - Order is confirmed and needs bar preparation
    
    Accessible by: Bar staff, Customer care, Cashier, Owner, Administrator
    """
    # Get the order
    order = get_object_or_404(Order, id=order_id)
    
    # Permission check - only staff can print BOT
    if not (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'bar') and not (
            request.user.is_customer_care() or 
            request.user.is_cashier() or
            request.user.is_owner() or 
            request.user.is_administrator()):
        messages.error(request, 'Access denied. Staff privileges required to print BOT.')
        return redirect('orders:my_orders')
    
    # Check owner permission (ensure user can access this restaurant's order)
    try:
        if not request.user.is_administrator():
            owner_filter = get_owner_filter(request.user)
            if owner_filter and order.table_info.owner != owner_filter:
                messages.error(request, 'Access denied. This order belongs to a different restaurant.')
                return redirect('orders:bar_dashboard')
    except Exception:
        messages.error(request, 'Permission error. Please contact administrator.')
        return redirect('orders:bar_dashboard')
    
    # Context for BOT template
    context = {
        'order': order,
        'now': timezone.now(),
    }
    
    return render(request, 'orders/bot.html', context)


@login_required  
def reprint_bot(request, order_id):
    """
    Reprint Bar Order Ticket for existing order
    Same as print_bot but with a different message for tracking
    """
    order = get_object_or_404(Order, id=order_id)
    
    # Permission check
    if not (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'bar') and not (
            request.user.is_customer_care() or 
            request.user.is_cashier() or
            request.user.is_owner() or 
            request.user.is_administrator()):
        messages.error(request, 'Access denied. Staff privileges required.')
        return redirect('orders:my_orders')
    
    # Add reprint message
    messages.info(request, f'Reprinting BOT for Order #{order.order_number}')
    
    context = {
        'order': order,
        'now': timezone.now(),
        'is_reprint': True,
    }
    
    return render(request, 'orders/bot.html', context)



@login_required
def request_bill(request, table_id):
    "Customer requests bill for their table"
    if not request.user.is_customer():
        messages.error(request, 'Access denied. Customer privileges required.')
        return redirect('orders:my_orders')
    
    try:
        table = TableInfo.objects.get(id=table_id)
        
        # Check if customer belongs to this restaurant
        if request.user.get_owner() != table.owner:
            messages.error(request, 'You can only request bill for your restaurant tables.')
            return redirect('orders:my_orders')
        
        # Check if there's already a pending bill request for this table
        existing_request = BillRequest.objects.filter(
            table_info=table,
            status='pending'
        ).first()
        
        if existing_request:
            messages.warning(request, f'Bill request already submitted for Table {table.tbl_no}. Staff will bring your bill shortly.')
        else:
            # Create new bill request
            bill_request = BillRequest.objects.create(
                table_info=table,
                requested_by=request.user,
                status='pending'
            )
            messages.success(request, f'Bill requested for Table {table.tbl_no}! Staff will bring your bill shortly.')
        
    except TableInfo.DoesNotExist:
        messages.error(request, 'Table not found.')
    
    return redirect('orders:my_orders')

@login_required
def request_bill(request, table_id):
    """Customer requests bill for their table"""
    if not request.user.is_customer():
        messages.error(request, 'Access denied. Customer privileges required.')
        return redirect('orders:my_orders')
    
    try:
        table = TableInfo.objects.get(id=table_id)
        
        # Get restaurant context from QR code session (not user ownership)
        selected_restaurant_id = request.session.get('selected_restaurant_id')
        
        if not selected_restaurant_id:
            messages.error(request, 'Restaurant context not found. Please scan QR code again.')
            return redirect('orders:my_orders')
        
        # Verify the table belongs to the restaurant from QR code session
        try:
            current_restaurant = User.objects.get(id=selected_restaurant_id, role__name='owner')
        except User.DoesNotExist:
            messages.error(request, 'Invalid restaurant context. Please scan QR code again.')
            return redirect('orders:my_orders')
        
        if table.owner != current_restaurant:
            messages.error(request, 'You can only request bill for tables in the current restaurant.')
            return redirect('orders:my_orders')
        
        # Check if there's already a pending bill request for this table
        existing_request = BillRequest.objects.filter(
            table_info=table,
            status='pending'
        ).first()
        
        if existing_request:
            messages.warning(request, f'Bill request already submitted for Table {table.tbl_no}. Staff will bring your bill shortly.')
        else:
            # Create new bill request
            bill_request = BillRequest.objects.create(
                table_info=table,
                requested_by=request.user,
                status='pending'
            )
            messages.success(request, f'Bill requested for Table {table.tbl_no}! Staff will bring your bill shortly.')
        
    except TableInfo.DoesNotExist:
        messages.error(request, 'Table not found.')
    except Exception as e:
        messages.error(request, f'An error occurred: {e}')
    
    return redirect('orders:my_orders')


@login_required
def mark_bill_request_completed(request, request_id):
    """Staff marks bill request as completed"""
    if not (request.user.is_customer_care() or request.user.is_owner() or request.user.is_cashier()):
        messages.error(request, 'Access denied. Staff privileges required.')
        return redirect('orders:my_orders')
    
    try:
        bill_request = BillRequest.objects.get(id=request_id)
        
        # Check ownership
        if request.user.get_owner() != bill_request.owner:
            messages.error(request, 'Access denied.')
            return redirect('orders:customer_care_dashboard')
        
        # Mark as completed
        bill_request.status = 'completed'
        bill_request.completed_by = request.user
        bill_request.completed_at = timezone.now()
        bill_request.save()
        
        messages.success(request, f'Bill request for Table {bill_request.table_info.tbl_no} marked as completed.')
        
    except BillRequest.DoesNotExist:
        messages.error(request, 'Bill request not found.')
    
    return redirect('orders:customer_care_dashboard')
