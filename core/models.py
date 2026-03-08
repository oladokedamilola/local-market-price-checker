# core/models.py
from django.db import models
from django.contrib.auth.models import User
from vendor.models import VendorProduct
import uuid

class Comparison(models.Model):
    """Saved product comparisons"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comparisons')
    name = models.CharField(max_length=100, blank=True, help_text="Optional name for this comparison")
    products = models.ManyToManyField(VendorProduct, related_name='comparisons')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    share_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comparison by {self.user.username} - {self.created_at.date()}"
    
    def product_count(self):
        return self.products.count()