# vendor/models.py
from django.db import models
from accounts.models import VendorProfile
from accounts.models import VendorProfile
from market.models import Product, Market

class VendorKYC(models.Model):
    ID_TYPE_CHOICES = [
        ('NIN', 'National Identification Number'),
        ('BVN', 'Bank Verification Number'),
        ('ID', 'Government Issued ID Card'),
    ]

    vendor = models.OneToOneField(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='kyc'
    )
    id_type = models.CharField(max_length=10, choices=ID_TYPE_CHOICES)
    id_document = models.FileField(upload_to='vendor_kyc/')
    business_name = models.CharField(max_length=200, blank=True)
    market_location = models.CharField(max_length=200, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection if applicable")
    
    def __str__(self):
        return f"KYC - {self.vendor.user.username}"



class VendorProduct(models.Model):
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='products'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # market is now derived from KYC, but we keep it for backward compatibility
    # It will be auto-filled from vendor's KYC market_location
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('vendor', 'product', 'market')

    def __str__(self):
        return f"{self.vendor.user.username} - {self.product}"
    
    def get_primary_image(self):
        """Get the primary image for this product"""
        return self.product.images.filter(is_primary=True).first() or self.product.images.first()