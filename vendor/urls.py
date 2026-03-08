# vendor/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Analytics and Product List
    path('analytics/', views.vendor_analytics_view, name='vendor_analytics'),
    path('products/', views.product_list_view, name='product_list'),
    path('products/<int:pk>/', views.product_detail_view, name='product_detail'),
    
    # Product Management
    path('add/', views.add_product, name='add_product'),
    path('edit/<int:pk>/', views.update_product, name='update_product'),
    path('delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('duplicate/<int:pk>/', views.duplicate_product_view, name='duplicate_product'),
    
    # Category Management
    path('request-category/', views.request_category, name='request_category'),
    
    # Bulk Operations
    path('bulk-update/', views.bulk_price_update_view, name='bulk_price_update'),
    path('export/', views.export_products_view, name='export_products'),
    
    # Alerts and Notifications
    path('stale-products/', views.low_stock_alert_view, name='stale_products'),
    
    # Legacy URL (for backward compatibility)
    path('pending/', views.vendor_dashboard, name='vendor_pending'),
]