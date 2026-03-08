from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db.models import Q
from datetime import timedelta
import logging
from accounts.models import PriceAlert
from .services import NotificationService

logger = logging.getLogger(__name__)

class PriceAlertService:
    """
    Service to check and process price alerts
    """
    
    @classmethod
    def check_all_alerts(cls, frequency=None):
        """
        Check all active price alerts
        If frequency specified, only check alerts with that frequency
        """
        logger.info("Starting price alert check...")
        
        # Base queryset for active alerts
        alerts = PriceAlert.objects.filter(
            status='active',
            product__is_available=True,
            product__vendor__is_verified=True
        ).select_related(
            'user', 
            'product__product', 
            'product__vendor__user'
        )
        
        # Filter by frequency if specified
        if frequency:
            alerts = alerts.filter(frequency=frequency)
        
        triggered_count = 0
        for alert in alerts:
            try:
                if cls.check_single_alert(alert):
                    triggered_count += 1
            except Exception as e:
                logger.error(f"Error checking alert {alert.id}: {str(e)}")
        
        logger.info(f"Price alert check complete. Triggered: {triggered_count}")
        return triggered_count
    
    @classmethod
    def check_single_alert(cls, alert):
        """
        Check a single price alert and trigger if conditions met
        """
        current_price = alert.product.price
        
        # Update current price
        alert.current_price = current_price
        alert.last_checked = timezone.now()
        
        # Check if price meets target
        if current_price <= alert.target_price:
            # Trigger the alert
            alert.status = 'triggered'
            alert.last_triggered = timezone.now()
            alert.trigger_count += 1
            alert.save()
            
            # Send notifications
            cls.send_alert_notifications(alert)
            
            logger.info(f"Alert {alert.id} triggered for {alert.user.email} - {alert.product.product.name}")
            return True
        else:
            alert.save(update_fields=['current_price', 'last_checked'])
            return False
    
    @classmethod
    def send_alert_notifications(cls, alert):
        """
        Send notifications for triggered alert
        """
        # Create in-app notification
        NotificationService.notify_price_alert(alert)
        
        # Send email notification based on frequency
        if alert.frequency == 'instant':
            cls.send_instant_email(alert)
        elif alert.frequency == 'daily':
            # Will be handled by daily digest
            pass
        elif alert.frequency == 'weekly':
            # Will be handled by weekly digest
            pass
    
    @classmethod
    def send_instant_email(cls, alert):
        """
        Send instant email notification for price alert
        """
        try:
            savings = alert.product.price - alert.target_price
            
            context = {
                'user': alert.user,
                'alert': alert,
                'product': alert.product,
                'savings': abs(savings),
                'site_url': settings.SITE_URL,
            }
            
            html_message = render_to_string('notifications/email/price_alert_instant.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f'🔥 Price Drop Alert: {alert.product.product.name} is now ₦{alert.product.price}',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[alert.user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Instant email sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending instant email for alert {alert.id}: {str(e)}")
            return False
    
    @classmethod
    def send_daily_digest(cls):
        """
        Send daily digest of triggered alerts
        """
        yesterday = timezone.now() - timedelta(days=1)
        
        # Get alerts triggered in the last 24 hours
        triggered_alerts = PriceAlert.objects.filter(
            status='triggered',
            last_triggered__gte=yesterday,
            frequency='daily',
            email_sent=False
        ).select_related('user', 'product__product')
        
        # Group by user
        user_alerts = {}
        for alert in triggered_alerts:
            if alert.user.id not in user_alerts:
                user_alerts[alert.user.id] = {
                    'user': alert.user,
                    'alerts': []
                }
            user_alerts[alert.user.id]['alerts'].append(alert)
        
        # Send digest to each user
        for user_data in user_alerts.values():
            cls.send_daily_digest_email(user_data['user'], user_data['alerts'])
            
            # Mark alerts as emailed
            for alert in user_data['alerts']:
                alert.email_sent = True
                alert.save()
        
        logger.info(f"Daily digest sent to {len(user_alerts)} users")
        return len(user_alerts)
    
    @classmethod
    def send_daily_digest_email(cls, user, alerts):
        """
        Send daily digest email to user
        """
        try:
            context = {
                'user': user,
                'alerts': alerts,
                'alert_count': len(alerts),
                'site_url': settings.SITE_URL,
            }
            
            html_message = render_to_string('notifications/email/price_alert_daily.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f'📊 Your Daily Price Alert Digest - {len(alerts)} updates',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Daily digest sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending daily digest to {user.email}: {str(e)}")
            return False
    
    @classmethod
    def send_weekly_digest(cls):
        """
        Send weekly digest of triggered alerts
        """
        last_week = timezone.now() - timedelta(days=7)
        
        # Get alerts triggered in the last 7 days
        triggered_alerts = PriceAlert.objects.filter(
            status='triggered',
            last_triggered__gte=last_week,
            frequency='weekly',
            email_sent=False
        ).select_related('user', 'product__product')
        
        # Group by user
        user_alerts = {}
        for alert in triggered_alerts:
            if alert.user.id not in user_alerts:
                user_alerts[alert.user.id] = {
                    'user': alert.user,
                    'alerts': []
                }
            user_alerts[alert.user.id]['alerts'].append(alert)
        
        # Send digest to each user
        for user_data in user_alerts.values():
            cls.send_weekly_digest_email(user_data['user'], user_data['alerts'])
            
            # Mark alerts as emailed
            for alert in user_data['alerts']:
                alert.email_sent = True
                alert.save()
        
        logger.info(f"Weekly digest sent to {len(user_alerts)} users")
        return len(user_alerts)
    
    @classmethod
    def send_weekly_digest_email(cls, user, alerts):
        """
        Send weekly digest email to user
        """
        try:
            # Calculate total savings
            total_savings = sum(alert.target_price - alert.product.price for alert in alerts)
            
            context = {
                'user': user,
                'alerts': alerts,
                'alert_count': len(alerts),
                'total_savings': abs(total_savings),
                'site_url': settings.SITE_URL,
            }
            
            html_message = render_to_string('notifications/email/price_alert_weekly.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f'📈 Your Weekly Price Alert Summary - {len(alerts)} deals found',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Weekly digest sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending weekly digest to {user.email}: {str(e)}")
            return False
    
    @classmethod
    def cleanup_old_alerts(cls, days=30):
        """
        Archive or delete old triggered alerts
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Archive old triggered alerts
        old_alerts = PriceAlert.objects.filter(
            status='triggered',
            last_triggered__lt=cutoff_date
        )
        
        count = old_alerts.count()
        # Instead of deleting, you might want to mark them as expired
        old_alerts.update(status='expired')
        
        logger.info(f"Cleaned up {count} old alerts")
        return count