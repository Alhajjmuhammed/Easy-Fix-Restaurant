from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from orders.models import Order, OrderItem
from restaurant.models import Product

User = get_user_model()


class FoodWasteLog(models.Model):
    """Track all food waste incidents for comprehensive reporting"""
    
    WASTE_REASON_CHOICES = [
        ('customer_refused', 'Customer Refused'),
        ('customer_left', 'Customer Left Before Pickup'),
        ('wrong_order', 'Wrong Order Made'),
        ('quality_issue', 'Quality Issue'),
        ('kitchen_error', 'Kitchen Error'),
        ('overcooking', 'Overcooking'),
        ('undercooking', 'Undercooking'),
        ('contamination', 'Food Contamination'),
        ('equipment_failure', 'Equipment Failure'),
        ('ingredient_expired', 'Expired Ingredients'),
        ('staff_error', 'Staff Error'),
        ('customer_complaint', 'Customer Complaint'),
        ('other', 'Other Reason'),
    ]
    
    DISPOSAL_METHOD_CHOICES = [
        ('waste_bin', 'Waste Bin'),
        ('staff_meal', 'Staff Meal'),
        ('compost', 'Compost'),
        ('donated', 'Donated'),
        ('returned_supplier', 'Returned to Supplier'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='waste_logs', null=True, blank=True)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='waste_logs', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='waste_logs')
    quantity_wasted = models.IntegerField()
    
    # Cost breakdown
    ingredient_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    overhead_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Waste details
    waste_reason = models.CharField(max_length=50, choices=WASTE_REASON_CHOICES)
    disposal_method = models.CharField(max_length=50, choices=DISPOSAL_METHOD_CHOICES, default='waste_bin')
    notes = models.TextField(blank=True)
    
    # Tracking
    recorded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waste_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Restaurant relationship
    @property
    def owner(self):
        if self.order:
            return self.order.table_info.owner
        return self.product.owner
    
    def calculate_costs(self):
        """Calculate costs based on product cost settings or default percentages"""
        try:
            # Try to get product-specific cost settings
            cost_settings = self.product.cost_settings
            self.ingredient_cost = cost_settings.ingredient_cost_per_unit * self.quantity_wasted
            self.labor_cost = cost_settings.labor_cost_per_unit * self.quantity_wasted
            self.overhead_cost = cost_settings.overhead_cost_per_unit * self.quantity_wasted
        except ProductCostSettings.DoesNotExist:
            # Fall back to percentage-based calculation
            base_price = self.product.price
            # Default percentages if no cost settings exist
            ingredient_pct = Decimal('30.0')  # 30%
            labor_pct = Decimal('25.0')       # 25%
            overhead_pct = Decimal('15.0')    # 15%
            
            self.ingredient_cost = (base_price * ingredient_pct / 100) * self.quantity_wasted
            self.labor_cost = (base_price * labor_pct / 100) * self.quantity_wasted
            self.overhead_cost = (base_price * overhead_pct / 100) * self.quantity_wasted
        
        self.total_cost = self.ingredient_cost + self.labor_cost + self.overhead_cost
    
    def save(self, *args, **kwargs):
        # Auto-calculate costs if not manually set
        if self.total_cost == Decimal('0.00'):
            self.calculate_costs()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['waste_reason']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"Waste: {self.quantity_wasted}x {self.product.name} - ${self.total_cost} ({self.get_waste_reason_display()})"


class OrderCostBreakdown(models.Model):
    """Track detailed cost breakdown for each order"""
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='cost_breakdown')
    
    # Revenue
    menu_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    taxes = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Costs
    ingredient_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    overhead_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Profit analysis
    gross_profit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    profit_margin_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_profit(self):
        """Calculate profit metrics"""
        self.total_revenue = self.menu_price + self.taxes + self.service_charge
        self.total_cost = self.ingredient_cost + self.labor_cost + self.overhead_cost
        self.gross_profit = self.total_revenue - self.total_cost
        
        if self.total_revenue > 0:
            self.profit_margin_percentage = (self.gross_profit / self.total_revenue) * 100
        else:
            self.profit_margin_percentage = Decimal('0.00')
    
    def save(self, *args, **kwargs):
        self.calculate_profit()
        super().save(*args, **kwargs)
    
    @property
    def owner(self):
        return self.order.table_info.owner
    
    def __str__(self):
        return f"Cost Breakdown: {self.order.order_number} - Profit: ${self.gross_profit} ({self.profit_margin_percentage}%)"


class WasteReportSummary(models.Model):
    """Daily/Weekly/Monthly waste summary for quick reporting"""
    
    PERIOD_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waste_summaries')
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Totals
    total_items_wasted = models.IntegerField(default=0)
    total_waste_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_revenue_lost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Breakdown by reason
    customer_refused_count = models.IntegerField(default=0)
    customer_refused_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    kitchen_error_count = models.IntegerField(default=0)
    kitchen_error_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    quality_issue_count = models.IntegerField(default=0)
    quality_issue_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    other_waste_count = models.IntegerField(default=0)
    other_waste_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['owner', 'period_type', 'period_start']]
        ordering = ['-period_start']
    
    def __str__(self):
        return f"Waste Summary: {self.owner.restaurant_name} - {self.period_type} {self.period_start}"


class ProductCostSettings(models.Model):
    """Store cost settings for products to calculate waste costs"""
    
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='cost_settings')
    
    # Cost per unit
    ingredient_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    labor_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    overhead_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Labor time (in minutes)
    preparation_time_minutes = models.IntegerField(default=0)
    cooking_time_minutes = models.IntegerField(default=0)
    
    # Overhead allocation
    equipment_cost_allocation = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    utility_cost_allocation = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_cost_per_unit(self):
        return self.ingredient_cost_per_unit + self.labor_cost_per_unit + self.overhead_cost_per_unit
    
    @property
    def owner(self):
        return self.product.owner
    
    def __str__(self):
        return f"Cost Settings: {self.product.name} - ${self.total_cost_per_unit}/unit"