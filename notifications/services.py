# notifications\services.py
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Service class for creating and sending notifications
    All notification creation goes through this service to ensure consistency
    and proper email sending based on user preferences.
    """
    
    @classmethod
    def create_notification(cls, recipient, notification_type, title, message, 
                           related_object=None, priority='medium', action_url=''):
        """
        Core method to create a notification for a user
        Handles both in-app and email notifications based on user preferences
        """
        try:
            # Get or create notification preferences
            preferences, _ = NotificationPreference.objects.get_or_create(user=recipient)
            
            # Check if in-app notification should be created
            send_in_app = preferences.should_send_in_app(notification_type)
            send_email = preferences.should_send_email(notification_type)
            
            notification = None
            
            # Create in-app notification if enabled
            if send_in_app:
                # Prepare related object data
                content_type = None
                object_id = None
                if related_object:
                    content_type = ContentType.objects.get_for_model(related_object)
                    object_id = related_object.id
                
                # Create notification
                notification = Notification.objects.create(
                    recipient=recipient,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    priority=priority,
                    content_type=content_type,
                    object_id=object_id,
                    action_url=action_url
                )
                
                logger.info(f"In-app notification created for {recipient.username}: {notification_type}")
            
            # Send email if enabled
            if send_email:
                cls._send_notification_email(
                    recipient=recipient,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    action_url=action_url,
                    related_object=related_object
                )
                logger.info(f"Email notification sent to {recipient.email}: {notification_type}")
            
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}", exc_info=True)
            return None
    

    @classmethod
    def _send_notification_email(cls, recipient, title, message, notification_type, 
                                action_url='', related_object=None):
        """
        Internal method to send notification email
        Separated from create_notification to allow direct email sending when needed
        """
        try:
            # Choose template based on notification type - UPDATED TO MATCH YOUR FILES
            template_map = {
                # Admin notifications
                'admin_new_vendor': 'notifications/email/admin_new_vendor.html',
                'admin_vendor_kyc': 'notifications/email/admin_vendor_kyc.html',
                'admin_new_product': 'notifications/email/admin_new_product.html',
                'admin_product_update': 'notifications/email/admin_product_update.html',
                'admin_category_request': 'notifications/email/admin_category_request.html',
                
                # Vendor notifications
                'vendor_kyc_approved': 'notifications/email/vendor_kyc_approved.html',
                'vendor_kyc_rejected': 'notifications/email/vendor_kyc_rejected.html',
                'vendor_category_approved': 'notifications/email/vendor_category_approved.html',
                'vendor_category_rejected': 'notifications/email/vendor_category_rejected.html',
                
                # Consumer notifications
                'consumer_price_alert': 'notifications/email/price_alert_instant.html',  # Note: using price_alert_instant.html
                'consumer_favorite_update': 'notifications/email/favorite_update.html',
                'consumer_new_vendor': 'notifications/email/new_vendor.html',
                'consumer_comparison_update': 'notifications/email/comparison_update.html',  # You might need to create this
            }
            
            template_name = template_map.get(notification_type)
            
            # If no specific template found, use base template
            if not template_name:
                template_name = 'notifications/email/base_notification.html'
                logger.warning(f"No specific email template found for {notification_type}, using base template")
            
            # Prepare context for template
            context = {
                'user': recipient,  # Changed from 'recipient' to 'user' to match template variables
                'title': title,
                'message': message,
                'notification_type': notification_type,
                'action_url': action_url,
                'site_url': settings.SITE_URL.rstrip('/'),
                'related_object': related_object,
            }
            
            # Add specific context for different notification types
            if notification_type == 'consumer_price_alert' and related_object:
                context['alert'] = related_object  # For price_alert_instant.html which uses 'alert' variable
                context['savings'] = abs(related_object.target_price - related_object.product.price)
                context['product'] = related_object.product
                
            elif notification_type == 'admin_new_vendor' and related_object:
                context['vendor_profile'] = related_object
                
            elif notification_type == 'admin_vendor_kyc' and related_object:
                context['kyc_submission'] = related_object
                
            elif notification_type in ['vendor_kyc_approved', 'vendor_kyc_rejected'] and related_object:
                context['vendor_profile'] = related_object
                
            elif notification_type in ['vendor_category_approved', 'vendor_category_rejected'] and related_object:
                context['category_request'] = related_object
                
            elif notification_type == 'consumer_favorite_update' and related_object:
                context['favorite'] = related_object
                
            elif notification_type == 'consumer_new_vendor' and related_object:
                context['vendor_profile'] = related_object
                
            elif notification_type == 'admin_category_request' and related_object:
                context['category_request'] = related_object
            
            # Render email templates
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)
            
            # Send email
            send_mail(
                subject=title,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Email sent successfully for {notification_type} to {recipient.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}", exc_info=True)
            return False
    
    # ==================== ADMIN NOTIFICATIONS ====================
    
    @classmethod
    def notify_admin_new_vendor(cls, vendor_profile):
        """
        Notify admins about new vendor registration (email + in-app)
        """
        admins = User.objects.filter(is_staff=True)
        title = f"New Vendor Registration: {vendor_profile.user.username}"
        message = f"{vendor_profile.user.get_full_name() or vendor_profile.user.username} has registered as a vendor and submitted KYC for verification."
        action_url = reverse('admin_vendor_verification')
        
        for admin in admins:
            cls.create_notification(
                recipient=admin,
                notification_type='admin_new_vendor',
                title=title,
                message=message,
                related_object=vendor_profile,
                priority='high',
                action_url=action_url
            )
    
    @classmethod
    def notify_admin_vendor_kyc(cls, kyc_submission):
        """
        Notify admins about new KYC submission (email + in-app)
        """
        admins = User.objects.filter(is_staff=True)
        title = f"KYC Submission: {kyc_submission.vendor.user.username}"
        message = f"New KYC documents submitted by {kyc_submission.vendor.user.username}. Please review."
        action_url = reverse('admin_verify_vendor', args=[kyc_submission.id])
        
        for admin in admins:
            cls.create_notification(
                recipient=admin,
                notification_type='admin_vendor_kyc',
                title=title,
                message=message,
                related_object=kyc_submission,
                priority='high',
                action_url=action_url
            )
    
    @classmethod
    def notify_admin_new_product(cls, vendor_product):
        """
        Notify admins about new product added (in-app only - no email)
        """
        admins = User.objects.filter(is_staff=True)
        title = f"New Product: {vendor_product.product.name}"
        message = f"{vendor_product.vendor.user.username} added {vendor_product.product.name} at ₦{vendor_product.price}"
        action_url = reverse('admin_vendor_products')
        
        for admin in admins:
            cls.create_notification(
                recipient=admin,
                notification_type='admin_new_product',
                title=title,
                message=message,
                related_object=vendor_product,
                priority='medium',
                action_url=action_url
            )
    
    @classmethod
    def notify_admin_product_update(cls, vendor_product):
        """
        Notify admins about product update (in-app only - no email)
        """
        admins = User.objects.filter(is_staff=True)
        title = f"Product Updated: {vendor_product.product.name}"
        message = f"{vendor_product.vendor.user.username} updated {vendor_product.product.name} to ₦{vendor_product.price}"
        action_url = reverse('admin_vendor_products')
        
        for admin in admins:
            cls.create_notification(
                recipient=admin,
                notification_type='admin_product_update',
                title=title,
                message=message,
                related_object=vendor_product,
                priority='low',
                action_url=action_url
            )
    
    @classmethod
    def notify_admin_category_request(cls, category_request):
        """
        Notify admins about new category request (email + in-app)
        Note: This is also triggered by signal, but kept here for direct calls if needed
        """
        admins = User.objects.filter(is_staff=True)
        title = f"New Category Request: {category_request.name}"
        message = f"Vendor {category_request.vendor.user.get_full_name() or category_request.vendor.user.username} has requested a new category: '{category_request.name}'."
        action_url = reverse('admin_category_requests')
        
        for admin in admins:
            cls.create_notification(
                recipient=admin,
                notification_type='admin_category_request',
                title=title,
                message=message,
                related_object=category_request,
                priority='medium',
                action_url=action_url
            )
    
    # ==================== VENDOR NOTIFICATIONS ====================
    
    @classmethod
    def notify_vendor_kyc_approved(cls, vendor_profile):
        """
        Notify vendor about KYC approval (email required)
        """
        title = "✅ KYC Verification Approved!"
        message = "Congratulations! Your KYC verification has been approved. You can now start listing products and managing your vendor account."
        action_url = reverse('vendor_dashboard')
        
        cls.create_notification(
            recipient=vendor_profile.user,
            notification_type='vendor_kyc_approved',
            title=title,
            message=message,
            related_object=vendor_profile,
            priority='high',
            action_url=action_url
        )
    
    @classmethod
    def notify_vendor_kyc_rejected(cls, vendor_profile, reason=""):
        """
        Notify vendor about KYC rejection (email required)
        """
        title = "❌ KYC Verification Update"
        message = f"Your KYC verification was not approved. {reason if reason else 'Please resubmit with correct documents and try again.'}"
        action_url = reverse('vendor_kyc')
        
        cls.create_notification(
            recipient=vendor_profile.user,
            notification_type='vendor_kyc_rejected',
            title=title,
            message=message,
            related_object=vendor_profile,
            priority='high',
            action_url=action_url
        )
    
    @classmethod
    def notify_vendor_category_approved(cls, category_request):
        """
        Notify vendor that their category request was approved
        """
        title = f"✅ Category Request Approved: {category_request.name}"
        message = f"Your request for category '{category_request.name}' has been approved. You can now select it when adding products."
        action_url = reverse('add_product')
        
        cls.create_notification(
            recipient=category_request.vendor.user,
            notification_type='vendor_category_approved',
            title=title,
            message=message,
            related_object=category_request,
            priority='high',
            action_url=action_url
        )
    
    @classmethod
    def notify_vendor_category_rejected(cls, category_request, reason=""):
        """
        Notify vendor that their category request was rejected
        """
        title = f"❌ Category Request Update: {category_request.name}"
        message = f"Your request for category '{category_request.name}' was not approved. {reason if reason else 'Please contact admin for more information.'}"
        action_url = reverse('request_category')
        
        cls.create_notification(
            recipient=category_request.vendor.user,
            notification_type='vendor_category_rejected',
            title=title,
            message=message,
            related_object=category_request,
            priority='medium',
            action_url=action_url
        )
    
    # ==================== CONSUMER NOTIFICATIONS ====================
    
    @classmethod
    def notify_price_alert(cls, price_alert):
        """
        Notify consumer about price drop alert (email + in-app)
        """
        user = price_alert.user
        product = price_alert.product
        savings = price_alert.target_price - product.price
        
        title = f"🔥 Price Drop Alert: {product.product.name}"
        message = f"Good news! {product.product.name} is now ₦{product.price} (₦{abs(savings)} below your target price of ₦{price_alert.target_price})"
        action_url = reverse('product_detail', args=[product.id])
        
        cls.create_notification(
            recipient=user,
            notification_type='consumer_price_alert',
            title=title,
            message=message,
            related_object=price_alert,
            priority='high',
            action_url=action_url
        )
    
    @classmethod
    def notify_favorite_update(cls, favorite_product):
        """
        Notify consumer about update to favorite product (email + in-app)
        """
        user = favorite_product.user
        product = favorite_product.product
        
        title = f"⭐ Favorite Product Update: {product.product.name}"
        message = f"Price updated to ₦{product.price} at {product.market.name}"
        action_url = reverse('product_detail', args=[product.id])
        
        cls.create_notification(
            recipient=user,
            notification_type='consumer_favorite_update',
            title=title,
            message=message,
            related_object=favorite_product,
            priority='medium',
            action_url=action_url
        )
    
    @classmethod
    def notify_new_vendor_in_market(cls, consumer, vendor_profile, market):
        """
        Notify consumers about new vendor in their preferred market (email + in-app)
        """
        title = f"🆕 New Vendor in {market.name}"
        message = f"{vendor_profile.user.get_full_name() or vendor_profile.user.username} has started selling in {market.name}. Check out their products!"
        action_url = reverse('consumer_market_detail', args=[market.id])
        
        cls.create_notification(
            recipient=consumer,
            notification_type='consumer_new_vendor',
            title=title,
            message=message,
            related_object=vendor_profile,
            priority='low',
            action_url=action_url
        )
    
    @classmethod
    def notify_saved_comparison_update(cls, comparison, changed_products):
        """
        Notify consumer about updates to their saved comparison
        """
        user = comparison.user
        product_names = ", ".join([p.product.name for p in changed_products[:3]])
        if len(changed_products) > 3:
            product_names += f" and {len(changed_products) - 3} more"
        
        title = f"📊 Comparison Updated: {comparison.name}"
        message = f"Prices have changed for: {product_names}"
        action_url = reverse('consumer_comparison', args=[comparison.id])
        
        cls.create_notification(
            recipient=user,
            notification_type='consumer_comparison_update',
            title=title,
            message=message,
            related_object=comparison,
            priority='medium',
            action_url=action_url
        )


class NotificationCleanupService:
    """
    Service for cleaning up old notifications
    """
    
    @classmethod
    def delete_old_notifications(cls, days=30):
        """
        Delete notifications older than specified days
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_archived=True
        ).delete()[0]
        
        logger.info(f"Deleted {deleted_count} old notifications")
        return deleted_count
    
    @classmethod
    def archive_read_notifications(cls, days=7):
        """
        Archive read notifications older than specified days
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        archived_count = Notification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date,
            is_archived=False
        ).update(is_archived=True)
        
        logger.info(f"Archived {archived_count} read notifications")
        return archived_count