# accounts/views/auth_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import IntegrityError
from django.urls import reverse
import logging
import smtplib

from ..forms import (
    UserRegistrationForm, 
    PasswordResetRequestForm,
    SetPasswordForm
)
from ..models import (
    ConsumerProfile, 
    VendorProfile, 
    EmailVerification, 
    PasswordReset,
    RateLimit
)
from ..utils import (
    send_verification_email, 
    send_password_reset_email,
    send_welcome_email
)

logger = logging.getLogger(__name__)

# Rate limit helper
def render_rate_limit_page(request, action, block_info):
    """Render rate limit exceeded page"""
    context = {
        'action': action,
        'action_display': dict(RateLimit.ACTION_CHOICES).get(action, action),
        'minutes_remaining': block_info.get('minutes_remaining', 0),
        'blocked_until': block_info.get('blocked_until'),
        'attempts': block_info.get('attempts', 0),
    }
    return render(request, 'accounts/rate_limit_exceeded.html', context, status=429)

# ============================================================================
# REGISTRATION AND VERIFICATION VIEWS
# ============================================================================

def register_view(request):
    """Handle user registration with email verification requirement"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create user but set as inactive until email verification
                user = form.save(commit=False)
                user.is_active = False
                user.save()
                
                # Create user profile based on role
                role = form.cleaned_data.get('role')
                
                if role == 'consumer':
                    consumer_group, created = Group.objects.get_or_create(name='CONSUMER')
                    user.groups.add(consumer_group)
                    ConsumerProfile.objects.create(user=user)
                    
                elif role == 'vendor':
                    vendor_group, created = Group.objects.get_or_create(name='VENDOR')
                    user.groups.add(vendor_group)
                    VendorProfile.objects.create(user=user, is_verified=False)
                    
                    # Store phone number in session for KYC form
                    request.session['temp_vendor_id'] = user.id
                    request.session['phone_number'] = form.cleaned_data.get('phone_number')
                
                # Create email verification record
                verification = EmailVerification.objects.create(user=user)
                
                # Send verification email
                try:
                    send_verification_email(user, verification)
                    logger.info(f"Verification email sent to {user.email}")
                    
                    request.session['pending_verification_email'] = user.email
                    
                    messages.success(
                        request, 
                        f"Account created! We've sent a verification link to **{user.email}**."
                    )
                    messages.info(
                        request, 
                        "Please check your inbox (and spam folder) and click the link to activate your account."
                    )
                    
                    return redirect('pending_verification')
                    
                except (ConnectionRefusedError, smtplib.SMTPException, TimeoutError) as e:
                    logger.error(f"Email sending failed for {user.email}: {str(e)}")
                    user.delete()
                    
                    messages.error(
                        request,
                        "We're having trouble with our email system right now. Please try again in a few minutes."
                    )
                    return redirect('register')
                    
            except IntegrityError as e:
                logger.error(f"Integrity error creating user: {str(e)}")
                messages.error(request, "This email is already registered. Please log in instead.")
                return redirect('login')
                
            except Exception as e:
                logger.error(f"Unexpected error in registration: {str(e)}", exc_info=True)
                messages.error(request, "An unexpected error occurred. Please try again.")
                return redirect('register')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        initial_data = {}
        if 'role' in request.GET:
            initial_data['role'] = request.GET.get('role')
        form = UserRegistrationForm(initial=initial_data)
    
    return render(request, 'accounts/register.html', {'form': form})


def verify_email_view(request, token):
    """Verify user's email address and activate account"""
    logger.info(f"Email verification attempt with token: {token}")
    
    try:
        verification = get_object_or_404(EmailVerification, token=token, is_used=False)
        
        if not verification.is_valid():
            logger.warning(f"Expired verification token: {token}")
            messages.error(
                request, 
                "This verification link has expired. Please request a new one."
            )
            return redirect('resend_verification')
        
        user = verification.user
        user.is_active = True
        user.save()
        
        verification.is_used = True
        verification.save()
        
        logger.info(f"User {user.email} verified successfully")
        
        try:
            if user.groups.filter(name='VENDOR').exists():
                send_welcome_email(user, role='vendor')
            else:
                send_welcome_email(user, role='consumer')
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
        
        login(request, user, backend='accounts.backends.EmailAuthBackend')
        
        messages.success(request, "Your email has been verified successfully! You are now logged in.")
        
        if user.groups.filter(name='VENDOR').exists():
            messages.info(request, "Please complete your KYC verification to start selling.")
            return redirect('vendor_kyc')
        else:
            return redirect('dashboard')
            
    except Exception as e:
        logger.error(f"Error in email verification: {str(e)}", exc_info=True)
        messages.error(request, "Invalid verification link. Please request a new one.")
        return redirect('resend_verification')


def resend_verification_view(request):
    """Resend verification email with rate limiting"""
    if request.method == "POST":
        email = request.POST.get("email")
        
        # Validate email
        if not email:
            messages.error(request, "Please provide an email address.")
            return redirect('resend_verification')
        
        # Check rate limit
        is_allowed, block_info = RateLimit.check_rate_limit(email, 'email_verification')
        
        if not is_allowed:
            return render_rate_limit_page(request, 'email_verification', block_info)
        
        try:
            # Try to find inactive user first
            user = User.objects.get(email=email, is_active=False)
            
        except User.DoesNotExist:
            try:
                # Check if user exists but is active (already verified)
                user = User.objects.get(email=email, is_active=True)
                # User is already active - redirect to login with info
                messages.info(request, "This account is already verified. Please log in.")
                return redirect('login')
                
            except User.DoesNotExist:
                # User doesn't exist at all - increment rate limit for security
                rate_limit, created = RateLimit.objects.get_or_create(
                    email=email,
                    action='email_verification'
                )
                rate_limit.increment_attempt()
                
                # Generic message for security
                messages.success(request, "If an account exists, a verification email has been sent.")
                return redirect('login')
        
        # Handle existing inactive user
        try:
            # Check for existing valid verification token
            verification = EmailVerification.objects.filter(
                user=user, 
                is_used=False
            ).first()
            
            if verification and verification.is_valid():
                # Reuse existing valid token
                token = verification.token
                logger.info(f"Reusing existing valid token for {email}")
            else:
                # Mark old token as used if it exists
                if verification:
                    verification.is_used = True
                    verification.save()
                
                # Create new verification token
                verification = EmailVerification.objects.create(user=user)
                token = verification.token
                logger.info(f"Created new verification token for {email}")
            
            # Send verification email
            try:
                send_verification_email(user, verification)
                logger.info(f"Verification email sent to {email}")
                
                # Reset rate limit on successful send
                RateLimit.objects.filter(email=email, action='email_verification').delete()
                
                # Store email in session for the pending verification page
                request.session['pending_verification_email'] = user.email
                
                messages.success(
                    request, 
                    f"A verification email has been sent to {email}. Please check your inbox."
                )
                return redirect('pending_verification')
                
            except Exception as e:
                logger.error(f"Failed to send verification email to {email}: {str(e)}", exc_info=True)
                
                # Increment rate limit for failed send
                rate_limit, created = RateLimit.objects.get_or_create(
                    email=email,
                    action='email_verification'
                )
                rate_limit.increment_attempt()
                
                messages.error(
                    request, 
                    "There was a problem sending the verification email. Please try again later."
                )
                return redirect('resend_verification')
            
        except Exception as e:
            logger.error(f"Error in resend verification for {email}: {str(e)}", exc_info=True)
            
            # Increment rate limit for unexpected errors
            rate_limit, created = RateLimit.objects.get_or_create(
                email=email,
                action='email_verification'
            )
            rate_limit.increment_attempt()
            
            messages.error(request, "An unexpected error occurred. Please try again.")
            return redirect('resend_verification')
    
    # GET request - display the form
    # Pre-fill email from session if available
    initial_email = request.session.get('pending_verification_email', '')
    
    context = {
        'email': initial_email,
    }
    return render(request, "accounts/resend_verification.html", context)


def pending_verification_view(request):
    """Show page informing user that their email is pending verification"""
    email = request.session.get('pending_verification_email')
    
    if not email:
        return redirect('register')
    
    context = {
        'email': email,
        'resend_url': reverse('resend_verification')
    }
    return render(request, "accounts/pending_verification.html", context)

def custom_account_inactive_view(request):
    """Custom view for inactive accounts - redirect to pending verification"""
    # Get email from session or request
    email = request.session.get('pending_verification_email', '')
    
    # If no email in session, try to get from user (if authenticated)
    if not email and request.user.is_authenticated:
        email = request.user.email
    
    # Store in session
    if email:
        request.session['pending_verification_email'] = email
    
    return redirect('pending_verification')

# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def login_view(request):
    """Email-based login view - only allows verified users to log in"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    next_url = request.GET.get('next')
    if next_url:
        request.session['next_url'] = next_url
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'accounts/login.html')
        
        is_allowed, block_info = RateLimit.check_rate_limit(email, 'login')
        
        if not is_allowed:
            return render_rate_limit_page(request, 'login', block_info)
        
        try:
            user = User.objects.get(email=email)
            
            if not user.is_active:
                verification = EmailVerification.objects.filter(
                    user=user, 
                    is_used=False
                ).first()
                
                if verification and verification.is_valid():
                    request.session['pending_verification_email'] = email
                    messages.warning(
                        request,
                        "Your email is not verified yet. Please check your inbox for the verification link."
                    )
                    return redirect('pending_verification')
                else:
                    if verification:
                        verification.is_used = True
                        verification.save()
                    
                    new_verification = EmailVerification.objects.create(user=user)
                    send_verification_email(user, new_verification)
                    
                    request.session['pending_verification_email'] = email
                    messages.info(
                        request,
                        "A new verification email has been sent. Please verify your email to log in."
                    )
                    return redirect('pending_verification')
                    
        except User.DoesNotExist:
            pass
        
        user = authenticate(request, email=email, password=password)
        
        if user is not None and user.is_active:
            RateLimit.objects.filter(email=email, action='login').delete()
            
            login(request, user)
            
            if remember_me:
                request.session.set_expiry(2592000)
            else:
                request.session.set_expiry(0)
            
            if user.groups.filter(name='VENDOR').exists():
                try:
                    vendor_profile = VendorProfile.objects.get(user=user)
                    if not vendor_profile.is_verified:
                        messages.info(
                            request, 
                            'Your vendor account is pending verification. '
                            'Please complete KYC to access vendor features.'
                        )
                        return redirect('vendor_kyc')
                except VendorProfile.DoesNotExist:
                    VendorProfile.objects.create(user=user, is_verified=False)
            
            messages.success(request, f'Welcome back, {user.first_name or "to MarketLens"}!')
            
            redirect_to = (
                request.POST.get('next') or 
                request.session.pop('next_url', None) or 
                request.GET.get('next', 'dashboard')
            )
            return redirect(redirect_to)
        else:
            rate_limit, created = RateLimit.objects.get_or_create(
                email=email,
                action='login'
            )
            rate_limit.increment_attempt()
            
            messages.error(request, 'Invalid email or password. Please try again.')
    
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """Log out the current user"""
    username = request.user.username
    logout(request)
    logger.info(f"User {username} logged out")
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')


# ============================================================================
# PASSWORD MANAGEMENT VIEWS
# ============================================================================

def password_reset_request_view(request):
    """Request password reset email with rate limiting"""
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            
            is_allowed, block_info = RateLimit.check_rate_limit(email, 'password_reset')
            
            if not is_allowed:
                return render_rate_limit_page(request, 'password_reset', block_info)
            
            try:
                user = User.objects.get(email=email, is_active=True)
                
                password_reset = PasswordReset.objects.create(user=user)
                
                try:
                    send_password_reset_email(user, password_reset)
                    
                    RateLimit.objects.filter(email=email, action='password_reset').delete()
                    
                    messages.success(
                        request, 
                        "Password reset instructions have been sent to your email."
                    )
                    return redirect('login')
                    
                except Exception as e:
                    logger.error(f"Failed to send password reset email: {str(e)}")
                    
                    rate_limit, created = RateLimit.objects.get_or_create(
                        email=email,
                        action='password_reset'
                    )
                    rate_limit.increment_attempt()
                    
                    messages.error(
                        request, 
                        "There was an error sending the reset email. Please try again."
                    )
                    password_reset.is_used = True
                    password_reset.save()
                    
            except User.DoesNotExist:
                rate_limit, created = RateLimit.objects.get_or_create(
                    email=email,
                    action='password_reset'
                )
                rate_limit.increment_attempt()
                
                messages.success(
                    request, 
                    "If an account exists with this email, you'll receive reset instructions."
                )
                return redirect('login')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, "accounts/password_reset_request.html", {"form": form})


def password_reset_confirm_view(request, token):
    """Confirm password reset and set new password"""
    try:
        password_reset = PasswordReset.objects.get(token=token, is_used=False)
        
        if not password_reset.is_valid():
            messages.error(request, "The password reset link has expired. Please request a new one.")
            return redirect("password_reset_request")
        
        user = password_reset.user
        
        if request.method == "POST":
            form = SetPasswordForm(request.POST)
            
            if form.is_valid():
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                
                password_reset.is_used = True
                password_reset.save()
                
                RateLimit.objects.filter(email=user.email, action='password_reset').delete()
                
                messages.success(request, "Your password has been reset successfully! You can now log in.")
                return redirect("login")
        else:
            form = SetPasswordForm()
        
        return render(request, "accounts/password_reset_confirm.html", {
            "form": form,
            "validlink": True,
            "email": user.email
        })
        
    except PasswordReset.DoesNotExist:
        messages.error(request, "Invalid password reset link.")
        return redirect("password_reset_request")


@login_required
def password_change_view(request):
    """Allow logged-in users to change their password"""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            
            messages.success(request, "Your password was successfully changed!")
            return redirect("dashboard")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, "accounts/password_change.html", {"form": form})


# AJAX endpoints
@csrf_exempt
def check_username(request):
    """Check username availability"""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        exists = User.objects.filter(username__iexact=username).exists()
        return JsonResponse({'available': not exists, 'username': username})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def check_email(request):
    """Check email availability"""
    if request.method == 'POST':
        email = request.POST.get('email', '')
        exists = User.objects.filter(email__iexact=email).exists()
        return JsonResponse({'available': not exists, 'email': email})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def social_complete_profile_view(request):
    """Allow users who signed up with Google to select their role and complete profile"""
    print("\n" + "="*50)
    print("🟡 SOCIAL_COMPLETE_PROFILE VIEW CALLED")
    print("="*50)
    
    user = request.user
    print(f"User: {user.email}")
    print(f"Has groups: {user.groups.filter(name__in=['CONSUMER', 'VENDOR']).exists()}")
    
    # If user already has a role, redirect to dashboard
    if user.groups.filter(name__in=['CONSUMER', 'VENDOR']).exists():
        print("✅ User already has role, redirecting to dashboard")
        return redirect('dashboard')
    
    if request.method == 'POST':
        print("\n📝 POST request received")
        role = request.POST.get('role')
        print(f"Selected role: {role}")
        
        if not role:
            messages.error(request, "Please select an account type.")
            return render(request, 'accounts/social_complete_profile.html', {
                'email': user.email,
                'first_name': request.POST.get('first_name', user.first_name),
                'last_name': request.POST.get('last_name', user.last_name),
            })
        
        # Update user details
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        
        # Set password if provided
        password = request.POST.get('password1')
        if password:
            user.set_password(password)
            print("✅ Password set")
        
        user.save()
        print(f"✅ User updated: {user.first_name} {user.last_name}")
        
        # Re-login the user to maintain session
        from django.contrib.auth import login
        login(request, user, backend='accounts.backends.EmailAuthBackend')
        print("✅ User re-logged in")
        
        # Add user to appropriate group and create profile
        from django.contrib.auth.models import Group
        from ..models import ConsumerProfile, VendorProfile
        
        if role == 'consumer':
            print("👤 Creating consumer account")
            # Add to Consumer group
            consumer_group, _ = Group.objects.get_or_create(name='CONSUMER')
            user.groups.add(consumer_group)
            
            # Create Consumer Profile (check if exists first)
            if not ConsumerProfile.objects.filter(user=user).exists():
                ConsumerProfile.objects.create(user=user)
                print("✅ Consumer profile created")
            else:
                print("⚠️ Consumer profile already exists")
            
            # Send consumer welcome email
            try:
                from ..utils import send_welcome_email
                send_welcome_email(user, role='consumer')
                print("✅ Welcome email sent to consumer")
            except Exception as e:
                print(f"❌ Failed to send welcome email: {str(e)}")
            
            messages.success(request, "Welcome to MarketLens! Your shopper account is ready.")
            return redirect('dashboard')
            
        elif role == 'vendor':
            print("🏪 Creating vendor account")
            # Add to Vendor group
            vendor_group, _ = Group.objects.get_or_create(name='VENDOR')
            user.groups.add(vendor_group)
            
            # Create Vendor Profile (check if exists first)
            if not VendorProfile.objects.filter(user=user).exists():
                VendorProfile.objects.create(user=user, is_verified=False)
                print("✅ Vendor profile created")
            else:
                print("⚠️ Vendor profile already exists")
            
            # Send vendor welcome email
            try:
                from ..utils import send_welcome_email
                send_welcome_email(user, role='vendor')
                print("✅ Welcome email sent to vendor")
            except Exception as e:
                print(f"❌ Failed to send welcome email: {str(e)}")
            
            messages.success(
                request, 
                "Welcome to MarketLens! Your vendor account has been created. "
                "Please complete KYC verification to start selling."
            )
            return redirect('vendor_kyc')
    
    # GET request - show the form
    print("\n📞 GET request - rendering form")
    context = {
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }
    print(f"Context: {context}")
    
    return render(request, 'accounts/social_complete_profile.html', context)


from django.utils import timezone
from datetime import timedelta
from ..models import RateLimit

@login_required
def password_change_view(request):
    """Allow logged-in users to change their password with rate limiting"""
    user = request.user
    
    # Define rate limit for password changes (3 per 2 weeks)
    PASSWORD_CHANGE_LIMIT = 3
    PASSWORD_CHANGE_WINDOW_DAYS = 14  # 2 weeks
    
    # Get or create rate limit record for password changes
    rate_limit, created = RateLimit.objects.get_or_create(
        email=user.email,
        action='password_change',
        defaults={
            'attempt_count': 0,
            'first_attempt': timezone.now()
        }
    )
    
    # Check if user is currently blocked
    if rate_limit.blocked_until and rate_limit.blocked_until > timezone.now():
        days_remaining = (rate_limit.blocked_until - timezone.now()).days
        hours_remaining = ((rate_limit.blocked_until - timezone.now()).seconds // 3600)
        
        if days_remaining > 0:
            block_message = f"Too many password change attempts. Please try again in {days_remaining} day(s)."
        else:
            block_message = f"Too many password change attempts. Please try again in {hours_remaining} hour(s)."
        
        messages.error(request, block_message)
        return render(request, "accounts/change_password.html", {"form": PasswordChangeForm(request.user)})
    
    # Check if we're outside the time window (2 weeks)
    window_start = timezone.now() - timedelta(days=PASSWORD_CHANGE_WINDOW_DAYS)
    
    if rate_limit.first_attempt < window_start:
        # Reset the counter if outside the time window
        rate_limit.attempt_count = 0
        rate_limit.first_attempt = timezone.now()
        rate_limit.blocked_until = None
        rate_limit.save()
    
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        
        if form.is_valid():
            # Save the new password
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            
            # Reset rate limit on successful password change
            rate_limit.attempt_count = 0
            rate_limit.first_attempt = timezone.now()
            rate_limit.blocked_until = None
            rate_limit.save()
            
            messages.success(request, "Your password was changed successfully!")
            return redirect("profile")
        else:
            # Increment attempt count on failed attempt
            rate_limit.attempt_count += 1
            rate_limit.last_attempt = timezone.now()
            
            # Check if exceeded limit
            if rate_limit.attempt_count >= PASSWORD_CHANGE_LIMIT:
                # Block for 2 weeks (same as window)
                rate_limit.blocked_until = timezone.now() + timedelta(days=PASSWORD_CHANGE_WINDOW_DAYS)
                messages.error(
                    request, 
                    f"You have exceeded the maximum number of password change attempts. "
                    f"Please try again in {PASSWORD_CHANGE_WINDOW_DAYS} days."
                )
            else:
                remaining = PASSWORD_CHANGE_LIMIT - rate_limit.attempt_count
                messages.warning(
                    request,
                    f"Invalid password. You have {remaining} attempt(s) remaining "
                    f"in the next {PASSWORD_CHANGE_WINDOW_DAYS} days."
                )
            
            rate_limit.save()
            
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = PasswordChangeForm(request.user)
    
    # Pass rate limit info to template for display
    remaining_attempts = max(0, PASSWORD_CHANGE_LIMIT - rate_limit.attempt_count)
    
    context = {
        'form': form,
        'remaining_attempts': remaining_attempts,
        'total_limit': PASSWORD_CHANGE_LIMIT,
        'window_days': PASSWORD_CHANGE_WINDOW_DAYS,
    }
    
    return render(request, "accounts/change_password.html", context)