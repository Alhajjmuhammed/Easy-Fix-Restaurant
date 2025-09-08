from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from .models import MainCategory, SubCategory, Product, TableInfo
from .forms import ProductForm, MainCategoryForm, SubCategoryForm, TableForm, StaffForm
from orders.models import Order
from accounts.models import User, Role

def home(request):
    return render(request, 'restaurant/home.html')

def menu(request):
    categories = MainCategory.objects.filter(is_active=True).prefetch_related('subcategories__products')
    return render(request, 'restaurant/menu.html', {'categories': categories})

@login_required
def owner_dashboard(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    # Dashboard statistics
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    total_staff = User.objects.exclude(role__name='customer').count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('table_info', 'ordered_by').order_by('-created_at')[:5]
    
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
    
    products = Product.objects.select_related('main_category', 'sub_category').order_by('-created_at')
    return render(request, 'restaurant/manage_products.html', {'products': products})

@login_required
def add_product(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('restaurant:manage_products')
    else:
        form = ProductForm()
    
    return render(request, 'restaurant/add_product.html', {'form': form})

@login_required
def edit_product(request, product_id):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('restaurant:manage_products')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'restaurant/edit_product.html', {'form': form, 'product': product})

@login_required
def delete_product(request, product_id):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    product = get_object_or_404(Product, id=product_id)
    
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
            form.save()
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
            form.save()
            messages.success(request, 'Subcategory added successfully!')
            return redirect('restaurant:manage_categories')
    else:
        form = SubCategoryForm()
    
    return render(request, 'restaurant/add_subcategory.html', {'form': form})

@login_required
def manage_staff(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    staff_members = User.objects.exclude(role__name='customer').select_related('role').order_by('role__name', 'username')
    return render(request, 'restaurant/manage_staff.html', {'staff_members': staff_members})

@login_required
def add_staff(request):
    if not request.user.is_owner():
        messages.error(request, 'Access denied. Owner privileges required.')
        return redirect('restaurant:home')
    
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
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
            form.save()
            messages.success(request, 'Table added successfully!')
            return redirect('restaurant:manage_tables')
    else:
        form = TableForm()
    
    return render(request, 'restaurant/add_table.html', {'form': form})
