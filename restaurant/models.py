from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class TableInfo(models.Model):
    tbl_no = models.CharField(max_length=10, unique=True)
    capacity = models.IntegerField(default=4)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Table {self.tbl_no}"
    
    class Meta:
        verbose_name = "Table Information"
        verbose_name_plural = "Tables Information"

class MainCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Main Category"
        verbose_name_plural = "Main Categories"

class SubCategory(models.Model):
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.main_category.name} - {self.name}"
    
    class Meta:
        verbose_name = "Sub Category"
        verbose_name_plural = "Sub Categories"
        unique_together = ['main_category', 'name']

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE, related_name='products')
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    available_in_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    preparation_time = models.IntegerField(help_text="Time in minutes", default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def is_in_stock(self):
        return self.available_in_stock > 0 and self.is_available
    
    class Meta:
        ordering = ['name']
