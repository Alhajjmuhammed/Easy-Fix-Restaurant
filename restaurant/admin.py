from django.contrib import admin
from .models import TableInfo, MainCategory, SubCategory, Product

@admin.register(TableInfo)
class TableInfoAdmin(admin.ModelAdmin):
    list_display = ['tbl_no', 'capacity', 'is_available', 'created_at']
    list_filter = ['is_available', 'capacity', 'created_at']
    search_fields = ['tbl_no']

@admin.register(MainCategory)
class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'main_category', 'is_active', 'created_at']
    list_filter = ['main_category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'main_category__name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'main_category', 'sub_category', 'price', 'available_in_stock', 'is_available']
    list_filter = ['main_category', 'sub_category', 'is_available', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'available_in_stock', 'is_available']
