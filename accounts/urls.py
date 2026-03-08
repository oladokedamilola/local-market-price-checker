# accounts/urls.py
from django.urls import path
from .views import auth_views, general_views, consumer_views, vendor_views, admin_views

urlpatterns = [
    # Authentication
    path('register/', auth_views.register_view, name='register'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    
    # Email Verification
    path('verify-email/<uuid:token>/', auth_views.verify_email_view, name='verify_email'),
    path('resend-verification/', auth_views.resend_verification_view, name='resend_verification'),
    path('pending-verification/', auth_views.pending_verification_view, name='pending_verification'),  
    path('social/complete/', auth_views.social_complete_profile_view, name='social_complete_profile'),  
    path('inactive/', auth_views.custom_account_inactive_view, name='account_inactive'),    
    
    # Password Reset
    path('password-reset/', auth_views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/<uuid:token>/', auth_views.password_reset_confirm_view, name='password_reset_confirm'),
    path('password-change/', auth_views.password_change_view, name='password_change'),
    
    # Profile & Dashboard
    path('profile/', general_views.profile_view, name='profile'),
    path('upload-profile-picture/', general_views.upload_profile_picture, name='upload_profile_picture'),
    path('dashboard/', general_views.dashboard_view, name='dashboard'),
    
    # Role-specific dashboards
    path('dashboard/vendor/', vendor_views.vendor_dashboard_view, name='vendor_dashboard'),
    path('dashboard/consumer/', consumer_views.consumer_dashboard_view, name='consumer_dashboard'),
    path('dashboard/admin/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    
    
    # Vendor Specific
    path('vendor/kyc/', vendor_views.vendor_kyc_view, name='vendor_kyc'),
    path('kyc-terms/', vendor_views.kyc_terms_view, name='kyc_terms'),
    path('vendor/kyc/pending/', vendor_views.vendor_kyc_pending_view, name='vendor_kyc_pending'),
    path('vendor/kyc/rejected/', vendor_views.vendor_kyc_rejected_view, name='vendor_kyc_rejected'),
    
    # ===== ADMIN MANAGEMENT URLS =====
    # User Management
    path('admin/users/', admin_views.admin_users_view, name='admin_users'),
    path('admin/users/<int:user_id>/', admin_views.admin_user_detail_view, name='admin_user_detail'),
    
    # Vendor Verification
    path('admin/vendor-verification/', admin_views.admin_vendor_verification_view, name='admin_vendor_verification'),
    path('admin/vendor-verification/<int:kyc_id>/', admin_views.admin_verify_vendor, name='admin_verify_vendor'),
    path('admin/rejected-kyc/', admin_views.admin_rejected_kyc_view, name='admin_rejected_kyc'),
    
    # Vendor Products
    path('admin/vendor-products/', admin_views.admin_vendor_products_view, name='admin_vendor_products'),
    path('admin/vendor-products/<int:product_id>/', admin_views.admin_vendor_product_detail_view, name='admin_vendor_product_detail'),
    
    # Consumer Management
    path('admin/consumers/', admin_views.admin_consumers_view, name='admin_consumers'),
    
    # Market Management
    path('admin/markets/', admin_views.admin_markets_view, name='admin_markets'),
    path('admin/markets/create/', admin_views.admin_market_create_view, name='admin_market_create'),
    path('admin/markets/<int:market_id>/', admin_views.admin_market_detail_view, name='admin_market_detail'),
    path('admin/markets/<int:market_id>/update/', admin_views.admin_market_update_view, name='admin_market_update'),
    path('admin/markets/<int:market_id>/delete/', admin_views.admin_market_delete_view, name='admin_market_delete'),
    
    # Categories
    path('admin/categories/', admin_views.admin_categories_view, name='admin_categories'),
    path('admin/categories/create/', admin_views.admin_category_create_view, name='admin_category_create'),
    path('admin/categories/<int:category_id>/update/', admin_views.admin_category_update_view, name='admin_category_update'),
    path('admin/categories/<int:category_id>/delete/', admin_views.admin_category_delete_view, name='admin_category_delete'),
    
    # Category Request Management
    path('admin/category-requests/', admin_views.admin_category_requests_view, name='admin_category_requests'),
    path('admin/category-requests/<int:request_id>/', admin_views.admin_category_request_detail_view, name='admin_category_request_detail'),
    path('admin/category-requests/<int:request_id>/process/', admin_views.admin_process_category_request, name='admin_process_category_request'),
    path('admin/category-requests/bulk-process/', admin_views.admin_bulk_process_category_requests, name='admin_bulk_category_requests'),
    
    # Reports
    path('admin/reports/', admin_views.admin_reports_view, name='admin_reports'),
    
    # AJAX endpoints
    path('check-username/', auth_views.check_username, name='check_username'),
    path('check-email/', auth_views.check_email, name='check_email'),
]