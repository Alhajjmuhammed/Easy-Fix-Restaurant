from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import PermissionDenied


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
