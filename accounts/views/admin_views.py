# accounts/views/admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime, timedelta

from ..models import ConsumerProfile, VendorProfile
from vendor.models import VendorKYC, VendorProduct
from market.models import Product, Market, Category
from market.forms import CategoryForm, MarketForm


from django.core.paginator import Paginator
from django.utils import timezone
from ..models import CategoryRequest
from notifications.services import NotificationService

import logging

logger = logging.getLogger(__name__)


@staff_member_required
def admin_dashboard_view(request):
    """Main admin dashboard with system overview"""
    
    # System Statistics
    total_users = User.objects.count()
    total_vendors = VendorProfile.objects.count()
    total_consumers = ConsumerProfile.objects.count()
    total_products = Product.objects.count()
    total_markets = Market.objects.count()
    
    # KYC Statistics
    pending_kyc = VendorKYC.objects.filter(is_approved=False).count()
    approved_kyc = VendorKYC.objects.filter(is_approved=True).count()
    
    # Recent Activity - with role information
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_users_data = []
    for user in recent_users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined,
            'groups': list(user.groups.values_list('name', flat=True)),
        }
        
        # Determine role
        if user.is_staff:
            user_data['role_display'] = 'Admin'
        elif 'VENDOR' in user_data['groups']:
            user_data['role_display'] = 'Vendor'
        elif 'CONSUMER' in user_data['groups']:
            user_data['role_display'] = 'Consumer'
        elif not user.is_active:
            user_data['role_display'] = 'Pending Email'
        else:
            user_data['role_display'] = 'No Role'
        
        recent_users_data.append(user_data)
    
    recent_vendors = VendorProfile.objects.select_related('user').order_by('-created_at')[:5]
    
    # Vendor Product Stats
    total_vendor_products = VendorProduct.objects.count()
    
    # Recent KYC submissions
    recent_kyc = VendorKYC.objects.select_related('vendor__user').order_by('-submitted_at')[:5]
    
    context = {
        'total_users': total_users,
        'total_vendors': total_vendors,
        'total_consumers': total_consumers,
        'total_products': total_products,
        'total_markets': total_markets,
        'pending_kyc': pending_kyc,
        'approved_kyc': approved_kyc,
        'total_vendor_products': total_vendor_products,
        'recent_users': recent_users_data,  # Now using the processed data
        'recent_vendors': recent_vendors,
        'recent_kyc': recent_kyc,
    }
    return render(request, 'dashboards/admin/dashboard.html', context)


# ============= USER MANAGEMENT =============

@staff_member_required
def admin_users_view(request):
    """View all users with filtering"""
    
    role = request.GET.get('role', 'all')
    search = request.GET.get('search', '')
    
    users = User.objects.all().select_related()
    
    if role == 'vendors':
        users = users.filter(groups__name='VENDOR')
    elif role == 'consumers':
        users = users.filter(groups__name='CONSUMER')
    elif role == 'admins':
        users = users.filter(is_staff=True)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Annotate users with their role information and profile pictures
    user_list = []
    for user in users:
        # Get profile picture
        profile_picture = None
        business_name = ''
        try:
            if hasattr(user, 'profile'):
                profile_picture = user.profile.profile_picture
        except:
            pass
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined,
            'groups': list(user.groups.values_list('name', flat=True)),
            'profile_picture': profile_picture,
        }
        
        # Determine role
        if user.is_staff:
            user_data['role_display'] = 'Admin'
            user_data['role_badge'] = 'bg-danger'
        elif 'VENDOR' in user_data['groups']:
            user_data['role_display'] = 'Vendor'
            user_data['role_badge'] = 'bg-primary'
            
            # Get vendor business name
            try:
                vendor_profile = VendorProfile.objects.get(user=user)
                user_data['business_name'] = vendor_profile.business_name if hasattr(vendor_profile, 'business_name') else ''
            except VendorProfile.DoesNotExist:
                user_data['business_name'] = ''
                
        elif 'CONSUMER' in user_data['groups']:
            user_data['role_display'] = 'Consumer'
            user_data['role_badge'] = 'bg-success'
        elif not user.is_active:
            user_data['role_display'] = 'Pending Email'
            user_data['role_badge'] = 'bg-secondary'
        else:
            user_data['role_display'] = 'No Role'
            user_data['role_badge'] = 'bg-secondary'
        
        # Get vendor KYC status if applicable
        if 'VENDOR' in user_data['groups']:
            try:
                vendor_profile = VendorProfile.objects.get(user=user)
                kyc = VendorKYC.objects.filter(vendor=vendor_profile).first()
                user_data['kyc_status'] = kyc
                if kyc:
                    if kyc.is_approved:
                        user_data['kyc_display'] = 'Verified'
                        user_data['kyc_badge'] = 'bg-success'
                    else:
                        user_data['kyc_display'] = 'Pending'
                        user_data['kyc_badge'] = 'bg-warning'
                else:
                    user_data['kyc_display'] = 'Not Submitted'
                    user_data['kyc_badge'] = 'bg-secondary'
            except VendorProfile.DoesNotExist:
                user_data['kyc_status'] = None
                user_data['kyc_display'] = 'No Profile'
                user_data['kyc_badge'] = 'bg-secondary'
        else:
            user_data['kyc_display'] = 'N/A'
            user_data['kyc_badge'] = 'bg-secondary'
        
        user_list.append(user_data)
    
    context = {
        'users': user_list,
        'current_role': role,
        'search': search,
        'total_count': len(user_list),
    }
    return render(request, 'dashboards/admin/users.html', context)


@staff_member_required
def admin_user_detail_view(request, user_id):
    """View detailed user information"""
    
    user = get_object_or_404(User, id=user_id)
    
    # Get profile information
    try:
        profile = user.profile
        profile_picture = profile.profile_picture
        phone_number = profile.phone_number
    except:
        profile = None
        profile_picture = None
        phone_number = ''
    
    # Base context with common user info
    context = {
        'user': user,
        'profile': profile,
        'profile_picture': profile_picture,
        'phone_number': phone_number,
        'user_type': 'UNKNOWN',
        'date_joined': user.date_joined,
        'last_login': user.last_login,
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'groups': list(user.groups.values_list('name', flat=True)),
    }
    
    # Determine role display
    if user.is_staff:
        context['role_display'] = 'Admin'
        context['role_badge'] = 'bg-danger'
    elif 'VENDOR' in context['groups']:
        context['role_display'] = 'Vendor'
        context['role_badge'] = 'bg-primary'
    elif 'CONSUMER' in context['groups']:
        context['role_display'] = 'Consumer'
        context['role_badge'] = 'bg-success'
    elif not user.is_active:
        context['role_display'] = 'Pending Email'
        context['role_badge'] = 'bg-secondary'
    else:
        context['role_display'] = 'No Role'
        context['role_badge'] = 'bg-secondary'
    
    # Vendor specific data
    if user.groups.filter(name='VENDOR').exists():
        try:
            vendor_profile = VendorProfile.objects.get(user=user)
            kyc = VendorKYC.objects.filter(vendor=vendor_profile).first()
            products = VendorProduct.objects.filter(vendor=vendor_profile).select_related('product', 'market', 'product__category')
            
            # Get KYC document info
            if kyc:
                context.update({
                    'kyc': kyc,
                    'id_type': kyc.get_id_type_display(),
                    'id_document_url': kyc.id_document.url if kyc.id_document else None,
                    'submitted_at': kyc.submitted_at,
                    'reviewed_at': kyc.reviewed_at,
                    'rejection_reason': kyc.rejection_reason,
                    'is_approved': kyc.is_approved,
                })
            
            context.update({
                'user_type': 'VENDOR',
                'vendor_profile': vendor_profile,
                'business_name': vendor_profile.business_name if hasattr(vendor_profile, 'business_name') else '',
                'market_location': vendor_profile.market_location if hasattr(vendor_profile, 'market_location') else '',
                'vendor_created_at': vendor_profile.created_at,
                'is_verified': vendor_profile.is_verified,
                'products': products,
                'products_count': products.count(),
            })
            
        except VendorProfile.DoesNotExist:
            context.update({
                'user_type': 'VENDOR (Incomplete)',
                'vendor_profile': None,
                'products': [],
                'products_count': 0,
            })
    
    # Consumer specific data
    elif user.groups.filter(name='CONSUMER').exists():
        try:
            consumer_profile = ConsumerProfile.objects.get(user=user)
            context.update({
                'user_type': 'CONSUMER',
                'consumer_profile': consumer_profile,
                'consumer_created_at': consumer_profile.created_at,
            })
        except ConsumerProfile.DoesNotExist:
            context.update({
                'user_type': 'CONSUMER (Incomplete)',
                'consumer_profile': None,
            })
    
    return render(request, 'dashboards/admin/user_detail.html', context)

# ============= VENDOR VERIFICATION =============

@staff_member_required
def admin_vendor_verification_view(request):
    """View all pending vendor verifications"""
    
    pending_kyc = VendorKYC.objects.filter(
        is_approved=False
    ).select_related('vendor__user').order_by('-submitted_at')
    
    # Also show rejected KYC if needed (optional)
    rejected_kyc = VendorKYC.objects.filter(
        is_approved=False,
        reviewed_at__isnull=False
    ).select_related('vendor__user').order_by('-reviewed_at')[:10]
    
    context = {
        'pending_kyc': pending_kyc,
        'rejected_kyc': rejected_kyc,
        'pending_count': pending_kyc.count(),
        'rejected_count': rejected_kyc.count(),
        'total_count': pending_kyc.count() + rejected_kyc.count(),
    }
    return render(request, 'dashboards/admin/vendor_verification.html', context)


from notifications.services import NotificationService
from django.utils import timezone

@staff_member_required
def admin_verify_vendor(request, kyc_id):
    """Approve or reject vendor KYC"""
    
    kyc = get_object_or_404(VendorKYC, id=kyc_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            try:
                kyc.is_approved = True
                kyc.reviewed_at = timezone.now()
                kyc.rejection_reason = ''  # Clear any previous rejection reason
                kyc.save()
                
                # Update vendor profile
                kyc.vendor.is_verified = True
                kyc.vendor.save()
                
                # Send notification to vendor about approval
                try:
                    from notifications.services import NotificationService
                    NotificationService.notify_vendor_kyc_approved(kyc.vendor)
                    logger.info(f"Approval notification sent to vendor {kyc.vendor.user.username}")
                except Exception as e:
                    logger.error(f"Failed to send approval notification: {str(e)}")
                    # Don't stop the process - vendor is still approved
                
                messages.success(request, f'Vendor {kyc.vendor.user.username} has been verified.')
                
            except Exception as e:
                logger.error(f"Error during KYC approval: {str(e)}")
                messages.error(request, f'An error occurred while approving vendor. Please try again.')
            
        elif action == 'reject':
            try:
                reason = request.POST.get('rejection_reason', 'No specific reason provided.')
                
                kyc.is_approved = False
                kyc.reviewed_at = timezone.now()
                kyc.rejection_reason = reason
                kyc.save()
                
                # Ensure vendor is marked as not verified
                kyc.vendor.is_verified = False
                kyc.vendor.save()
                
                # Send notification to vendor with rejection reason
                try:
                    from notifications.services import NotificationService
                    NotificationService.notify_vendor_kyc_rejected(kyc.vendor, reason)
                    logger.info(f"Rejection notification sent to vendor {kyc.vendor.user.username}")
                except Exception as e:
                    logger.error(f"Failed to send rejection notification: {str(e)}")
                    # Don't stop the process - vendor is still rejected
                
                messages.warning(request, f'Vendor {kyc.vendor.user.username} has been rejected.')
                
            except Exception as e:
                logger.error(f"Error during KYC rejection: {str(e)}")
                messages.error(request, f'An error occurred while rejecting vendor. Please try again.')
            
        elif action == 'reset':
            try:
                # Optional: Reset a rejected KYC to pending for resubmission
                kyc.is_approved = False
                kyc.reviewed_at = None
                kyc.rejection_reason = ''
                kyc.save()
                
                # Update vendor profile
                kyc.vendor.is_verified = False
                kyc.vendor.save()
                
                messages.info(request, f'KYC for {kyc.vendor.user.username} has been reset to pending.')
                
            except Exception as e:
                logger.error(f"Error during KYC reset: {str(e)}")
                messages.error(request, f'An error occurred while resetting KYC. Please try again.')
        
        return redirect('admin_vendor_verification')
    
    # For GET request, prepare context
    context = {
        'kyc': kyc,
        'id_type_choices': dict(VendorKYC.ID_TYPE_CHOICES),
        'document_url': kyc.id_document.url if kyc.id_document else None,
        'submitted_date': kyc.submitted_at.strftime('%B %d, %Y at %I:%M %p'),
        'vendor_name': kyc.vendor.user.get_full_name() or kyc.vendor.user.username,
        'vendor_email': kyc.vendor.user.email,
        'business_name': kyc.business_name,
        'market_location': kyc.market_location,
    }
    
    return render(request, 'dashboards/admin/verify_vendor_detail.html', context)


@staff_member_required
def admin_rejected_kyc_view(request):
    """View all rejected KYC submissions"""
    
    rejected_kyc = VendorKYC.objects.filter(
        is_approved=False,
        reviewed_at__isnull=False
    ).select_related('vendor__user').order_by('-reviewed_at')
    
    # Filter by search if provided
    search = request.GET.get('search', '')
    if search:
        rejected_kyc = rejected_kyc.filter(
            Q(vendor__user__username__icontains=search) |
            Q(vendor__user__email__icontains=search) |
            Q(business_name__icontains=search)
        )
    
    context = {
        'rejected_kyc': rejected_kyc,
        'count': rejected_kyc.count(),
        'search': search,
    }
    return render(request, 'dashboards/admin/rejected_kyc.html', context)


# ============= VENDOR PRODUCTS MANAGEMENT =============

@staff_member_required
def admin_vendor_products_view(request):
    """View all vendor products"""
    
    vendor_products = VendorProduct.objects.select_related(
        'vendor__user', 'product', 'market'
    ).order_by('-last_updated')
    
    vendor_id = request.GET.get('vendor')
    market_id = request.GET.get('market')
    
    if vendor_id:
        vendor_products = vendor_products.filter(vendor_id=vendor_id)
    if market_id:
        vendor_products = vendor_products.filter(market_id=market_id)
    
    # Get filter options
    from accounts.models import VendorProfile
    from market.models import Market
    
    vendors = VendorProfile.objects.filter(
        products__isnull=False
    ).distinct().select_related('user')
    
    markets = Market.objects.filter(
        vendorproduct__isnull=False
    ).distinct()
    
    context = {
        'vendor_products': vendor_products,
        'vendors': vendors,
        'markets': markets,
        'total_count': vendor_products.count(),
    }
    return render(request, 'dashboards/admin/vendor_products.html', context)


@staff_member_required
def admin_vendor_product_detail_view(request, product_id):
    """View detailed information about a vendor product"""
    
    product = get_object_or_404(VendorProduct, id=product_id)
    
    similar_products = VendorProduct.objects.filter(
        product=product.product
    ).exclude(id=product_id).select_related('vendor__user', 'market')[:5]
    
    context = {
        'product': product,
        'similar_products': similar_products,
    }
    return render(request, 'dashboards/admin/vendor_product_detail.html', context)


# ============= CONSUMER MANAGEMENT =============

@staff_member_required
def admin_consumers_view(request):
    """View all consumers with profile images"""
    
    consumers = ConsumerProfile.objects.select_related('user').all()
    
    search = request.GET.get('search', '')
    if search:
        consumers = consumers.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    # Annotate consumers with profile data
    consumer_list = []
    for consumer in consumers:
        consumer_data = {
            'id': consumer.user.id,
            'username': consumer.user.username,
            'email': consumer.user.email,
            'first_name': consumer.user.first_name,
            'last_name': consumer.user.last_name,
            'is_active': consumer.user.is_active,
            'date_joined': consumer.user.date_joined,
            'last_login': consumer.user.last_login,
            'consumer': consumer,
        }
        
        # Get profile picture
        try:
            if hasattr(consumer.user, 'profile') and consumer.user.profile.profile_picture:
                consumer_data['profile_picture'] = consumer.user.profile.profile_picture.url
            else:
                consumer_data['profile_picture'] = None
        except:
            consumer_data['profile_picture'] = None
        
        consumer_list.append(consumer_data)
    
    context = {
        'consumers': consumer_list,
        'total_count': len(consumer_list),
        'search': search,
    }
    return render(request, 'dashboards/admin/consumers.html', context)


# ============= CATEGORY MANAGEMENT =============

@staff_member_required
def admin_categories_view(request):
    """View all product categories"""
    
    categories = Category.objects.annotate(
        product_count=Count('product')
    ).order_by('name')
    
    search = request.GET.get('search', '')
    if search:
        categories = categories.filter(name__icontains=search)
    
    # Pagination
    limit = request.GET.get('limit', 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    
    paginator = Paginator(categories, limit)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'categories': page_obj,
        'page_obj': page_obj,
        'search': search,
        'limit': limit,
        'total_count': categories.count(),
    }
    return render(request, 'dashboards/admin/categories.html', context)


@staff_member_required
def admin_category_create_view(request):
    """Create a new category"""
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('admin_categories')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'title': 'Create New Category',
    }
    return render(request, 'dashboards/admin/category_form.html', context)


@staff_member_required
def admin_category_update_view(request, category_id):
    """Update an existing category"""
    
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('admin_categories')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'Edit Category: {category.name}',
    }
    return render(request, 'dashboards/admin/category_form.html', context)


@staff_member_required
def admin_category_delete_view(request, category_id):
    """Delete a category"""
    
    category = get_object_or_404(Category, id=category_id)
    product_count = category.product_set.count()
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully.')
        return redirect('admin_categories')
    
    context = {
        'category': category,
        'product_count': product_count,
    }
    return render(request, 'dashboards/admin/category_delete.html', context)


# ============= MARKET MANAGEMENT =============

@staff_member_required
def admin_markets_view(request):
    """View all markets"""
    
    markets = Market.objects.annotate(
        product_count=Count('vendorproduct')
    ).order_by('name')
    
    search = request.GET.get('search', '')
    if search:
        markets = markets.filter(
            Q(name__icontains=search) | 
            Q(location__icontains=search) |
            Q(address__icontains=search)
        )
    
    # Sorting
    sort = request.GET.get('sort', 'name')
    if sort == 'name':
        markets = markets.order_by('name')
    elif sort == 'newest':
        markets = markets.order_by('-created_at')
    elif sort == 'oldest':
        markets = markets.order_by('created_at')
    elif sort == 'products':
        markets = markets.order_by('-product_count')
    
    # Pagination
    limit = request.GET.get('limit', 5)
    try:
        limit = int(limit)
    except ValueError:
        limit = 5
    
    paginator = Paginator(markets, limit)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'markets': page_obj,
        'page_obj': page_obj,
        'search': search,
        'sort': sort,
        'limit': limit,
    }
    return render(request, 'dashboards/admin/markets.html', context)


@staff_member_required
def admin_market_create_view(request):
    """Create a new market"""
    
    if request.method == 'POST':
        form = MarketForm(request.POST, request.FILES)
        if form.is_valid():
            market = form.save()
            messages.success(request, f'Market "{market.name}" created successfully.')
            return redirect('admin_markets')
    else:
        form = MarketForm()
    
    context = {
        'form': form,
        'title': 'Create New Market',
    }
    return render(request, 'dashboards/admin/market_form.html', context)


@staff_member_required
def admin_market_update_view(request, market_id):
    """Update an existing market"""
    
    market = get_object_or_404(Market, id=market_id)
    
    if request.method == 'POST':
        form = MarketForm(request.POST, request.FILES, instance=market)
        if form.is_valid():
            market = form.save()
            messages.success(request, f'Market "{market.name}" updated successfully.')
            return redirect('admin_markets')
    else:
        form = MarketForm(instance=market)
    
    context = {
        'form': form,
        'market': market,
        'title': f'Edit Market: {market.name}',
    }
    return render(request, 'dashboards/admin/market_form.html', context)


@staff_member_required
def admin_market_detail_view(request, market_id):
    """View market details"""
    
    market = get_object_or_404(Market, id=market_id)
    
    vendors = VendorProfile.objects.filter(
        products__market=market
    ).distinct().annotate(
        product_count=Count('products')
    )
    
    products = VendorProduct.objects.filter(
        market=market
    ).select_related('product', 'vendor__user')[:20]
    
    context = {
        'market': market,
        'vendors': vendors,
        'products': products,
        'vendor_count': vendors.count(),
        'product_count': products.count(),
    }
    return render(request, 'dashboards/admin/market_detail.html', context)


@staff_member_required
def admin_market_delete_view(request, market_id):
    """Delete a market"""
    
    market = get_object_or_404(Market, id=market_id)
    product_count = VendorProduct.objects.filter(market=market).count()
    
    if request.method == 'POST':
        market_name = market.name
        market.delete()
        messages.success(request, f'Market "{market_name}" deleted successfully.')
        return redirect('admin_markets')
    
    context = {
        'market': market,
        'product_count': product_count,
    }
    return render(request, 'dashboards/admin/market_delete.html', context)


# ============= REPORTS =============

@staff_member_required
def admin_reports_view(request):
    """Generate system reports"""
    
    days = int(request.GET.get('days', 30))
    since_date = datetime.now() - timedelta(days=days)
    
    new_users = User.objects.filter(date_joined__gte=since_date).count()
    new_vendors = VendorProfile.objects.filter(created_at__gte=since_date).count()
    kyc_approved = VendorKYC.objects.filter(
        reviewed_at__gte=since_date,
        is_approved=True
    ).count()
    product_updates = VendorProduct.objects.filter(
        last_updated__gte=since_date
    ).count()
    
    context = {
        'days': days,
        'new_users': new_users,
        'new_vendors': new_vendors,
        'kyc_approved': kyc_approved,
        'product_updates': product_updates,
    }
    return render(request, 'dashboards/admin/reports.html', context)



@staff_member_required
def admin_category_requests_view(request):
    """View and manage category requests from vendors"""
    
    status_filter = request.GET.get('status', 'pending')
    search = request.GET.get('search', '')
    
    requests = CategoryRequest.objects.select_related(
        'vendor__user', 'reviewed_by'
    )
    
    if status_filter != 'all':
        requests = requests.filter(status=status_filter)
    
    if search:
        requests = requests.filter(
            Q(name__icontains=search) |
            Q(vendor__user__username__icontains=search) |
            Q(vendor__user__email__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(requests, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'pending': CategoryRequest.objects.filter(status='pending').count(),
        'approved': CategoryRequest.objects.filter(status='approved').count(),
        'rejected': CategoryRequest.objects.filter(status='rejected').count(),
        'in_review': CategoryRequest.objects.filter(status='in_review').count(),
        'total': CategoryRequest.objects.count(),
    }
    
    context = {
        'requests': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search': search,
    }
    
    return render(request, 'dashboards/admin/category_requests.html', context)


@staff_member_required
def admin_category_request_detail_view(request, request_id):
    """View and process a single category request"""
    
    category_request = get_object_or_404(
        CategoryRequest.objects.select_related('vendor__user'),
        id=request_id
    )
    
    context = {
        'request': category_request,
    }
    
    return render(request, 'dashboards/admin/category_request_detail.html', context)


@staff_member_required
def admin_process_category_request(request, request_id):
    """Approve or reject a category request"""
    
    category_request = get_object_or_404(CategoryRequest, id=request_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'approve':
            # Approve and create category
            category = category_request.approve(admin_user=request.user, notes=admin_notes)
            
            # Notify vendor
            NotificationService.create_notification(
                recipient=category_request.vendor.user,
                notification_type='vendor_category_approved',
                title=f'Category Request Approved: {category_request.name}',
                message=f'Your request for category "{category_request.name}" has been approved. You can now select it when adding products.',
                priority='high',
                related_object=category_request,
                action_url='/vendor/add-product/'
            )
            
            messages.success(
                request, 
                f'Category "{category_request.name}" has been approved and created successfully.'
            )
            
        elif action == 'reject':
            # Reject the request
            category_request.reject(admin_user=request.user, reason=admin_notes)
            
            # Notify vendor
            NotificationService.create_notification(
                recipient=category_request.vendor.user,
                notification_type='vendor_category_rejected',
                title=f'Category Request Update: {category_request.name}',
                message=f'Your request for category "{category_request.name}" was not approved. {admin_notes}',
                priority='medium',
                related_object=category_request,
            )
            
            messages.info(
                request, 
                f'Category request for "{category_request.name}" has been rejected.'
            )
        
        elif action == 'in_review':
            # Mark as in review
            category_request.status = 'in_review'
            category_request.admin_notes = admin_notes
            category_request.save()
            
            messages.info(request, f'Category request marked as in review.')
        
        return redirect('admin_category_requests')
    
    return redirect('admin_category_request_detail', request_id=request_id)


@staff_member_required
def admin_bulk_process_category_requests(request):
    """Bulk approve/reject multiple category requests"""
    
    if request.method == 'POST':
        action = request.POST.get('bulk_action')
        request_ids = request.POST.getlist('selected_requests')
        
        if not request_ids:
            messages.error(request, 'No requests selected.')
            return redirect('admin_category_requests')
        
        requests = CategoryRequest.objects.filter(id__in=request_ids)
        
        if action == 'approve':
            for cat_request in requests:
                if cat_request.status == 'pending':
                    cat_request.approve(admin_user=request.user)
            
            messages.success(request, f'Approved {requests.count()} category requests.')
        
        elif action == 'reject':
            for cat_request in requests:
                if cat_request.status == 'pending':
                    cat_request.reject(admin_user=request.user)
            
            messages.success(request, f'Rejected {requests.count()} category requests.')
        
        elif action == 'delete':
            requests.delete()
            messages.success(request, f'Deleted {requests.count()} category requests.')
        
        return redirect('admin_category_requests')
    
    return redirect('admin_category_requests')