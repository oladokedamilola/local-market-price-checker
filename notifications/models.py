# notifications/models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
import json

class Notification(models.Model):
    """
    Universal notification model for all user types
    """
    NOTIFICATION_TYPES = (
        # Admin Notifications
        ('admin_new_vendor', 'New Vendor Registration'),
        ('admin_vendor_kyc', 'Vendor KYC Submission'),
        ('admin_vendor_verified', 'Vendor Verified'),
        ('admin_new_product', 'New Product Added'),
        ('admin_product_update', 'Product Updated'),
        ('admin_category_request', 'New Category Request'),
        
        # Vendor Notifications
        ('vendor_kyc_approved', 'KYC Approved'),
        ('vendor_kyc_rejected', 'KYC Rejected'),
        ('vendor_kyc_pending', 'KYC Pending Review'),
        ('vendor_product_approved', 'Product Approved'),
        ('vendor_price_alert', 'Price Alert for Your Product'),
        ('vendor_category_approved', 'Category Request Approved'),
        ('vendor_category_rejected', 'Category Request Rejected'),
        
        # Consumer Notifications
        ('consumer_price_alert', 'Price Drop Alert'),
        ('consumer_favorite_update', 'Favorite Product Update'),
        ('consumer_comparison_update', 'Saved Comparison Update'),
        ('consumer_new_vendor', 'New Vendor in Your Market'),
        ('consumer_product_available', 'Product Back in Stock'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    # Basic fields
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Priority and status
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    # For linking to related objects
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Action URL (where to go when clicked)
    action_url = models.CharField(max_length=500, blank=True)
    
    # Email tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    def mark_as_unread(self):
        """Mark notification as unread"""
        self.is_read = False
        self.save(update_fields=['is_read'])
    
    def archive(self):
        """Archive notification"""
        self.is_archived = True
        self.save(update_fields=['is_archived'])
    
    def get_icon_class(self):
        """Get Bootstrap icon class based on notification type"""
        icons = {
            'admin': 'bi-shield-shaded',
            'vendor': 'bi-shop',
            'consumer': 'bi-person',
            'price_alert': 'bi-graph-down',
            'kyc': 'bi-check-circle',
            'product': 'bi-box',
            'default': 'bi-bell',
        }
        
        if self.notification_type.startswith('admin'):
            return icons['admin']
        elif self.notification_type.startswith('vendor'):
            return icons['vendor']
        elif self.notification_type.startswith('consumer'):
            return icons['consumer']
        elif 'price' in self.notification_type:
            return icons['price_alert']
        elif 'kyc' in self.notification_type:
            return icons['kyc']
        elif 'product' in self.notification_type:
            return icons['product']
        return icons['default']
    
    def get_color_class(self):
        """Get color class based on priority"""
        colors = {
            'low': 'text-secondary',
            'medium': 'text-primary',
            'high': 'text-warning',
            'urgent': 'text-danger',
        }
        return colors.get(self.priority, 'text-primary')
    
    def get_badge_class(self):
        """Get badge class based on priority"""
        classes = {
            'low': 'bg-secondary',
            'medium': 'bg-primary',
            'high': 'bg-warning',
            'urgent': 'bg-danger',
        }
        return classes.get(self.priority, 'bg-primary')


class NotificationPreference(models.Model):
    """
    User preferences for notifications
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_notifications = models.BooleanField(default=True)
    email_frequency = models.CharField(
        max_length=20,
        choices=[
            ('instant', 'Instant'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
        ],
        default='instant'
    )
    
    # In-app preferences
    in_app_notifications = models.BooleanField(default=True)
    
    # Specific notification type preferences (JSON field)
    type_preferences = models.JSONField(default=dict)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    def should_send_email(self, notification_type):
        """Check if email should be sent for this notification type"""
        if not self.email_notifications:
            return False
        
        # Check quiet hours
        if self.quiet_hours_enabled and self.quiet_hours_start and self.quiet_hours_end:
            now = timezone.now().time()
            if self.quiet_hours_start <= now <= self.quiet_hours_end:
                return False
        
        # Check type-specific preferences
        if notification_type in self.type_preferences:
            return self.type_preferences[notification_type].get('email', True)
        
        return True
    
    def should_send_in_app(self, notification_type):
        """Check if in-app notification should be created"""
        if not self.in_app_notifications:
            return False
        
        # Check type-specific preferences
        if notification_type in self.type_preferences:
            return self.type_preferences[notification_type].get('in_app', True)
        
        return True