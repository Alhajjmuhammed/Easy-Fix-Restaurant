from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['get_subtotal']
    
    def get_subtotal(self, obj):
        return obj.get_subtotal() if obj.id else 0
    get_subtotal.short_description = 'Subtotal'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'table_info', 'ordered_by', 'status', 'total_amount', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at', 'table_info']
    search_fields = ['order_number', 'table_info__tbl_no', 'ordered_by__username']
    readonly_fields = ['order_number', 'total_amount', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    def save_model(self, request, obj, form, change):
        if not obj.order_number:
            # Generate order number
            import uuid
            obj.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save_model(request, obj, form, change)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'unit_price', 'get_subtotal']
    list_filter = ['order__status', 'product__main_category', 'created_at']
    search_fields = ['order__order_number', 'product__name']
