from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta


def get_owner_filter(user):
    """
    Get the owner filter for the current user.
    Returns the owner instance that should be used for filtering data.
    """
    if user.is_administrator():
        return None  # Administrators can see all data
    elif user.is_owner():
        return user  # Owners see their own data
    elif user.owner:
        return user.owner  # Staff/customers see their owner's data
    else:
        raise PermissionDenied("User is not associated with any owner.")


def check_owner_permission(user, obj):
    """
    Check if the user has permission to access the given object.
    Object must have an 'owner' property or method.
    """
    if user.is_administrator():
        return True
    
    obj_owner = obj.owner if hasattr(obj, 'owner') else obj.get_owner()
    user_owner = get_owner_filter(user)
    
    return obj_owner == user_owner

class Role(models.Model):
    ROLE_CHOICES = [
        ('administrator', 'Administrator'),
        ('owner', 'Owner'),
        ('customer_care', 'Customer Care'),
        ('kitchen', 'Kitchen'),
        ('bar', 'Bar'),
        ('cashier', 'Cashier'),
        ('customer', 'Customer'),
    ]
    
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.get_name_display()

class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    # Owner relationship - customers and staff belong to an owner
    owner = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                             related_name='owned_users', limit_choices_to={'role__name': 'owner'})
    # Restaurant information for owners
    restaurant_name = models.CharField(max_length=200, blank=True, 
                                     help_text="Name of the restaurant (for owners only)")
    restaurant_description = models.TextField(blank=True,
                                            help_text="Description of the restaurant (for owners only)")
    # QR Code for restaurant identification
    restaurant_qr_code = models.CharField(max_length=50, unique=True, blank=True, null=True,
                                        help_text="Unique QR code for restaurant access")
    # Tax configuration for restaurant owners
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.0800'), 
                                 help_text="Tax rate as decimal (e.g., 0.0800 for 8%, 0.0500 for 5%)")
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    is_active_staff = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.is_owner():
            return f"{self.username} - {self.role.name if self.role else 'No Role'} ({self.restaurant_name or 'No Restaurant'})"
        return f"{self.username} - {self.role.name if self.role else 'No Role'}"
    
    def is_administrator(self):
        return self.role and self.role.name == 'administrator'
    
    def is_owner(self):
        return self.role and self.role.name == 'owner'
    
    def is_customer_care(self):
        return self.role and self.role.name == 'customer_care'
    
    def is_kitchen_staff(self):
        return self.role and self.role.name == 'kitchen'
    
    def is_bar_staff(self):
        return self.role and self.role.name == 'bar'
    
    def is_cashier(self):
        return self.role and self.role.name == 'cashier'
    
    def is_customer(self):
        return self.role and self.role.name == 'customer'
    
    def get_owner(self):
        """Get the owner this user belongs to"""
        if self.is_owner():
            return self
        return self.owner
    
    def get_restaurant_name(self, request=None):
        """Get the restaurant name for this user's owner or current session restaurant"""
        if self.is_customer():
            # For universal customers, try to get restaurant from session
            if request and hasattr(request, 'session'):
                restaurant_name = request.session.get('selected_restaurant_name')
                if restaurant_name:
                    return restaurant_name
            
            # Fallback: if customer has an owner (old system), use it
            if self.owner:
                return self.owner.restaurant_name
            
            # Default fallback
            return "Restaurant"
        
        # For staff/owners, use the traditional method
        owner = self.get_owner()
        return owner.restaurant_name if owner else "Unknown Restaurant"
    
    def get_tax_rate(self):
        """Get the tax rate for this user's restaurant owner"""
        owner = self.get_owner()
        return owner.tax_rate if owner else Decimal('0.0800')
    
    def get_tax_rate_percentage(self):
        """Get the tax rate as percentage for display (e.g., 8.0 for 8%)"""
        return float(self.get_tax_rate() * 100)
    
    def generate_qr_code(self):
        """Generate unique QR code for restaurant"""
        import uuid
        if self.is_owner() and not self.restaurant_qr_code:
            self.restaurant_qr_code = f"REST-{uuid.uuid4().hex[:12].upper()}"
            return self.restaurant_qr_code
        return self.restaurant_qr_code
    
    def get_qr_url(self, request=None):
        """Get the URL for QR code access"""
        if self.restaurant_qr_code:
            if request:
                base_url = request.build_absolute_uri('/')
                return f"{base_url}r/{self.restaurant_qr_code}/"
            else:
                # Use production domain as fallback
                return f"https://easyfixsoft.com/r/{self.restaurant_qr_code}/"
        return None
    
    def save(self, *args, **kwargs):
        # Owners don't have an owner (they are the owner)
        if self.is_owner():
            self.owner = None
            # Generate QR code if not exists
            if not self.restaurant_qr_code:
                self.generate_qr_code()
        super().save(*args, **kwargs)


class RestaurantSubscription(models.Model):
    """
    SaaS Subscription Management Model
    Manages restaurant subscription periods, blocking, and access control
    """
    
    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'), 
        ('blocked', 'Blocked by Admin'),
        ('cancelled', 'Cancelled'),
    ]
    
    SUBSCRIPTION_PLAN_CHOICES = [
        ('trial', 'Trial (7 days)'),
        ('basic', 'Basic (Monthly)'),
        ('premium', 'Premium (Monthly)'),
        ('enterprise', 'Enterprise (Yearly)'),
        ('custom', 'Custom Plan'),
    ]
    
    # Core subscription fields
    restaurant_owner = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='subscription',
        limit_choices_to={'role__name': 'owner'}
    )
    
    # Subscription period management
    subscription_start_date = models.DateField(
        help_text="When the subscription becomes active"
    )
    subscription_end_date = models.DateField(
        help_text="When the subscription expires"
    )
    
    # Subscription details
    subscription_plan = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_PLAN_CHOICES,
        default='trial'
    )
    
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='active'
    )
    
    # Access control
    is_blocked_by_admin = models.BooleanField(
        default=False,
        help_text="Manually blocked by system administrator"
    )
    
    block_reason = models.TextField(
        blank=True,
        help_text="Reason for blocking (if blocked by admin)"
    )
    
    # Grace period management
    grace_period_days = models.PositiveIntegerField(
        default=7,
        help_text="Grace period after expiration before full blocking"
    )
    
    # Financial tracking
    monthly_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('29.99'),
        help_text="Monthly subscription fee"
    )
    
    last_payment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last successful payment"
    )
    
    next_billing_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next billing cycle date"
    )
    
    # Notification tracking
    expiration_warning_sent = models.BooleanField(
        default=False,
        help_text="Whether expiration warning has been sent"
    )
    
    warning_sent_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when expiration warning was sent"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_subscriptions',
        limit_choices_to={'role__name': 'administrator'}
    )
    
    class Meta:
        verbose_name = "Restaurant Subscription"
        verbose_name_plural = "Restaurant Subscriptions"
        ordering = ['-created_at']
    
    def __str__(self):
        restaurant_name = self.restaurant_owner.restaurant_name or self.restaurant_owner.username
        return f"{restaurant_name} - {self.subscription_plan} ({self.subscription_status})"
    
    @property
    def is_active(self):
        """Check if subscription is currently active"""
        today = date.today()
        
        # Check if blocked by admin
        if self.is_blocked_by_admin:
            return False
        
        # Check if status is active
        if self.subscription_status != 'active':
            return False
        
        # Check if within subscription period
        if today < self.subscription_start_date:
            return False
        
        # Check if expired (considering grace period)
        grace_end_date = self.subscription_end_date + timedelta(days=self.grace_period_days)
        if today > grace_end_date:
            return False
        
        return True
    
    @property
    def is_in_grace_period(self):
        """Check if subscription is in grace period after expiration"""
        today = date.today()
        grace_end_date = self.subscription_end_date + timedelta(days=self.grace_period_days)
        
        return (
            today > self.subscription_end_date and 
            today <= grace_end_date and 
            self.subscription_status == 'active' and
            not self.is_blocked_by_admin
        )
    
    @property
    def days_until_expiration(self):
        """Get number of days until subscription expires (negative if overdue)"""
        today = date.today()
        return (self.subscription_end_date - today).days
    
    @property
    def days_in_grace_period(self):
        """Get number of days remaining in grace period"""
        if not self.is_in_grace_period:
            return 0
        
        today = date.today()
        grace_end_date = self.subscription_end_date + timedelta(days=self.grace_period_days)
        return (grace_end_date - today).days
    
    def extend_subscription(self, days=30, extend_by_admin=False):
        """Extend subscription by specified days"""
        self.subscription_end_date += timedelta(days=days)
        
        if extend_by_admin:
            self.subscription_status = 'active'
            self.is_blocked_by_admin = False
            
        # Update next billing date
        if self.next_billing_date:
            self.next_billing_date += timedelta(days=days)
        
        self.save()
    
    def block_restaurant(self, reason="Blocked by administrator", blocked_by=None):
        """Block restaurant access"""
        self.is_blocked_by_admin = True
        self.block_reason = reason
        self.subscription_status = 'blocked'
        
        # Block all related users
        self.restaurant_owner.is_active = False
        self.restaurant_owner.save()
        
        # Block all staff under this owner
        staff_users = self.restaurant_owner.owned_users.all()
        staff_users.update(is_active=False)
        
        self.save()
        
        # Log the action
        SubscriptionLog.objects.create(
            subscription=self,
            action='blocked',
            description=f"Restaurant blocked: {reason}",
            old_status=self.subscription_status,
            new_status='blocked',
            performed_by=blocked_by
        )
    
    def unblock_restaurant(self, unblocked_by=None):
        """Unblock restaurant access"""
        old_status = self.subscription_status
        
        self.is_blocked_by_admin = False
        self.block_reason = ""
        
        # Admin can unblock regardless of subscription period validity
        # If subscription period is valid, make it active; otherwise keep current status
        if self.is_subscription_period_valid():
            self.subscription_status = 'active'
        
        # Always reactivate users when admin unblocks (admin override)
        # Unblock owner
        self.restaurant_owner.is_active = True
        self.restaurant_owner.save()
        
        # Unblock all staff under this owner
        staff_users = self.restaurant_owner.owned_users.all()
        staff_users.update(is_active=True)
        
        self.save()
        
        # Log the action
        SubscriptionLog.objects.create(
            subscription=self,
            action='unblocked',
            description="Restaurant unblocked by administrator",
            old_status=old_status,
            new_status=self.subscription_status,
            performed_by=unblocked_by
        )
    
    def is_subscription_period_valid(self):
        """Check if subscription period is valid (ignoring block status)"""
        today = date.today()
        grace_end_date = self.subscription_end_date + timedelta(days=self.grace_period_days)
        
        return (
            self.subscription_start_date <= today <= grace_end_date and
            self.subscription_status in ['active', 'blocked']
        )
    
    def update_subscription_status(self):
        """Update subscription status based on current date"""
        today = date.today()
        old_status = self.subscription_status
        
        # Don't change status if blocked by admin
        if self.is_blocked_by_admin:
            return
        
        # Check if subscription hasn't started yet
        if today < self.subscription_start_date:
            # Keep current status if before start date
            return
        
        # Check if subscription has expired
        if today > self.subscription_end_date:
            grace_end_date = self.subscription_end_date + timedelta(days=self.grace_period_days)
            
            if today > grace_end_date:
                # Fully expired, block access
                self.subscription_status = 'expired'
                self.restaurant_owner.is_active = False
                self.restaurant_owner.save()
                
                # Block all staff
                staff_users = self.restaurant_owner.owned_users.all()
                staff_users.update(is_active=False)
                
                self.save()
                
                # Log the expiration
                SubscriptionLog.objects.create(
                    subscription=self,
                    action='expired',
                    description="Subscription expired and access blocked",
                    old_status=old_status,
                    new_status='expired'
                )
            # else: in grace period, keep status as 'active'
        
    def get_subscription_info(self):
        """Get comprehensive subscription information"""
        today = date.today()
        
        info = {
            'restaurant_name': self.restaurant_owner.restaurant_name or self.restaurant_owner.username,
            'plan': self.get_subscription_plan_display(),
            'status': self.get_subscription_status_display(),
            'start_date': self.subscription_start_date,
            'end_date': self.subscription_end_date,
            'is_active': self.is_active,
            'is_blocked': self.is_blocked_by_admin,
            'block_reason': self.block_reason,
            'days_until_expiration': self.days_until_expiration,
            'is_in_grace_period': self.is_in_grace_period,
            'days_in_grace_period': self.days_in_grace_period,
            'monthly_fee': self.monthly_fee,
            'last_payment_date': self.last_payment_date,
            'next_billing_date': self.next_billing_date,
        }
        
        return info


class SubscriptionLog(models.Model):
    """
    Audit log for subscription changes
    """
    
    ACTION_CHOICES = [
        ('created', 'Subscription Created'),
        ('extended', 'Subscription Extended'),
        ('blocked', 'Restaurant Blocked'),
        ('unblocked', 'Restaurant Unblocked'),
        ('expired', 'Subscription Expired'),
        ('renewed', 'Subscription Renewed'),
        ('cancelled', 'Subscription Cancelled'),
        ('plan_changed', 'Plan Changed'),
    ]
    
    subscription = models.ForeignKey(
        RestaurantSubscription,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    
    # Change details
    old_end_date = models.DateField(null=True, blank=True)
    new_end_date = models.DateField(null=True, blank=True)
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    
    # Audit fields
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__name': 'administrator'}
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Subscription Log"
        verbose_name_plural = "Subscription Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscription} - {self.get_action_display()}"
