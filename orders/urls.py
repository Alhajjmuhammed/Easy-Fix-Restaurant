from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('create/', views.create_order, name='create_order'),
    
    # Customer ordering flow
    path('table/', views.select_table, name='select_table'),
    path('menu/', views.browse_menu, name='browse_menu'),
    path('cart/', views.view_cart, name='view_cart'),
    path('place-order/', views.place_order, name='place_order'),
    path('confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    # Cart management (AJAX)
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/', views.update_cart_quantity, name='update_cart_quantity'),
    
    # Customer order management
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('receipt/<int:order_id>/', views.view_receipt, name='view_receipt'),
    path('track/<str:order_number>/', views.track_order, name='track_order'),
    path('customer-cancel/<int:order_id>/', views.customer_cancel_order, name='customer_cancel_order'),
    
    # Kitchen management
    path('kitchen/', views.kitchen_dashboard, name='kitchen_dashboard'),
    path('kitchen/order/<int:order_id>/', views.kitchen_order_detail, name='kitchen_order_detail'),
    path('confirm-order/<int:order_id>/', views.confirm_order, name='confirm_order'),
    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    
    # Customer care management
    path('customer-care/', views.customer_care_dashboard, name='customer_care_dashboard'),
    path('customer-care/payments/', views.customer_care_payments, name='customer_care_payments'),
    path('customer-care/receipt/<int:payment_id>/', views.customer_care_receipt, name='customer_care_receipt'),
    path('customer-care/reprint/<int:payment_id>/', views.customer_care_reprint_receipt, name='customer_care_reprint_receipt'),
    path('customer-care/receipts/', views.customer_care_receipt_management, name='customer_care_receipt_management'),
]
