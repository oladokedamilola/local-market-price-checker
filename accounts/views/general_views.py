from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from ..forms import UserProfileForm
from ..models import VendorProfile, ConsumerProfile, Profile

import logging

logger = logging.getLogger(__name__)


@login_required
def profile_view(request):
    """User profile view - accessible by all authenticated users"""
    user = request.user
    
    # Skip the Google user check for admin users
    if not (user.is_staff or user.is_superuser):
        # Check if this is a Google user who hasn't completed registration
        has_group = user.groups.filter(name__in=['CONSUMER', 'VENDOR']).exists()
        has_profile = ConsumerProfile.objects.filter(user=user).exists() or VendorProfile.objects.filter(user=user).exists()
        
        # If this is a Google user who hasn't set their role (no group and no profile)
        if not has_group and not has_profile:
            print(f"🔄 Google user detected with incomplete profile: {user.email}")
            messages.info(
                request, 
                "Please complete your registration by selecting an account type."
            )
            return redirect('social_complete_profile')
    else:
        print(f"👑 Admin user detected: {user.email} - skipping Google user check")
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        initial_data = {
            'email': user.email,
        }
        form = UserProfileForm(instance=user, initial=initial_data)
    
    is_vendor = user.groups.filter(name='VENDOR').exists()
    is_consumer = user.groups.filter(name='CONSUMER').exists()
    
    # Get profile picture
    try:
        profile = user.profile
        profile_picture_url = profile.get_profile_picture_url()
        phone_number = profile.phone_number
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user)
        profile_picture_url = '/static/images/default-avatar.png'
        phone_number = ''
    
    context = {
        'form': form,
        'is_vendor': is_vendor,
        'is_consumer': is_consumer,
        'profile_picture_url': profile_picture_url,
        'phone_number': phone_number,
    }
    
    if is_vendor:
        try:
            vendor_profile = VendorProfile.objects.get(user=user)
            context['vendor_profile'] = vendor_profile
        except VendorProfile.DoesNotExist:
            pass
    
    return render(request, 'accounts/profile.html', context)


# Add this new view for AJAX profile picture upload (optional)
@login_required
def upload_profile_picture(request):
    """AJAX endpoint for profile picture upload"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        user = request.user
        profile, created = Profile.objects.get_or_create(user=user)
        profile.profile_picture = request.FILES['profile_picture']
        profile.save()
        
        return JsonResponse({
            'success': True,
            'image_url': profile.get_profile_picture_url()
        })
    
    return JsonResponse({'success': False}, status=400)


@login_required
def dashboard_view(request):
    """Main dashboard redirector - sends users to their role-specific dashboards"""
    user = request.user
    
    # Skip the Google user check for admin users
    if not (user.is_staff or user.is_superuser):
        # Check if this is a Google user who hasn't completed registration
        has_group = user.groups.filter(name__in=['CONSUMER', 'VENDOR']).exists()
        has_profile = ConsumerProfile.objects.filter(user=user).exists() or VendorProfile.objects.filter(user=user).exists()
        
        # If this is a Google user who hasn't set their role (no group and no profile)
        if not has_group and not has_profile:
            print(f"🔄 Google user detected with incomplete profile: {user.email}")
            messages.info(
                request, 
                "Please complete your registration by selecting an account type."
            )
            return redirect('social_complete_profile')
    else:
        print(f"👑 Admin user detected: {user.email} - skipping Google user check")
    
    if user.is_staff or user.is_superuser:
        messages.info(request, 'Welcome to the admin dashboard.')
        return redirect('admin_dashboard')
    
    if user.groups.filter(name='VENDOR').exists():
        try:
            vendor_profile = VendorProfile.objects.get(user=user)
            if not vendor_profile.is_verified:
                messages.warning(request, 'Your vendor account is pending verification. Please complete KYC.')
                return redirect('vendor_kyc')
        except VendorProfile.DoesNotExist:
            VendorProfile.objects.create(user=user)
            messages.info(request, 'Please complete your vendor KYC verification.')
            return redirect('vendor_kyc')
        
        messages.success(request, f'Welcome back, {user.first_name or "Vendor"}!')
        return redirect('vendor_dashboard')
    
    elif user.groups.filter(name='CONSUMER').exists():
        messages.success(request, f'Welcome back, {user.first_name or "Shopper"}!')
        return redirect('consumer_dashboard')
    
    else:
        messages.warning(request, 'Please complete your profile setup.')
        return redirect('profile')