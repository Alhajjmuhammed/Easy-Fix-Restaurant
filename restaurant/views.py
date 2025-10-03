from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from .models import MainCategory, SubCategory, Product, TableInfo, HappyHourPromotion
from .forms import ProductForm, MainCategoryForm, SubCategoryForm, TableForm, StaffForm, HappyHourPromotionForm
from orders.models import Order
from accounts.models import User, Role

def home(request):
    return render(request, 'restaurant/home.html')

def menu(request):
    """Display menu with cart functionality"""
    # Check if table is selected
    if 'selected_table' not in request.session:
        messages.warning(request, 'Please select your table number first.')
        return redirect('orders:select_table')

    table_number = request.session['selected_table']
    
    # Get current restaurant for filtering menu
    current_restaurant = None
    
    # For customer care users, use their assigned restaurant
    if request.user.is_authenticated and request.user.is_customer_care() and request.user.owner:
        current_restaurant = request.user.owner
        # Ensure session data is set for consistency
        request.session['selected_restaurant_id'] = current_restaurant.id
        request.session['selected_restaurant_name'] = current_restaurant.restaurant_name
    else:
        # For regular customers, use QR code session
        selected_restaurant_id = request.session.get('selected_restaurant_id')
        
        if selected_restaurant_id:
            try:
                current_restaurant = User.objects.get(id=selected_restaurant_id, role__name='owner')
            except User.DoesNotExist:
                messages.error(request, 'Selected restaurant not found.')
                return redirect('orders:select_table')
    
    # Filter categories by current restaurant
    if current_restaurant:
        categories = MainCategory.objects.filter(
            is_active=True, 
            owner=current_restaurant
        ).prefetch_related('subcategories__products').order_by('name')
        
        restaurant_name = current_restaurant.restaurant_name
    else:
        # Fallback: try traditional owner filtering for staff/tied customers
        try:
            from accounts.models import get_owner_filter
            owner_filter = get_owner_filter(request.user)
            if owner_filter:
                categories = MainCategory.objects.filter(
                    is_active=True, 
                    owner=owner_filter
                ).prefetch_related('subcategories__products').order_by('name')
                restaurant_name = owner_filter.restaurant_name
            else:
                # Administrator can see all categories
                categories = MainCategory.objects.filter(is_active=True).prefetch_related('subcategories__products').order_by('name')
                restaurant_name = "Restaurant System"
        except Exception:
            # Fallback - show no categories if user not properly associated
            categories = MainCategory.objects.none()
            restaurant_name = "Restaurant"

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
        'restaurant_name': restaurant_name,
        'current_restaurant': current_restaurant,
    }

    return render(request, 'restaurant/menu.html', context)

@login_required
def owner_dashboard(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Get owner filter for data isolation
    from accounts.models import get_owner_filter
    try:
        owner_filter = get_owner_filter(request.user)
        
        # Dashboard statistics - filtered by owner
        if owner_filter:
            total_products = Product.objects.filter(main_category__owner=owner_filter).count()
            total_orders = Order.objects.filter(ordered_by__owner=owner_filter).count()
            pending_orders = Order.objects.filter(status='pending', ordered_by__owner=owner_filter).count()
            total_staff = User.objects.filter(owner=owner_filter).exclude(role__name='customer').count()
            
            # Recent orders - filtered by owner
            recent_orders = Order.objects.filter(
                ordered_by__owner=owner_filter
            ).select_related('table_info', 'ordered_by').order_by('-created_at')[:5]
        else:
            # Administrator sees all data
            total_products = Product.objects.count()
            total_orders = Order.objects.count()
            pending_orders = Order.objects.filter(status='pending').count()
            total_staff = User.objects.exclude(role__name='customer').count()
            recent_orders = Order.objects.select_related('table_info', 'ordered_by').order_by('-created_at')[:5]
    except Exception:
        # Fallback - no data if user not properly associated
        total_products = total_orders = pending_orders = total_staff = 0
        recent_orders = Order.objects.none()
    
    # Popular products
    popular_products = Product.objects.annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count')[:5]
    
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'total_staff': total_staff,
        'recent_orders': recent_orders,
        'popular_products': popular_products,
    }
    
    return render(request, 'restaurant/owner_dashboard.html', context)

@login_required
def manage_products(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Get products with owner filtering
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    if owner_filter:
        products = Product.objects.filter(main_category__owner=owner_filter).select_related('main_category', 'sub_category').order_by('-created_at')
    else:
        products = Product.objects.select_related('main_category', 'sub_category').order_by('-created_at')
    
    return render(request, 'restaurant/manage_products.html', {'products': products})

@login_required
def add_product(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Get owner filter for form
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, owner=owner_filter)
        if form.is_valid():
            product = form.save(commit=False)
            # Verify the main category belongs to this owner
            if owner_filter and product.main_category.owner != owner_filter:
                messages.error(request, 'Access denied. Category not found.')
                return redirect('restaurant:manage_products')
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('restaurant:manage_products')
    else:
        form = ProductForm(owner=owner_filter)
    
    return render(request, 'restaurant/add_product.html', {'form': form})

@login_required
def edit_product(request, product_id):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Get product with owner filtering
    from accounts.models import get_owner_filter
    try:
        owner_filter = get_owner_filter(request.user)
        if owner_filter:
            product = get_object_or_404(Product, id=product_id, main_category__owner=owner_filter)
        else:
            product = get_object_or_404(Product, id=product_id)
    except Exception:
        messages.error(request, 'Product not found or access denied.')
        return redirect('restaurant:manage_products')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, owner=owner_filter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('restaurant:manage_products')
    else:
        form = ProductForm(instance=product, owner=owner_filter)
    
    return render(request, 'restaurant/edit_product.html', {'form': form, 'product': product})

@login_required
def delete_product(request, product_id):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Get product with owner filtering
    from accounts.models import get_owner_filter
    try:
        owner_filter = get_owner_filter(request.user)
        if owner_filter:
            product = get_object_or_404(Product, id=product_id, main_category__owner=owner_filter)
        else:
            product = get_object_or_404(Product, id=product_id)
    except Exception:
        messages.error(request, 'Product not found or access denied.')
        return redirect('restaurant:manage_products')
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('restaurant:manage_products')
    
    return render(request, 'restaurant/delete_product.html', {'product': product})

@login_required
def manage_categories(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Get categories with owner filtering
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    if owner_filter:
        main_categories = MainCategory.objects.filter(owner=owner_filter).prefetch_related('subcategories').order_by('name')
    else:
        main_categories = MainCategory.objects.prefetch_related('subcategories').order_by('name')
    
    return render(request, 'restaurant/manage_categories.html', {'main_categories': main_categories})

@login_required
def add_category(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    if request.method == 'POST':
        form = MainCategoryForm(request.POST)
        if form.is_valid():
            # Set owner before saving
            from accounts.models import get_owner_filter
            owner_filter = get_owner_filter(request.user)
            category = form.save(commit=False)
            if owner_filter:
                category.owner = owner_filter
            category.save()
            messages.success(request, 'Category added successfully!')
            return redirect('restaurant:manage_categories')
    else:
        form = MainCategoryForm()
    
    return render(request, 'restaurant/add_category.html', {'form': form})

@login_required
def add_subcategory(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    if request.method == 'POST':
        form = SubCategoryForm(request.POST)
        if form.is_valid():
            # Verify the main category belongs to this owner
            from accounts.models import get_owner_filter
            owner_filter = get_owner_filter(request.user)
            subcategory = form.save(commit=False)
            
            if owner_filter and subcategory.main_category.owner != owner_filter:
                messages.error(request, 'Access denied. Category not found.')
                return redirect('restaurant:manage_categories')
            
            subcategory.save()
            messages.success(request, 'Subcategory added successfully!')
            return redirect('restaurant:manage_categories')
    else:
        form = SubCategoryForm()
        # Filter main categories by owner
        from accounts.models import get_owner_filter
        owner_filter = get_owner_filter(request.user)
        if owner_filter:
            form.fields['main_category'].queryset = MainCategory.objects.filter(owner=owner_filter)
    
    return render(request, 'restaurant/add_subcategory.html', {'form': form})

@login_required
def manage_staff(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Get staff members belonging to this owner only
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    if owner_filter:
        staff_members = User.objects.filter(owner=owner_filter).exclude(role__name='customer').select_related('role').order_by('role__name', 'username')
    else:
        staff_members = User.objects.exclude(role__name='customer').select_related('role').order_by('role__name', 'username')
    
    return render(request, 'restaurant/manage_staff.html', {'staff_members': staff_members})

@login_required
def add_staff(request):
    if not request.user.is_owner():
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'message': 'Access denied. Owner privileges required.'})
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    if request.method == 'POST':
        # Handle AJAX request from owner dashboard
        if request.headers.get('Content-Type') == 'application/json':
            try:
                import json
                data = json.loads(request.body)
                
                # Validate required fields
                required_fields = ['username', 'email', 'first_name', 'last_name', 'role', 'password']
                for field in required_fields:
                    if not data.get(field):
                        return JsonResponse({'success': False, 'message': f'{field.replace("_", " ").title()} is required'})
                
                # Check if username already exists
                if User.objects.filter(username=data['username']).exists():
                    return JsonResponse({'success': False, 'message': 'Username already exists'})
                
                # Check if email already exists
                if User.objects.filter(email=data['email']).exists():
                    return JsonResponse({'success': False, 'message': 'Email already exists'})
                
                # Validate role (owner can only add kitchen and customer_care)
                allowed_roles = ['kitchen', 'customer_care']
                if data['role'] not in allowed_roles:
                    return JsonResponse({'success': False, 'message': 'Invalid role. Owner can only add Kitchen Staff or Customer Care.'})
                
                # Get the role object
                try:
                    role = Role.objects.get(name=data['role'])
                except Role.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Role not found'})
                
                # Create the user
                from accounts.models import get_owner_filter
                owner_filter = get_owner_filter(request.user)
                user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=data['password'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    role=role,
                    phone_number=data.get('phone_number', ''),
                    is_active_staff=True,
                    owner=owner_filter if owner_filter else None
                )
                
                return JsonResponse({
                    'success': True, 
                    'message': f'{user.get_full_name()} added as {role.get_name_display()} successfully!'
                })
                
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Error creating user: {str(e)}'})
        
        # Handle regular form submission
        form = StaffForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            # Set owner for the new staff member
            from accounts.models import get_owner_filter
            owner_filter = get_owner_filter(request.user)
            if owner_filter:
                user.owner = owner_filter
            user.save()
            messages.success(request, f'{user.get_full_name()} added as {user.role.get_name_display()}!')
            return redirect('restaurant:manage_staff')
    else:
        form = StaffForm()
    
    return render(request, 'restaurant/add_staff.html', {'form': form})

@login_required
def view_orders(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    status_filter = request.GET.get('status', 'all')
    
    # Get orders with owner filtering
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    if owner_filter:
        orders = Order.objects.filter(table_info__owner=owner_filter).select_related('table_info', 'ordered_by', 'confirmed_by').order_by('-created_at')
    else:
        orders = Order.objects.select_related('table_info', 'ordered_by', 'confirmed_by').order_by('-created_at')
    
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'restaurant/view_orders.html', context)

@login_required
def manage_tables(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Get tables with owner filtering
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    if owner_filter:
        tables = TableInfo.objects.filter(owner=owner_filter).order_by('tbl_no')
    else:
        tables = TableInfo.objects.order_by('tbl_no')
    
    return render(request, 'restaurant/manage_tables.html', {'tables': tables})

@login_required
def add_table(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            # Set owner before saving
            from accounts.models import get_owner_filter
            owner_filter = get_owner_filter(request.user)
            table = form.save(commit=False)
            if owner_filter:
                table.owner = owner_filter
            table.save()
            messages.success(request, 'Table added successfully!')
            return redirect('restaurant:manage_tables')
    else:
        form = TableForm()
    
    return render(request, 'restaurant/add_table.html', {'form': form})


# Happy Hour Management Views
@login_required
def manage_promotions(request):
    """View all Happy Hour promotions for the current owner"""
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    
    if owner_filter:
        promotions = HappyHourPromotion.objects.filter(owner=owner_filter).order_by('-created_at')
    else:
        promotions = HappyHourPromotion.objects.none()
    
    # Calculate real-time statistics for dashboard
    total_promotions = promotions.count()
    active_promotions = promotions.filter(is_active=True).count()
    currently_running = len([p for p in promotions if p.is_currently_active()])
    
    context = {
        'promotions': promotions,
        'total_promotions': total_promotions,
        'active_promotions': active_promotions,
        'currently_running': currently_running,
    }
    
    return render(request, 'restaurant/manage_promotions.html', context)


@login_required
def add_promotion(request):
    """Add a new Happy Hour promotion"""
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    
    if request.method == 'POST':
        form = HappyHourPromotionForm(request.POST, owner=owner_filter)
        if form.is_valid():
            promotion = form.save(commit=False)
            promotion.owner = owner_filter
            promotion.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f'Happy Hour promotion "{promotion.name}" created successfully!')
            return redirect('restaurant:manage_promotions')
    else:
        form = HappyHourPromotionForm(owner=owner_filter)
    
    return render(request, 'restaurant/add_promotion.html', {'form': form})


@login_required
def edit_promotion(request, promotion_id):
    """Edit an existing Happy Hour promotion"""
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    
    promotion = get_object_or_404(HappyHourPromotion, id=promotion_id, owner=owner_filter)
    
    if request.method == 'POST':
        form = HappyHourPromotionForm(request.POST, instance=promotion, owner=owner_filter)
        if form.is_valid():
            form.save()
            messages.success(request, f'Promotion "{promotion.name}" updated successfully!')
            return redirect('restaurant:manage_promotions')
    else:
        form = HappyHourPromotionForm(instance=promotion, owner=owner_filter)
    
    return render(request, 'restaurant/edit_promotion.html', {'form': form, 'promotion': promotion})


@login_required
def delete_promotion(request, promotion_id):
    """Delete a Happy Hour promotion"""
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    
    promotion = get_object_or_404(HappyHourPromotion, id=promotion_id, owner=owner_filter)
    
    if request.method == 'POST':
        promotion_name = promotion.name
        promotion.delete()
        messages.success(request, f'Promotion "{promotion_name}" deleted successfully!')
        return redirect('restaurant:manage_promotions')
    
    return render(request, 'restaurant/delete_promotion.html', {'promotion': promotion})


@login_required 
def toggle_promotion(request, promotion_id):
    """Toggle promotion active/inactive status via AJAX"""
    if not request.user.is_owner():
        return JsonResponse({'success': False, 'message': 'Access denied.'})
    
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    
    try:
        promotion = HappyHourPromotion.objects.get(id=promotion_id, owner=owner_filter)
        promotion.is_active = not promotion.is_active
        promotion.save()
        
        return JsonResponse({
            'success': True,
            'is_active': promotion.is_active,
            'message': f'Promotion {"activated" if promotion.is_active else "deactivated"} successfully!'
        })
    except HappyHourPromotion.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Promotion not found.'})


@login_required
def promotion_preview(request, promotion_id):
    """Preview promotion details and affected products"""
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    from accounts.models import get_owner_filter
    owner_filter = get_owner_filter(request.user)
    
    promotion = get_object_or_404(HappyHourPromotion, id=promotion_id, owner=owner_filter)
    
    # Get all affected products
    from django.db.models import Q
    affected_products = Product.objects.filter(
        Q(pk__in=promotion.products.all()) |
        Q(main_category__in=promotion.main_categories.all()) |
        Q(sub_category__in=promotion.sub_categories.all()),
        main_category__owner=owner_filter
    ).distinct().select_related('main_category', 'sub_category')
    
    context = {
        'promotion': promotion,
        'affected_products': affected_products,
        'affected_count': affected_products.count(),
    }
    
    return render(request, 'restaurant/promotion_preview.html', context)
