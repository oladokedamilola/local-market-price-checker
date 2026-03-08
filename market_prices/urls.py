# market_prices/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views
from notifications import views as notification_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')), 
    path('accounts/', include('accounts.urls')),  # Accounts app
    path('accounts/', include('allauth.urls')),
    path('market/', include('market.urls')),  # Market app
    path('notifications/', include('notifications.urls')),  # Notifications app
    path('vendor/', include('vendor.urls')),  # Vendor app
    
    # Notification API endpoints
    path('api/', notification_views.get_notifications_api, name='api_notifications'),
    path('api/mark-read/<int:notification_id>/', notification_views.mark_notification_read, name='api_mark_read'),
    path('api/mark-all-read/', notification_views.mark_all_read, name='api_mark_all_read'),
    path('api/archive/<int:notification_id>/', notification_views.archive_notification, name='api_archive'),
    path('api/archive-all-read/', notification_views.archive_all_read, name='api_archive_all_read'),    
    path('api/pending-vendors-count/', notification_views.pending_vendors_count_api, name='pending_vendors_count'),
    
    
    # Resources Pages
    path('how-to-use/', core_views.how_to_use_view, name='how_to_use'),
    path('vendor-guidelines/', core_views.vendor_guidelines_view, name='vendor_guidelines'),
    path('price-update-policy/', core_views.price_update_policy_view, name='price_update_policy'),
    path('faq/', core_views.faq_view, name='faq'),
    
    # Legal Pages
    path('privacy-policy/', core_views.privacy_policy_view, name='privacy_policy'),
    path('terms-of-service/', core_views.terms_of_service_view, name='terms_of_service'),
    path('cookie-policy/', core_views.cookie_policy_view, name='cookie_policy'),
    path('contact-us/', core_views.contact_us_view, name='contact_us'),
    path('api/cookie-consent/', core_views.cookie_consent_api, name='cookie_consent_api'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Error handlers
handler404 = core_views.handler404
handler500 = core_views.handler500
handler403 = core_views.handler403
handler400 = core_views.handler400