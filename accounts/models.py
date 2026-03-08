from django.contrib.auth.models import User
from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class Profile(models.Model):
    """
    Common profile model for all users to store profile pictures and other shared data
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

    def get_profile_picture_url(self):
        """Returns the profile picture URL or a default one"""
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return '/static/images/default-avatar.jpg'  

class ConsumerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Consumer: {self.user.username}"


class VendorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vendor: {self.user.username}"


class EmailVerification(models.Model):
    """Model to handle email verification tokens"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"

    def __str__(self):
        return f"Verification for {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24)
            self.expires_at = timezone.now() + timedelta(hours=expiry_hours)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if token is valid (not expired and not used)"""
        return not self.is_used and self.expires_at > timezone.now()


class PasswordReset(models.Model):
    """Model to handle password reset tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_resets')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Password Reset"
        verbose_name_plural = "Password Resets"

    def __str__(self):
        return f"Password reset for {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            expiry_hours = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY_HOURS', 1)
            self.expires_at = timezone.now() + timedelta(hours=expiry_hours)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if token is valid (not expired and not used)"""
        return not self.is_used and self.expires_at > timezone.now()


class RateLimit(models.Model):
    """Rate limiting for various actions"""
    ACTION_CHOICES = (
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('email_verification', 'Email Verification'),
        ('password_reset', 'Password Reset'),
         ('password_change', 'Password Change'),
    )
    
    email = models.EmailField(db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    attempt_count = models.IntegerField(default=0)
    first_attempt = models.DateTimeField(auto_now_add=True)
    last_attempt = models.DateTimeField(auto_now=True)
    blocked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('email', 'action')
        verbose_name = "Rate Limit"
        verbose_name_plural = "Rate Limits"

    def __str__(self):
        return f"{self.email} - {self.action}"

    @classmethod
    def check_rate_limit(cls, email, action):
        """
        Check if an action is rate limited.
        Returns (is_allowed, block_info)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        rate_limit, created = cls.objects.get_or_create(
            email=email,
            action=action,
            defaults={'first_attempt': timezone.now()}
        )
        
        if rate_limit.blocked_until and rate_limit.blocked_until > timezone.now():
            minutes_remaining = int((rate_limit.blocked_until - timezone.now()).total_seconds() / 60)
            return False, {
                'blocked': True,
                'minutes_remaining': minutes_remaining,
                'blocked_until': rate_limit.blocked_until,
                'attempts': rate_limit.attempt_count
            }
        
        if rate_limit.blocked_until and rate_limit.blocked_until <= timezone.now():
            rate_limit.blocked_until = None
            rate_limit.attempt_count = 0
            rate_limit.save()
        
        window_hours = getattr(settings, 'RATE_LIMIT_WINDOW_HOURS', 1)
        max_attempts = getattr(settings, 'RATE_LIMIT_MAX_ATTEMPTS', 3)
        
        time_window_start = timezone.now() - timedelta(hours=window_hours)
        
        if rate_limit.first_attempt < time_window_start:
            rate_limit.attempt_count = 0
            rate_limit.first_attempt = timezone.now()
            rate_limit.save()
        
        if rate_limit.attempt_count >= max_attempts:
            block_hours = getattr(settings, 'RATE_LIMIT_BLOCK_HOURS', 1)
            rate_limit.blocked_until = timezone.now() + timedelta(hours=block_hours)
            rate_limit.save()
            
            minutes_remaining = block_hours * 60
            return False, {
                'blocked': True,
                'minutes_remaining': minutes_remaining,
                'blocked_until': rate_limit.blocked_until,
                'attempts': rate_limit.attempt_count
            }
        
        return True, {
            'blocked': False,
            'attempts': rate_limit.attempt_count,
            'remaining': max_attempts - rate_limit.attempt_count
        }
    
    def increment_attempt(self):
        """Increment attempt count"""
        self.attempt_count += 1
        self.last_attempt = timezone.now()
        self.save()
    
    def reset_attempts(self):
        """Reset attempt count"""
        self.attempt_count = 0
        self.blocked_until = None
        self.first_attempt = timezone.now()
        self.save()
        
        
class PriceAlert(models.Model):
    """Model for users to set price alerts on products"""
    FREQUENCY_CHOICES = (
        ('instant', 'Instant (as soon as price drops)'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('triggered', 'Triggered'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='price_alerts')
    product = models.ForeignKey('vendor.VendorProduct', on_delete=models.CASCADE, related_name='price_alerts')
    target_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='instant')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    last_checked = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    trigger_count = models.IntegerField(default=0)
    
    notes = models.TextField(blank=True, help_text="Optional notes about this alert")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'product', 'target_price')
    
    def __str__(self):
        return f"Alert for {self.product.product.name} at ₦{self.target_price}"
    
    def check_price(self):
        """Check if current price meets target"""
        from django.utils import timezone
        
        latest_price = self.product.price
        
        if latest_price <= self.target_price:
            self.status = 'triggered'
            self.last_triggered = timezone.now()
            self.trigger_count += 1
            self.save()
            return True
        
        self.last_checked = timezone.now()
        self.save()
        return False


class FavoriteProduct(models.Model):
    """Model for users to save favorite products"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_products')
    product = models.ForeignKey('vendor.VendorProduct', on_delete=models.CASCADE, related_name='favorited_by')
    notes = models.CharField(max_length=255, blank=True, help_text="Personal notes about this product")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.username} - {self.product.product.name}"


class FavoriteVendor(models.Model):
    """Model for users to save favorite vendors"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_vendors')
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='favorited_by')
    notes = models.CharField(max_length=255, blank=True, help_text="Personal notes about this vendor")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'vendor')
    
    def __str__(self):
        return f"{self.user.username} - {self.vendor.user.username}"
    
    
class CategoryRequest(models.Model):
    """
    Model to handle vendor requests for new product categories
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_review', 'In Review'),
    )
    
    vendor = models.ForeignKey('VendorProfile', on_delete=models.CASCADE, related_name='category_requests')
    name = models.CharField(max_length=100, help_text="Requested category name")
    description = models.TextField(blank=True, help_text="Description or reason for the category")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes about this request")
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_category_requests'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Category Request"
        verbose_name_plural = "Category Requests"
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['vendor', 'status']),
        ]
    
    def __str__(self):
        return f"Category Request: {self.name} by {self.vendor.user.username}"
    
    def approve(self, admin_user=None, notes=""):
        """Approve the category request and create the actual category"""
        from django.utils import timezone
        from market.models import Category
        from django.utils.text import slugify
        
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save()
        
        category = Category.objects.create(
            name=self.name,
            slug=slugify(self.name),
            description=self.description,
            icon='bi-tag'
        )
        
        return category
    
    def reject(self, admin_user=None, reason=""):
        """Reject the category request"""
        from django.utils import timezone
        
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        if reason:
            self.admin_notes = reason
        self.save()
    
    def get_status_badge_class(self):
        """Get Bootstrap badge class for status"""
        badge_map = {
            'pending': 'bg-warning',
            'approved': 'bg-success',
            'rejected': 'bg-danger',
            'in_review': 'bg-info',
        }
        return badge_map.get(self.status, 'bg-secondary')
    
    def get_status_icon(self):
        """Get Bootstrap icon for status"""
        icon_map = {
            'pending': 'bi-hourglass',
            'approved': 'bi-check-circle',
            'rejected': 'bi-x-circle',
            'in_review': 'bi-eye',
        }
        return icon_map.get(self.status, 'bi-question-circle')
    
    @property
    def days_since_request(self):
        """Get number of days since request was made"""
        from django.utils import timezone
        delta = timezone.now() - self.created_at
        return delta.days