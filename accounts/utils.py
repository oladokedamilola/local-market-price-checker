# accounts/utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
import logging




logger = logging.getLogger(__name__)

def send_verification_email(user, token_obj):
    """Send email verification link to user"""
    try:
        verification_url = f"{settings.SITE_URL}{reverse('verify_email', args=[token_obj.token])}"
        
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'MarketLens',
            'expiry_hours': getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24),
        }
        
        # Render email templates
        html_message = render_to_string('accounts/emails/verification_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Verify your email address - MarketLens',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        raise

def send_password_reset_email(user, token_obj):
    """Send password reset link to user"""
    try:
        reset_url = f"{settings.SITE_URL}{reverse('password_reset_confirm', args=[token_obj.token])}"
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'MarketLens',
            'expiry_hours': getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY_HOURS', 1),
        }
        
        # Render email templates
        html_message = render_to_string('accounts/emails/password_reset_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Reset your password - MarketLens',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        raise

def send_welcome_email(user, role='consumer'):
    """
    Send welcome email based on user role
    """
    try:
        if role == 'vendor':
            template = 'accounts/emails/welcome_vendor_email.html'
            subject = 'Welcome to MarketLens - Complete Your Vendor Setup!'
        else:
            template = 'accounts/emails/welcome_consumer_email.html'
            subject = 'Welcome to MarketLens - Start Comparing Prices!'
        
        context = {
            'user': user,
            'site_name': 'MarketLens',
            'login_url': f"{settings.SITE_URL}{reverse('login')}",
            'dashboard_url': f"{settings.SITE_URL}{reverse('dashboard')}",
        }
        
        if role == 'vendor':
            context['kyc_url'] = f"{settings.SITE_URL}{reverse('vendor_kyc')}"
        
        html_message = render_to_string(template, context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to {user.email} ({role})")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        raise