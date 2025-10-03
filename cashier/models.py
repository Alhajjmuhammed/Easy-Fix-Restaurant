from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from decimal import Decimal

User = get_user_model()

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('digital', 'Digital Payment'),
        ('voucher', 'Voucher'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    processed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processed_payments')
    reference_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    is_voided = models.BooleanField(default=False)
    voided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='voided_payments')
    void_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def owner(self):
        return self.order.owner
    
    def __str__(self):
        status = " (VOIDED)" if self.is_voided else ""
        return f"Payment ${self.amount} for Order {self.order.order_number}{status}"

class OrderItemPayment(models.Model):
    """Track which specific items were paid for in split bill scenarios"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='item_payments')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity_paid = models.IntegerField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity_paid}x {self.order_item.product.name} - ${self.amount_paid}"

class VoidTransaction(models.Model):
    """Track voided transactions for audit purposes"""
    original_payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    voided_by = models.ForeignKey(User, on_delete=models.CASCADE)
    void_reason = models.TextField()
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    refund_method = models.CharField(max_length=20, choices=Payment.PAYMENT_METHOD_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def owner(self):
        return self.original_payment.owner
    
    def __str__(self):
        return f"Void ${self.refund_amount} for Payment {self.original_payment.id}"