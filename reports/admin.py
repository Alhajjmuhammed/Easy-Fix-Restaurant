from django.contrib import admin
from .models import SalesReport, ProductSalesDetail, CashierPerformance, HourlyBreakdown


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'period_type', 'date_from', 'date_to', 'total_revenue', 'total_orders', 'generated_at', 'owner')
    list_filter = ('report_type', 'period_type', 'generated_at', 'owner')
    search_fields = ('owner__restaurant_name', 'category__name', 'subcategory__name')
    readonly_fields = ('generated_at', 'generated_by')
    date_hierarchy = 'generated_at'
    
    fieldsets = (
        ('Report Information', {
            'fields': ('report_type', 'period_type', 'date_from', 'date_to', 'owner')
        }),
        ('Category Filters', {
            'fields': ('category', 'subcategory'),
            'classes': ('collapse',)
        }),
        ('Sales Metrics', {
            'fields': ('total_revenue', 'total_orders', 'total_items_sold', 'average_order_value')
        }),
        ('Payment Breakdown', {
            'fields': ('cash_payments', 'card_payments', 'digital_payments', 'voucher_payments'),
            'classes': ('collapse',)
        }),
        ('Discounts & Tax', {
            'fields': ('total_discounts', 'discount_percentage', 'total_tax'),
            'classes': ('collapse',)
        }),
        ('Generation Info', {
            'fields': ('generated_at', 'generated_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductSalesDetail)
class ProductSalesDetailAdmin(admin.ModelAdmin):
    list_display = ('product', 'report', 'quantity_sold', 'total_revenue', 'average_price')
    list_filter = ('report__report_type', 'report__period_type', 'product__main_category')
    search_fields = ('product__name', 'report__owner__restaurant_name')
    ordering = ('-quantity_sold', '-total_revenue')


@admin.register(CashierPerformance)
class CashierPerformanceAdmin(admin.ModelAdmin):
    list_display = ('cashier', 'report', 'orders_processed', 'total_sales', 'average_order_value')
    list_filter = ('report__report_type', 'report__period_type', 'cashier')
    search_fields = ('cashier__first_name', 'cashier__last_name', 'report__owner__restaurant_name')
    ordering = ('-total_sales', '-orders_processed')


@admin.register(HourlyBreakdown)
class HourlyBreakdownAdmin(admin.ModelAdmin):
    list_display = ('report', 'hour', 'orders_count', 'revenue')
    list_filter = ('report__report_type', 'report__period_type', 'hour')
    search_fields = ('report__owner__restaurant_name',)
    ordering = ('report', 'hour')