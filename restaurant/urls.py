from django.urls import path
from . import views

app_name = 'restaurant'

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/', views.menu, name='menu'),
    
    # Owner dashboard URLs
    path('owner/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/products/', views.manage_products, name='manage_products'),
    path('owner/products/add/', views.add_product, name='add_product'),
    path('owner/products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('owner/products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('owner/categories/', views.manage_categories, name='manage_categories'),
    path('owner/categories/add/', views.add_category, name='add_category'),
    path('owner/subcategories/add/', views.add_subcategory, name='add_subcategory'),
    path('owner/staff/', views.manage_staff, name='manage_staff'),
    path('owner/staff/add/', views.add_staff, name='add_staff'),
    path('owner/orders/', views.view_orders, name='view_orders'),
    path('owner/tables/', views.manage_tables, name='manage_tables'),
    path('owner/tables/add/', views.add_table, name='add_table'),
]
