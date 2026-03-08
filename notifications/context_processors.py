from .models import Notification
import logging

logger = logging.getLogger(__name__)

def notifications_processor(request):
    """
    Context processor to add notification data to all templates
    """
    if request.user.is_authenticated:
        print(f"\n{'='*50}")
        print(f"🔍 NOTIFICATION CONTEXT PROCESSOR DEBUG")
        print(f"{'='*50}")
        print(f"User: {request.user.username} (ID: {request.user.id})")
        print(f"Is authenticated: {request.user.is_authenticated}")
        
        # Check ALL notifications for this user
        all_notifications = Notification.objects.filter(recipient=request.user)
        total_count = all_notifications.count()
        print(f"Total notifications in DB for this user: {total_count}")
        
        if total_count > 0:
            print("\nAll notifications:")
            for n in all_notifications:
                print(f"  - ID: {n.id}, Title: {n.title[:30]}, Read: {n.is_read}, Archived: {n.is_archived}")
        
        # Count unread, non-archived
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
            is_archived=False
        ).count()
        print(f"\nUnread count (is_read=False, is_archived=False): {unread_count}")
        
        # Break down the counts
        read_count = all_notifications.filter(is_read=True).count()
        archived_count = all_notifications.filter(is_archived=True).count()
        read_archived = all_notifications.filter(is_read=True, is_archived=True).count()
        unread_archived = all_notifications.filter(is_read=False, is_archived=True).count()
        
        print(f"\nBreakdown:")
        print(f"  - Read: {read_count}")
        print(f"  - Archived: {archived_count}")
        print(f"  - Read + Archived: {read_archived}")
        print(f"  - Unread + Archived: {unread_archived}")
        print(f"{'='*50}\n")
        
        recent_notifications = Notification.objects.filter(
            recipient=request.user,
            is_archived=False
        ).order_by('-created_at')[:5]
        
        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    
    print(f"\n{'='*50}")
    print(f"🔍 NOTIFICATION CONTEXT PROCESSOR DEBUG (Unauthenticated)")
    print(f"{'='*50}\n")
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }