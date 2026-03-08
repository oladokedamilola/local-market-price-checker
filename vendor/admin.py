from django.contrib import admin
from .models import VendorKYC

@admin.register(VendorKYC)
class VendorKYCAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'id_type', 'is_approved', 'submitted_at')
    list_filter = ('is_approved', 'id_type')
    actions = ['approve_kyc']

    def approve_kyc(self, request, queryset):
        for kyc in queryset:
            kyc.is_approved = True
            kyc.save()

            vendor = kyc.vendor
            vendor.is_verified = True
            vendor.save()

    approve_kyc.short_description = "Approve selected vendor KYC"
    
    
from .models import VendorProduct

admin.site.register(VendorProduct)
