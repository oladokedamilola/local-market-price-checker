from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from vendor.models import VendorProduct
from accounts.models import FavoriteVendor
from notifications.services import NotificationService
from django.urls import reverse

@receiver(post_save, sender=VendorProduct)
def notify_followers_on_new_product(sender, instance, created, **kwargs):
    """Notify followers when a vendor adds a new product"""
    if created:
        vendor = instance.vendor
        followers = FavoriteVendor.objects.filter(vendor=vendor).select_related('user')
        
        for follower in followers:
            NotificationService.create_notification(
                recipient=follower.user,
                notification_type='consumer_new_vendor',
                title=f'New Product from {vendor.user.get_full_name() or vendor.user.username}',
                message=f'{vendor.user.get_full_name() or vendor.user.username} added {instance.product.name} at ₦{instance.price}',
                related_object=instance,
                priority='medium',
                action_url=reverse('product_detail', args=[instance.id])
            )

@receiver(pre_save, sender=VendorProduct)
def notify_followers_on_price_change(sender, instance, **kwargs):
    """Notify followers when a vendor updates product price"""
    if instance.pk:
        try:
            old = VendorProduct.objects.get(pk=instance.pk)
            if old.price != instance.price:
                vendor = instance.vendor
                followers = FavoriteVendor.objects.filter(vendor=vendor).select_related('user')
                
                for follower in followers:
                    NotificationService.create_notification(
                        recipient=follower.user,
                        notification_type='consumer_favorite_update',
                        title=f'Price Update from {vendor.user.get_full_name() or vendor.user.username}',
                        message=f'{instance.product.name} price changed from ₦{old.price} to ₦{instance.price}',
                        related_object=instance,
                        priority='medium',
                        action_url=reverse('product_detail', args=[instance.id])
                    )
        except VendorProduct.DoesNotExist:
            pass