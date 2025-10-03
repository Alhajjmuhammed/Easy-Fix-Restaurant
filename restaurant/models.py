from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

class TableInfo(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tables', 
                             limit_choices_to={'role__name': 'owner'}, null=True, blank=True)
    tbl_no = models.CharField(max_length=10)
    capacity = models.IntegerField(default=4)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Table {self.tbl_no} ({self.owner.restaurant_name})"
    
    class Meta:
        verbose_name = "Table Information"
        verbose_name_plural = "Tables Information"
        unique_together = ['owner', 'tbl_no']  # Each owner can have their own table numbering

class MainCategory(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='main_categories',
                             limit_choices_to={'role__name': 'owner'}, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.owner.restaurant_name})"
    
    class Meta:
        verbose_name = "Main Category"
        verbose_name_plural = "Main Categories"
        unique_together = ['owner', 'name']  # Each owner can have their own category names

class SubCategory(models.Model):
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def owner(self):
        return self.main_category.owner
    
    def __str__(self):
        return f"{self.main_category.name} - {self.name} ({self.owner.restaurant_name})"
    
    class Meta:
        verbose_name = "Sub Category"
        verbose_name_plural = "Sub Categories"
        unique_together = ['main_category', 'name']

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE, related_name='products')
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    available_in_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    preparation_time = models.IntegerField(help_text="Time in minutes", default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def owner(self):
        return self.main_category.owner
    
    def __str__(self):
        return f"{self.name} ({self.owner.restaurant_name})"
    
    def is_in_stock(self):
        return self.available_in_stock > 0 and self.is_available
    
    def get_current_price(self):
        """Get current price considering active Happy Hour promotions"""
        from django.utils import timezone
        
        # Get current time in the configured timezone
        now = timezone.localtime(timezone.now())
        current_day = now.weekday() + 1  # Monday=1, Sunday=7
        current_time = now.time()
        
        # Check for active promotions affecting this product
        active_promotions = HappyHourPromotion.objects.filter(
            owner=self.owner,
            is_active=True,
            start_time__lte=current_time,
            end_time__gte=current_time,
            days_of_week__contains=str(current_day)
        ).filter(
            models.Q(products=self) |
            models.Q(main_categories=self.main_category) |
            models.Q(sub_categories=self.sub_category)
        ).order_by('-discount_percentage')  # Get highest discount first
        
        if active_promotions.exists():
            promotion = active_promotions.first()
            discount_amount = self.price * (promotion.discount_percentage / Decimal('100'))
            discounted_price = self.price - discount_amount
            return max(discounted_price, Decimal('0.01'))  # Ensure minimum price
        
        return self.price
    
    def get_active_promotion(self):
        """Get the currently active promotion for this product"""
        from django.utils import timezone
        
        # Get current time in the configured timezone
        now = timezone.localtime(timezone.now())
        current_day = now.weekday() + 1  # Monday=1, Sunday=7
        current_time = now.time()
        
        return HappyHourPromotion.objects.filter(
            owner=self.owner,
            is_active=True,
            start_time__lte=current_time,
            end_time__gte=current_time,
            days_of_week__contains=str(current_day)
        ).filter(
            models.Q(products=self) |
            models.Q(main_categories=self.main_category) |
            models.Q(sub_categories=self.sub_category)
        ).order_by('-discount_percentage').first()
    
    def has_active_promotion(self):
        """Check if product has an active promotion"""
        return self.get_active_promotion() is not None
    
    class Meta:
        ordering = ['name']


class HappyHourPromotion(models.Model):
    DAYS_CHOICES = [
        ('1', 'Monday'),
        ('2', 'Tuesday'),
        ('3', 'Wednesday'),
        ('4', 'Thursday'),
        ('5', 'Friday'),
        ('6', 'Saturday'),
        ('7', 'Sunday'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='happy_hour_promotions',
                             limit_choices_to={'role__name': 'owner'})
    name = models.CharField(max_length=100, help_text="e.g., 'Happy Hour Special', 'Weekend Discount'")
    description = models.TextField(blank=True, help_text="Optional description of the promotion")
    
    # Discount settings
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, 
                                            validators=[MinValueValidator(Decimal('0.01')), 
                                                      MaxValueValidator(Decimal('99.99'))],
                                            help_text="Discount percentage (1-99)")
    
    # Time settings
    start_time = models.TimeField(help_text="Start time for the promotion")
    end_time = models.TimeField(help_text="End time for the promotion")
    days_of_week = models.CharField(max_length=13, help_text="Comma-separated days (1=Mon, 7=Sun), e.g., '1,2,3,4,5' for weekdays")
    
    # Promotion targets - can apply to products, categories, or subcategories
    products = models.ManyToManyField(Product, blank=True, related_name='happy_hour_promotions',
                                     help_text="Specific products for this promotion")
    main_categories = models.ManyToManyField(MainCategory, blank=True, related_name='happy_hour_promotions',
                                           help_text="Main categories for this promotion")
    sub_categories = models.ManyToManyField(SubCategory, blank=True, related_name='happy_hour_promotions',
                                          help_text="Sub categories for this promotion")
    
    # Status and metadata
    is_active = models.BooleanField(default=True, help_text="Enable/disable this promotion")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.discount_percentage}% ({self.owner.restaurant_name})"
    
    def get_days_display(self):
        """Return human-readable days"""
        day_names = {
            '1': 'Mon', '2': 'Tue', '3': 'Wed', '4': 'Thu',
            '5': 'Fri', '6': 'Sat', '7': 'Sun'
        }
        if self.days_of_week:
            days = self.days_of_week.split(',')
            return ', '.join([day_names.get(day.strip(), day.strip()) for day in days])
        return 'No days selected'
    
    def is_currently_active(self):
        """Check if promotion is currently active based on time and day"""
        if not self.is_active:
            return False
            
        from django.utils import timezone
        
        # Get current time in the configured timezone
        now = timezone.localtime(timezone.now())
        current_day = str(now.weekday() + 1)  # Monday=1, Sunday=7
        current_time = now.time()
        
        # Check if current day is in promotion days
        if current_day not in self.days_of_week.split(','):
            return False
        
        # Check if current time is within promotion hours
        if self.start_time <= self.end_time:
            # Normal case: start_time < end_time (same day)
            return self.start_time <= current_time <= self.end_time
        else:
            # Cross-midnight case: start_time > end_time
            return current_time >= self.start_time or current_time <= self.end_time
    
    def get_affected_products_count(self):
        """Get count of products affected by this promotion"""
        from django.db.models import Q
        
        # Products directly selected
        direct_products = self.products.count()
        
        # Products from selected main categories
        category_products = Product.objects.filter(main_category__in=self.main_categories.all()).count()
        
        # Products from selected sub categories
        subcategory_products = Product.objects.filter(sub_category__in=self.sub_categories.all()).count()
        
        # Use Q objects to avoid double counting
        total_products = Product.objects.filter(
            Q(pk__in=self.products.all()) |
            Q(main_category__in=self.main_categories.all()) |
            Q(sub_category__in=self.sub_categories.all()),
            main_category__owner=self.owner
        ).distinct().count()
        
        return total_products
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Happy Hour Promotion"
        verbose_name_plural = "Happy Hour Promotions"
