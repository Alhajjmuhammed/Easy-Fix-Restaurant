from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from .forms import UserRegistrationForm, UserLoginForm, OwnerRegistrationForm, CustomerRegistrationForm
from .models import Role, User

@ensure_csrf_cookie
def csrf_debug_view(request):
    return render(request, 'csrf_debug.html')

# Temporary CSRF exemption for login - remove this in production
@csrf_exempt  
def login_view(request):
    if request.user.is_authenticated:
        return redirect('restaurant:home')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                
                # Role-based redirect
                if user.is_administrator():
                    return redirect('system_admin:dashboard')  # Redirect admins to system dashboard
                elif user.is_owner():
                    return redirect('admin_panel:admin_dashboard')  # Owners now use admin panel
                elif user.is_kitchen_staff():
                    return redirect('orders:kitchen_dashboard')
                elif user.is_customer_care():
                    return redirect('orders:customer_care_dashboard')
                elif user.is_cashier():
                    return redirect('cashier:dashboard')
                else:
                    return redirect('restaurant:menu')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    # Only show logout message if user was actually logged in
    if request.user.is_authenticated:
        messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.role = form.cleaned_data['role']
            user.owner = form.cleaned_data['owner']
            user.save()
            
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('accounts:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def register_owner_view(request):
    """Separate registration for restaurant owners"""
    if request.method == 'POST':
        form = OwnerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            # Set role as owner
            owner_role, created = Role.objects.get_or_create(
                name='owner',
                defaults={'description': 'Restaurant Owner'}
            )
            user.role = owner_role
            user.owner = None  # Owners don't have an owner
            user.save()
            
            messages.success(request, f'Owner registration successful for {user.restaurant_name}! You can now log in.')
            return redirect('accounts:login')
    else:
        form = OwnerRegistrationForm()
    
    return render(request, 'accounts/register_owner.html', {'form': form})

@login_required
def profile_view(request):
    """Role-based profile view"""
    user = request.user
    
    # Get user's recent orders for customer care profiles only
    recent_orders = []
    if user.is_customer_care():
        from orders.models import Order
        recent_orders = Order.objects.filter(ordered_by=user).order_by('-created_at')[:5]
    
    # Get staff management data for owner/admin
    staff_users = []
    if user.is_owner() or user.is_administrator():
        staff_users = User.objects.filter(role__name__in=['customer_care', 'kitchen']).select_related('role')
    
    context = {
        'user': user,
        'recent_orders': recent_orders,
        'staff_users': staff_users,
        'restaurant_name': user.get_restaurant_name(request) if user.is_customer() else None,
    }
    
    # Role-based template selection
    if user.is_administrator():
        template = 'accounts/profile_admin.html'
    elif user.is_owner():
        template = 'accounts/profile_owner.html'
    elif user.is_customer_care():
        template = 'accounts/profile_customer_care.html'
    elif user.is_kitchen_staff():
        template = 'accounts/profile_kitchen.html'
    elif user.is_cashier():
        template = 'accounts/profile_cashier.html'
    else:  # customer
        template = 'accounts/profile_customer.html'
    
    return render(request, template, context)

def qr_code_access(request, qr_code):
    """Handle QR code access to restaurant"""
    try:
        # Find restaurant by QR code
        restaurant = User.objects.get(
            restaurant_qr_code=qr_code, 
            role__name='owner', 
            is_active=True
        )
        
        # Store restaurant in session
        request.session['selected_restaurant_id'] = restaurant.id
        request.session['selected_restaurant_name'] = restaurant.restaurant_name
        request.session['access_method'] = 'qr_code'
        
        # If user is not logged in, show restaurant info and prompt for login/register
        if not request.user.is_authenticated:
            return render(request, 'accounts/qr_restaurant_access.html', {
                'restaurant': restaurant,
                'qr_code': qr_code
            })
        
        # If user is already logged in as customer, switch restaurant context and continue
        if request.user.is_customer():
            messages.success(request, f'Welcome to {restaurant.restaurant_name}!')
            return redirect('orders:select_table')
        
        # If user is staff of this restaurant, redirect to appropriate dashboard
        if request.user.get_owner() == restaurant:
            if request.user.is_kitchen_staff():
                return redirect('orders:kitchen_dashboard')
            elif request.user.is_cashier():
                return redirect('cashier:dashboard')
            elif request.user.is_owner():
                return redirect('admin_panel:admin_dashboard')
        
        # Default: redirect to menu
        messages.success(request, f'Welcome to {restaurant.restaurant_name}!')
        return redirect('restaurant:menu')
        
    except User.DoesNotExist:
        messages.error(request, 'Invalid QR code. Restaurant not found.')
        return redirect('accounts:login')


def customer_register_view(request, qr_code):
    """Customer registration specifically for QR code access"""
    try:
        # Get the restaurant from QR code
        restaurant = User.objects.get(
            restaurant_qr_code=qr_code,
            role__name='owner',
            is_active=True
        )
        
        # Store restaurant info in session
        request.session['selected_restaurant_id'] = restaurant.id
        request.session['selected_restaurant_name'] = restaurant.restaurant_name
        request.session['access_method'] = 'qr_code'
        
        if request.method == 'POST':
            form = CustomerRegistrationForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                
                # Set as customer role
                customer_role, created = Role.objects.get_or_create(
                    name='customer',
                    defaults={'description': 'Customer'}
                )
                user.role = customer_role
                user.owner = None  # Universal customer - not tied to specific restaurant
                user.save()
                
                # Auto-login the user
                user = authenticate(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password']
                )
                if user:
                    login(request, user)
                    messages.success(request, f'Welcome to {restaurant.restaurant_name}! Account created successfully.')
                    return redirect('orders:select_table')
                
        else:
            form = CustomerRegistrationForm()
        
        context = {
            'form': form,
            'restaurant': restaurant,
            'qr_code': qr_code
        }
        return render(request, 'accounts/customer_register.html', context)
        
    except User.DoesNotExist:
        messages.error(request, 'Invalid QR code. Restaurant not found.')
        return redirect('accounts:login')
