# market/models.py
from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    """Product categories"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon class (e.g., bi-box)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def product_count(self):
        return self.product_set.count()


class Market(models.Model):
    """Markets in Alimosho LGA"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    cover_image = models.ImageField(upload_to='markets/', blank=True, null=True)
    opening_hours = models.CharField(max_length=255, blank=True, help_text="e.g., Mon-Sat: 8am-8pm")
    contact_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def vendor_count(self):
        from vendor.models import VendorProduct
        return VendorProduct.objects.filter(market=self).values('vendor').distinct().count()

    def product_count(self):
        from vendor.models import VendorProduct
        return VendorProduct.objects.filter(market=self).count()


class Product(models.Model):
    """Base product definitions"""
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    unit = models.CharField(
        max_length=50,
        help_text="e.g., cup, kg, basket, piece"
    )
    image = models.ImageField(upload_to='products/', blank=True, null=True)  # Single image
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'unit')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.unit})"

    def vendor_count(self):
        from vendor.models import VendorProduct
        return VendorProduct.objects.filter(product=self).values('vendor').distinct().count()

    def average_price(self):
        from vendor.models import VendorProduct
        prices = VendorProduct.objects.filter(product=self).values_list('price', flat=True)
        if prices:
            return sum(prices) / len(prices)
        return 0