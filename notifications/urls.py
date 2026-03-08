# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Main views
    path('', views.notification_center_view, name='notification_center'),
    path('preferences/', views.notification_preferences_view, name='notification_preferences'),
    
    # API endpoints
    path('api/', views.get_notifications_api, name='api_notifications'),
    path('api/mark-read/<int:notification_id>/', views.mark_notification_read, name='api_mark_read'),
    path('api/mark-all-read/', views.mark_all_read, name='api_mark_all_read'),
    path('api/archive/<int:notification_id>/', views.archive_notification, name='api_archive'),
    path('api/archive-all-read/', views.archive_all_read, name='api_archive_all_read'),
]