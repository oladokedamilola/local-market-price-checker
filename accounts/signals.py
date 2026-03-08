from django.db.models.signals import post_save, pre_save, pre_delete, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from notifications.services import NotificationService
from .models import (
    Profile, CategoryRequest, PriceAlert, 
    FavoriteProduct, FavoriteVendor
)
from notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    """Create default groups after migrations."""
    if sender.name == 'accounts':
        Group.objects.get_or_create(name='CONSUMER')
        Group.objects.get_or_create(name='VENDOR')
        print("✅ Default groups created successfully!")


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile for every new user"""
    if created:
        Profile.objects.create(user=instance)
        print(f"✅ Profile created for user: {instance.username}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile when user is saved"""
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)


# ==================== CATEGORY REQUEST SIGNALS ====================

@receiver(post_save, sender=CategoryRequest)
def notify_admin_on_category_request(sender, instance, created, **kwargs):
    """
    Signal to notify admins when a new category request is created
    """
    if created:
        try:
            NotificationService.notify_admin_category_request(instance)
            logger.info(f"Admins notified about new category request: {instance.name}")
        except Exception as e:
            logger.error(f"Failed to notify admins about category request: {str(e)}", exc_info=True)


@receiver(post_save, sender=CategoryRequest)
def notify_vendor_on_category_decision(sender, instance, **kwargs):
    """
    Signal to notify vendor when their category request is approved or rejected
    """
    if not kwargs.get('created', False):
        try:
            old_instance = CategoryRequest.objects.get(pk=instance.pk)
            
            if old_instance.status != instance.status:
                if instance.status == 'approved':
                    NotificationService.notify_vendor_category_approved(instance)
                    logger.info(f"Vendor {instance.vendor.user.username} notified of category approval: {instance.name}")
                    
                elif instance.status == 'rejected':
                    NotificationService.notify_vendor_category_rejected(instance, instance.admin_notes)
                    logger.info(f"Vendor {instance.vendor.user.username} notified of category rejection: {instance.name}")
                    
        except CategoryRequest.DoesNotExist:
            logger.error(f"CategoryRequest with id {instance.pk} not found during status change check")
        except Exception as e:
            logger.error(f"Error in vendor category decision notification: {str(e)}", exc_info=True)


@receiver(pre_save, sender=CategoryRequest)
def track_status_change(sender, instance, **kwargs):
    """
    Track when status changes to set reviewed_at timestamp
    """
    if instance.pk:
        try:
            old_instance = CategoryRequest.objects.get(pk=instance.pk)
            
            if old_instance.status != instance.status and not instance.reviewed_at:
                from django.utils import timezone
                instance.reviewed_at = timezone.now()
                
        except CategoryRequest.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error tracking status change: {str(e)}")


@receiver(pre_delete, sender=CategoryRequest)
def archive_notifications_on_delete(sender, instance, **kwargs):
    """
    Archive notifications related to this category request when it's deleted
    """
    try:
        content_type = ContentType.objects.get_for_model(instance)
        
        Notification.objects.filter(
            content_type=content_type,
            object_id=instance.id
        ).update(is_archived=True)
        
        logger.info(f"Archived notifications for deleted category request: {instance.name}")
        
    except Exception as e:
        logger.error(f"Error archiving notifications on delete: {str(e)}", exc_info=True)


# ==================== PRICE ALERT SIGNALS ====================

@receiver(post_save, sender=PriceAlert)
def notify_on_price_alert_creation(sender, instance, created, **kwargs):
    """
    When a new price alert is created, check if price already meets target
    """
    if created:
        try:
            instance.check_price()
            logger.info(f"Initial price check performed for new alert {instance.id}")
        except Exception as e:
            logger.error(f"Error in initial price check for alert {instance.id}: {str(e)}", exc_info=True)


@receiver(post_save, sender=PriceAlert)
def notify_on_price_alert_trigger(sender, instance, **kwargs):
    """
    When a price alert status changes to 'triggered', send notification
    """
    if not kwargs.get('created', False):
        try:
            old_instance = PriceAlert.objects.get(pk=instance.pk)
            
            if old_instance.status != 'triggered' and instance.status == 'triggered':
                from notifications.services import NotificationService
                NotificationService.notify_price_alert(instance)
                logger.info(f"Price alert {instance.id} triggered - notification sent")
                
        except PriceAlert.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error in price alert trigger notification: {str(e)}", exc_info=True)


# ==================== FAVORITE PRODUCT SIGNALS ====================

@receiver(post_save, sender=FavoriteProduct)
def notify_on_favorite_product_update(sender, instance, created, **kwargs):
    """
    Notify user when a favorite product's price changes
    This would typically be triggered by a price update on VendorProduct
    """
    # This is a placeholder - actual implementation would be in vendor/models.py
    pass


# ==================== FAVORITE VENDOR SIGNALS ====================

@receiver(post_save, sender=FavoriteVendor)
def notify_on_favorite_vendor_new_product(sender, instance, created, **kwargs):
    """
    Notify user when a favorite vendor adds a new product
    This would be triggered when VendorProduct is created for that vendor
    """
    # This is a placeholder - actual implementation would be in vendor/models.py
    pass


# ==================== HELPER FUNCTION FOR PRICE CHECKING ====================

def check_all_price_alerts():
    """
    Helper function to check all active price alerts
    This can be called by a management command
    """
    from django.utils import timezone
    
    active_alerts = PriceAlert.objects.filter(
        status='active',
        product__is_available=True
    ).select_related('product', 'user')
    
    triggered_count = 0
    for alert in active_alerts:
        if alert.check_price():
            triggered_count += 1
    
    logger.info(f"Price alert check completed. Triggered: {triggered_count}")
    return triggered_count