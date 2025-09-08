from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.Model):
    ROLE_CHOICES = [
        ('administrator', 'Administrator'),
        ('owner', 'Owner'),
        ('customer_care', 'Customer Care'),
        ('kitchen', 'Kitchen'),
        ('customer', 'Customer'),
    ]
    
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.get_name_display()

class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    is_active_staff = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} - {self.role.name if self.role else 'No Role'}"
    
    def is_administrator(self):
        return self.role and self.role.name == 'administrator'
    
    def is_owner(self):
        return self.role and self.role.name == 'owner'
    
    def is_customer_care(self):
        return self.role and self.role.name == 'customer_care'
    
    def is_kitchen_staff(self):
        return self.role and self.role.name == 'kitchen'
    
    def is_customer(self):
        return self.role and self.role.name == 'customer'
