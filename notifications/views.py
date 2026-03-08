# notifications/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import Notification, NotificationPreference

@login_required
def notification_center_view(request):
    """
    Main notification center page
    """
    # Get filter from query params
    filter_type = request.GET.get('filter', 'all')
    
    # Base queryset
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_archived=False
    )
    
    # Apply filters
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type == 'read':
        notifications = notifications.filter(is_read=True)
    elif filter_type == 'admin':
        notifications = notifications.filter(notification_type__startswith='admin')
    elif filter_type == 'vendor':
        notifications = notifications.filter(notification_type__startswith='vendor')
    elif filter_type == 'consumer':
        notifications = notifications.filter(notification_type__startswith='consumer')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total': Notification.objects.filter(recipient=request.user, is_archived=False).count(),
        'unread': Notification.objects.filter(recipient=request.user, is_read=False, is_archived=False).count(),
        'read': Notification.objects.filter(recipient=request.user, is_read=True, is_archived=False).count(),
    }
    
    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'filter_type': filter_type,
    }
    
    return render(request, 'notifications/notification_center.html', context)


@login_required
def get_notifications_api(request):
    """
    AJAX endpoint to get notifications
    """
    limit = int(request.GET.get('limit', 10))
    include_read = request.GET.get('include_read', 'false').lower() == 'true'
    
    # Debug: Check what's in the database
    all_user_notifications = Notification.objects.filter(recipient=request.user)
    print(f"\n🔍 API DEBUG for user {request.user.username}:")
    print(f"Total notifications in DB: {all_user_notifications.count()}")
    
    for n in all_user_notifications:
        print(f"  - ID: {n.id}, Read: {n.is_read}, Archived: {n.is_archived}, Title: {n.title[:30]}")
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_archived=False
    )
    
    if not include_read:
        notifications = notifications.filter(is_read=False)
    
    notifications = notifications[:limit]
    
    unread_count = Notification.objects.filter(
        recipient=request.user, 
        is_read=False,
        is_archived=False
    ).count()
    
    print(f"Calculated unread_count: {unread_count}")
    
    data = {
        'count': notifications.count(),
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'icon': n.get_icon_class(),
                'color': n.get_color_class(),
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
                'time_ago': n.created_at.strftime('%Y-%m-%d %H:%M'),
                'action_url': n.action_url,
            }
            for n in notifications
        ]
    }
    
    return JsonResponse(data)


@require_POST
@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a single notification as read
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    
    return JsonResponse({
        'success': True,
        'unread_count': Notification.objects.filter(
            recipient=request.user, 
            is_read=False,
            is_archived=False
        ).count()
    })


@require_POST
@login_required
def mark_all_read(request):
    """
    Mark all notifications as read
    """
    updated = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
        is_archived=False
    ).update(is_read=True)
    
    return JsonResponse({
        'success': True,
        'updated': updated,
        'unread_count': 0
    })


@require_POST
@login_required
def archive_notification(request, notification_id):
    """
    Archive a notification
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.archive()
    
    return JsonResponse({'success': True})


@require_POST
@login_required
def archive_all_read(request):
    """
    Archive all read notifications
    """
    updated = Notification.objects.filter(
        recipient=request.user,
        is_read=True,
        is_archived=False
    ).update(is_archived=True)
    
    return JsonResponse({
        'success': True,
        'updated': updated
    })


@login_required
def notification_preferences_view(request):
    """
    View and update notification preferences
    """
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update email preferences
        preferences.email_notifications = request.POST.get('email_notifications') == 'on'
        preferences.email_frequency = request.POST.get('email_frequency', 'instant')
        preferences.in_app_notifications = request.POST.get('in_app_notifications') == 'on'
        
        # Update quiet hours
        preferences.quiet_hours_enabled = request.POST.get('quiet_hours_enabled') == 'on'
        if preferences.quiet_hours_enabled:
            from django.utils.dateparse import parse_time
            preferences.quiet_hours_start = parse_time(request.POST.get('quiet_hours_start'))
            preferences.quiet_hours_end = parse_time(request.POST.get('quiet_hours_end'))
        else:
            preferences.quiet_hours_start = None
            preferences.quiet_hours_end = None
        
        # Update type preferences
        type_preferences = {}
        notification_types = [
            'admin_new_vendor', 'admin_vendor_kyc', 'admin_new_product',
            'vendor_kyc_approved', 'vendor_kyc_rejected',
            'consumer_price_alert', 'consumer_favorite_update', 'consumer_new_vendor'
        ]
        
        for nt in notification_types:
            type_preferences[nt] = {
                'email': request.POST.get(f'{nt}_email') == 'on',
                'in_app': request.POST.get(f'{nt}_in_app') == 'on',
            }
        
        preferences.type_preferences = type_preferences
        preferences.save()
        
        return JsonResponse({'success': True})
    
    context = {
        'preferences': preferences,
    }
    
    return render(request, 'notifications/preferences.html', context)



@login_required
def pending_vendors_count_api(request):
    """
    API endpoint to get count of pending vendor verifications for admin
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    from vendor.models import VendorKYC
    count = VendorKYC.objects.filter(is_approved=False).count()
    
    return JsonResponse({'count': count})