# accounts/views/vendor_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.urls import reverse
from ..forms import VendorKYCForm
from ..models import VendorProfile
from vendor.models import VendorKYC, VendorProduct
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@login_required
def vendor_dashboard_view(request):
    """Vendor-specific dashboard"""
    if not request.user.groups.filter(name='VENDOR').exists():
        messages.error(request, 'Access denied. Vendor privileges required.')
        return redirect('dashboard')
    
    try:
        vendor_profile = VendorProfile.objects.get(user=request.user)
        
        # Get vendor products
        products = VendorProduct.objects.filter(
            vendor=vendor_profile
        ).select_related('product', 'market').order_by('-last_updated')
        
        # Calculate statistics
        total_products = products.count()
        
        # Products by market
        products_by_market = {}
        for product in products:
            market_name = product.market.name
            if market_name not in products_by_market:
                products_by_market[market_name] = 0
            products_by_market[market_name] += 1
        
        # Recent products (last 5)
        recent_products = products[:5]
        
        # Price update stats
        last_week = timezone.now() - timedelta(days=7)
        recent_updates = products.filter(last_updated__gte=last_week).count()
        
        context = {
            'vendor_profile': vendor_profile,
            'products': products,
            'total_products': total_products,
            'products_by_market': products_by_market,
            'recent_products': recent_products,
            'recent_updates': recent_updates,
            'markets_count': len(products_by_market),
        }
        
        # Add verification status
        if vendor_profile.is_verified:
            context['verification_status'] = 'verified'
            context['verification_badge'] = 'bg-success'
        else:
            kyc_exists = VendorKYC.objects.filter(vendor=vendor_profile).exists()
            if kyc_exists:
                context['verification_status'] = 'pending'
                context['verification_badge'] = 'bg-warning'
            else:
                context['verification_status'] = 'not_submitted'
                context['verification_badge'] = 'bg-secondary'
        
        return render(request, 'dashboards/vendor/vendor_dashboard.html', context)
        
    except VendorProfile.DoesNotExist:
        messages.error(request, 'Vendor profile not found. Please complete your registration.')
        return redirect('vendor_kyc')


@login_required
def vendor_kyc_view(request):
    """Vendor KYC submission form"""
    if not request.user.groups.filter(name='VENDOR').exists():
        messages.error(request, 'Access denied. Vendor accounts only.')
        return redirect('dashboard')
    
    try:
        vendor_profile = VendorProfile.objects.get(user=request.user)
        
        # Check if vendor is already verified
        if vendor_profile.is_verified:
            messages.info(request, 'Your KYC is already verified.')
            return redirect('vendor_dashboard')
        
        # Check if vendor has already submitted KYC
        try:
            existing_kyc = VendorKYC.objects.get(vendor=vendor_profile)
            
            # If KYC exists, redirect based on status
            if existing_kyc.is_approved is False and existing_kyc.reviewed_at is None:
                # Pending review
                messages.info(
                    request, 
                    'Your KYC documents are currently under review. '
                    'You will be notified once verification is complete.'
                )
                return redirect('vendor_kyc_pending')
            elif existing_kyc.is_approved is False and existing_kyc.reviewed_at is not None:
                # Rejected
                messages.warning(
                    request, 
                    'Your KYC verification was not approved. '
                    'Please contact support for assistance.'
                )
                return redirect('vendor_kyc_rejected')
                
        except VendorKYC.DoesNotExist:
            # No KYC exists - proceed to form
            pass
            
    except VendorProfile.DoesNotExist:
        vendor_profile = VendorProfile.objects.create(user=request.user, is_verified=False)
    
    # Clear any existing KYC session data on GET request
    if request.method == 'GET':
        session_keys = ['kyc_business_name', 'kyc_market_location', 'kyc_document_type', 'kyc_submitted_date']
        for key in session_keys:
            if key in request.session:
                del request.session[key]
    
    if request.method == 'POST':
        form = VendorKYCForm(request.POST, request.FILES)
        if form.is_valid():
            # Double-check that no KYC exists before creating (security)
            if VendorKYC.objects.filter(vendor=vendor_profile).exists():
                messages.error(request, 'KYC documents have already been submitted.')
                return redirect('vendor_kyc_pending')
            
            # Get the selected market
            market = form.cleaned_data['market']
            stall_number = form.cleaned_data.get('stall_number', '')
            
            # Combine market name with stall number for the market_location field
            market_location = market.name
            if stall_number:
                market_location = f"{market.name}, {stall_number}"
            
            # Get document type display value
            kyc_type_display = dict(form.fields['kyc_type'].choices).get(form.cleaned_data['kyc_type'], '')
            
            # Create KYC record
            kyc = VendorKYC.objects.create(
                vendor=vendor_profile,
                id_type=form.cleaned_data['kyc_type'],
                id_document=form.cleaned_data['document_image'],
                business_name=form.cleaned_data['business_name'],
                market_location=market_location
            )
            
            # ========== SEND NOTIFICATIONS TO ADMINS ==========
            try:
                from notifications.services import NotificationService
                import logging
                logger = logging.getLogger(__name__)
                
                # 1. Notify admins about new vendor registration
                admin_count = NotificationService.notify_admin_new_vendor(vendor_profile)
                logger.info(f"Admin notifications sent to {admin_count} admins for new vendor: {vendor_profile.user.username}")
                
                # 2. Notify admins about new KYC submission
                kyc_count = NotificationService.notify_admin_vendor_kyc(kyc)
                logger.info(f"Admin notifications sent to {kyc_count} admins for KYC submission: {kyc.id}")
                
                # Optional: Send a test notification to the vendor (to confirm submission)
                # This is not required but can be helpful for testing
                NotificationService.create_notification(
                    recipient=request.user,
                    notification_type='vendor_kyc_pending',
                    title='KYC Submitted Successfully',
                    message='Your KYC documents have been submitted and are now under review. You will be notified once verification is complete.',
                    related_object=kyc,
                    priority='medium',
                    action_url=reverse('vendor_kyc_pending')
                )
                
            except Exception as e:
                # Log the error but don't stop the process - KYC is still submitted
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send admin notifications: {str(e)}", exc_info=True)
                # You could also add a debug message for development
                if settings.DEBUG:
                    print(f"⚠️ Notification error: {str(e)}")
            
            # Store submission details in session for the success modal
            request.session['kyc_business_name'] = form.cleaned_data['business_name']
            request.session['kyc_market_location'] = market_location
            request.session['kyc_document_type'] = kyc_type_display
            
            # Format current date and time
            from django.utils import timezone
            now = timezone.now()
            request.session['kyc_submitted_date'] = now.strftime('%B %d, %Y at %I:%M %p')
            
            # Set session expiry (optional - clear after 1 hour or when browser closes)
            request.session.set_expiry(3600)  # 1 hour
            
            messages.success(
                request, 
                'KYC submitted successfully! Your documents are under review. '
                'You will be notified once verification is complete.'
            )
            
            # Return JSON response for AJAX or redirect for regular form
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'KYC submitted successfully!',
                    'redirect_url': reverse('vendor_kyc_pending')
                })
            return redirect('vendor_kyc_pending')  # Redirect to pending page after submission
        else:
            # Form is invalid
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        form = VendorKYCForm()
    
    return render(request, 'accounts/vendor_kyc.html', {'form': form})

@login_required
def vendor_kyc_pending_view(request):
    """Show pending KYC status page"""
    if not request.user.groups.filter(name='VENDOR').exists():
        return redirect('dashboard')
    
    try:
        vendor_profile = VendorProfile.objects.get(user=request.user)
        kyc = VendorKYC.objects.get(vendor=vendor_profile)
        
        context = {
            'kyc': kyc,
            'submitted_date': kyc.submitted_at,
            'estimated_completion': kyc.submitted_at + timezone.timedelta(hours=48)
        }
        return render(request, 'accounts/vendor_kyc_pending.html', context)
        
    except (VendorProfile.DoesNotExist, VendorKYC.DoesNotExist):
        messages.warning(request, 'No KYC submission found. Please complete KYC verification.')
        return redirect('vendor_kyc')


@login_required
def vendor_kyc_rejected_view(request):
    """Show rejected KYC status page"""
    if not request.user.groups.filter(name='VENDOR').exists():
        return redirect('dashboard')
    
    try:
        vendor_profile = VendorProfile.objects.get(user=request.user)
        kyc = VendorKYC.objects.get(vendor=vendor_profile)
        
        context = {
            'kyc': kyc,
            'rejection_reason': kyc.rejection_reason if hasattr(kyc, 'rejection_reason') else None
        }
        return render(request, 'accounts/vendor_kyc_rejected.html', context)
        
    except (VendorProfile.DoesNotExist, VendorKYC.DoesNotExist):
        messages.warning(request, 'No KYC submission found.')
        return redirect('vendor_kyc')


def kyc_terms_view(request):
    """Display KYC verification terms"""
    return render(request, 'accounts/kyc_terms.html')