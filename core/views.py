# core/views.py
import json
import uuid
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Min, Max, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from vendor.models import VendorProduct
from market.models import Market, Product, Category
from accounts.models import PriceAlert, FavoriteProduct, FavoriteVendor, VendorProfile
from .models import Comparison

# Session key for storing comparison products
COMPARISON_SESSION_KEY = 'comparison_products'


# ============================================================================
# SEARCH & PRODUCT VIEWS
# ============================================================================

@login_required
def search_view(request):
    """
    Search page for consumers to find products across markets.
    """
    # Check if user is a vendor - they shouldn't access this page
    if request.user.groups.filter(name='VENDOR').exists():
        messages.info(request, 'Vendors cannot access the consumer search page. Use your vendor dashboard to manage your products.')
        return redirect('vendor_dashboard')
    
    # Get search parameters
    query = request.GET.get('q', '')
    market_id = request.GET.get('market', '')
    
    # Get comparison products from session
    comparison_ids = request.session.get(COMPARISON_SESSION_KEY, [])
    
    # Get all markets for filter dropdown
    markets = Market.objects.filter(is_active=True).order_by('name')
    
    # Base queryset - only show products from verified vendors
    products = VendorProduct.objects.filter(
        vendor__is_verified=True
    ).select_related(
        'product', 'market', 'vendor__user'
    ).order_by('-last_updated')
    
    # Apply search filter
    if query:
        products = products.filter(
            Q(product__name__icontains=query) |
            Q(product__description__icontains=query)
        )
    
    # Apply market filter
    if market_id:
        products = products.filter(market_id=market_id)
    
    # Annotate whether product is in comparison
    for product in products:
        product.in_comparison = product.id in comparison_ids
    
    # Pagination - 12 products per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'markets': markets,
        'selected_market': market_id,
        'query': query,
        'total_results': products.count(),
        'comparison_count': len(comparison_ids),
        'comparison_ids': comparison_ids,
    }
    
    return render(request, 'core/search.html', context)


@login_required
def product_detail_view(request, product_id):
    """View product details - only for consumers"""
    
    # Redirect vendors away
    if request.user.groups.filter(name='VENDOR').exists():
        messages.info(request, 'Vendors cannot view product details.')
        return redirect('vendor_dashboard')
    
    product = get_object_or_404(
        VendorProduct.objects.select_related(
            'product', 'market', 'vendor__user', 'product__category'
        ),
        id=product_id,
        vendor__is_verified=True  # Only show products from verified vendors
    )
    
    # Track recently viewed products
    recently_viewed = request.session.get('recently_viewed_products', [])
    if product_id not in recently_viewed:
        recently_viewed.insert(0, product_id)
        request.session['recently_viewed_products'] = recently_viewed[:10]
    
    # Find same product from other vendors for comparison
    other_vendors = VendorProduct.objects.filter(
        product=product.product,
        vendor__is_verified=True
    ).exclude(
        id=product_id
    ).select_related(
        'vendor__user', 'market'
    ).order_by('price')
    
    # Calculate price statistics
    all_prices = list(VendorProduct.objects.filter(
        product=product.product,
        vendor__is_verified=True
    ).values_list('price', flat=True))
    
    price_stats = {
        'min': min(all_prices) if all_prices else product.price,
        'max': max(all_prices) if all_prices else product.price,
        'avg': sum(all_prices) / len(all_prices) if all_prices else product.price,
        'count': len(all_prices)
    }
    
    # Determine if current product has best price
    is_best_price = product.price <= price_stats['min']
    
    # Get similar products in same category
    similar_products = VendorProduct.objects.filter(
        product__category=product.product.category,
        vendor__is_verified=True
    ).exclude(
        id=product_id
    ).select_related(
        'product', 'vendor__user', 'market'
    ).order_by('?')[:5]
    
    # Check if product is in user's favorites
    from accounts.models import FavoriteProduct
    is_favorite = FavoriteProduct.objects.filter(
        user=request.user,
        product=product
    ).exists()
    
    # Check if vendor is in user's favorites
    from accounts.models import FavoriteVendor
    is_vendor_favorite = FavoriteVendor.objects.filter(
        user=request.user,
        vendor=product.vendor
    ).exists()
    
    context = {
        'product': product,
        'other_vendors': other_vendors,
        'price_stats': price_stats,
        'is_best_price': is_best_price,
        'similar_products': similar_products,
        'savings': other_vendors.first().price - product.price if other_vendors and is_best_price else 0,
        'is_favorite': is_favorite,
        'is_vendor_favorite': is_vendor_favorite,
    }
    
    return render(request, 'core/product_detail.html', context)


# ============================================================================
# COMPARISON TOOLS
# ============================================================================

@login_required
def add_to_comparison(request, product_id):
    """Add a product to comparison list"""
    
    # Check if user is a vendor
    if request.user.groups.filter(name='VENDOR').exists():
        return JsonResponse({'error': 'Vendors cannot use comparison'}, status=403)
    
    # Get or create comparison list in session
    comparison_ids = request.session.get(COMPARISON_SESSION_KEY, [])
    
    # Check if product exists and is from verified vendor
    try:
        product = VendorProduct.objects.select_related('product').get(
            id=product_id,
            vendor__is_verified=True
        )
    except VendorProduct.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    
    # Check if already in comparison
    if product_id in comparison_ids:
        return JsonResponse({
            'status': 'already_exists',
            'message': 'Product already in comparison'
        })
    
    # Check if we've reached the limit (max 4 products)
    if len(comparison_ids) >= 4:
        return JsonResponse({
            'error': 'limit_exceeded',
            'message': 'You can only compare up to 4 products at a time'
        }, status=400)
    
    # Add to session
    comparison_ids.append(product_id)
    request.session[COMPARISON_SESSION_KEY] = comparison_ids
    request.session.modified = True
    
    return JsonResponse({
        'status': 'added',
        'message': f'{product.product.name} added to comparison',
        'comparison_count': len(comparison_ids),
        'product_id': product_id
    })


@login_required
def remove_from_comparison(request, product_id):
    """Remove a product from comparison list"""
    
    comparison_ids = request.session.get(COMPARISON_SESSION_KEY, [])
    
    if product_id in comparison_ids:
        comparison_ids.remove(product_id)
        request.session[COMPARISON_SESSION_KEY] = comparison_ids
        request.session.modified = True
        
        try:
            product = VendorProduct.objects.get(id=product_id)
            product_name = product.product.name
        except:
            product_name = "Product"
        
        return JsonResponse({
            'status': 'removed',
            'message': f'{product_name} removed from comparison',
            'comparison_count': len(comparison_ids)
        })
    
    return JsonResponse({'error': 'Product not in comparison'}, status=404)


@login_required
def clear_comparison(request):
    """Clear all products from comparison"""
    request.session[COMPARISON_SESSION_KEY] = []
    request.session.modified = True
    
    messages.success(request, 'Comparison list cleared')
    return redirect(request.META.get('HTTP_REFERER', 'search'))


@login_required
def compare_view(request):
    """View to compare selected products"""
    
    # Check if user is a vendor
    if request.user.groups.filter(name='VENDOR').exists():
        messages.info(request, 'Vendors cannot access the comparison feature.')
        return redirect('vendor_dashboard')
    
    comparison_ids = request.session.get(COMPARISON_SESSION_KEY, [])
    
    if not comparison_ids:
        messages.info(request, 'No products selected for comparison.')
        return redirect('search')
    
    # Get products with all related data
    products = VendorProduct.objects.filter(
        id__in=comparison_ids,
        vendor__is_verified=True
    ).select_related(
        'product', 'market', 'vendor__user'
    )
    
    # Calculate statistics
    stats = {}
    if products:
        prices = [p.price for p in products]
        stats['min_price'] = min(prices)
        stats['max_price'] = max(prices)
        stats['avg_price'] = sum(prices) / len(prices)
        stats['price_diff'] = stats['max_price'] - stats['min_price']
    
    context = {
        'products': products,
        'stats': stats,
        'count': len(products),
    }
    
    return render(request, 'core/compare.html', context)


@login_required
def save_comparison(request):
    """Save current comparison to database"""
    
    if request.method == 'POST':
        comparison_ids = request.session.get(COMPARISON_SESSION_KEY, [])
        name = request.POST.get('name', '')
        
        if not comparison_ids:
            messages.error(request, 'No products to save')
            return redirect('compare')
        
        # Create comparison
        comparison = Comparison.objects.create(
            user=request.user,
            name=name or f"Comparison {Comparison.objects.filter(user=request.user).count() + 1}",
            share_uuid=uuid.uuid4()
        )
        
        # Add products
        products = VendorProduct.objects.filter(id__in=comparison_ids)
        comparison.products.set(products)
        
        messages.success(request, 'Comparison saved successfully!')
        
        return redirect('my_comparisons')
    
    return redirect('compare')


@login_required
def my_comparisons_view(request):
    """View user's saved comparisons with pagination"""
    
    comparisons = Comparison.objects.filter(
        user=request.user
    ).prefetch_related('products__product', 'products__market').order_by('-updated_at')
    
    # Pagination
    paginator = Paginator(comparisons, 9)  # 9 comparisons per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'comparisons': page_obj,
        'page_obj': page_obj,
    }
    
    return render(request, 'core/my_comparisons.html', context)


def shared_comparison_view(request, share_uuid):
    """View a shared comparison (public access)"""
    
    comparison = get_object_or_404(
        Comparison.objects.prefetch_related(
            'products__product', 
            'products__market', 
            'products__vendor__user'
        ),
        share_uuid=share_uuid
    )
    
    products = comparison.products.filter(vendor__is_verified=True)
    
    # Calculate statistics for shared view
    stats = {}
    if products:
        prices = [p.price for p in products]
        stats['min_price'] = min(prices)
        stats['max_price'] = max(prices)
        stats['avg_price'] = sum(prices) / len(prices)
        stats['price_diff'] = stats['max_price'] - stats['min_price']
    
    context = {
        'comparison': comparison,
        'products': products,
        'stats': stats,
        'count': len(products),
        'is_shared': True,
    }
    
    return render(request, 'core/shared_comparison.html', context)


def home(request):
    """Home page view"""
    return render(request, 'home.html')


# ============================================================================
# CONSUMER MARKET & CATEGORY VIEWS
# ============================================================================

@login_required
def market_detail_view(request, market_id):
    """View market details and products available there"""
    
    # Verify consumer access
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    market = get_object_or_404(Market, id=market_id, is_active=True)
    
    # Get products in this market from verified vendors
    products = VendorProduct.objects.filter(
        market=market,
        vendor__is_verified=True
    ).select_related(
        'product', 'vendor__user', 'product__category'
    ).order_by('-last_updated')
    
    # Group products by category
    products_by_category = {}
    for product in products:
        category_name = product.product.category.name if product.product.category else 'Uncategorized'
        if category_name not in products_by_category:
            products_by_category[category_name] = []
        products_by_category[category_name].append(product)
    
    # Get vendors in this market - FIXED VERSION
    # Get unique vendor IDs first
    vendor_ids = products.values_list('vendor', flat=True).distinct()
    
    # Then get vendor details
    from accounts.models import VendorProfile
    from vendor.models import VendorKYC
    
    vendors = []
    for vendor_id in vendor_ids:
        try:
            vendor = VendorProfile.objects.select_related('user').get(id=vendor_id)
            
            # Get KYC info for business name if available
            try:
                kyc = VendorKYC.objects.get(vendor=vendor)
                business_name = kyc.business_name
            except VendorKYC.DoesNotExist:
                business_name = None
            
            vendors.append({
                'id': vendor.id,
                'username': vendor.user.username,
                'full_name': vendor.user.get_full_name() or vendor.user.username,
                'business_name': business_name,
                'is_verified': vendor.is_verified,
                'product_count': products.filter(vendor=vendor).count(),
            })
        except VendorProfile.DoesNotExist:
            continue
    
    # Get popular products in this market (most listed by vendors)
    popular_products = products.values(
        'product__id', 'product__name'
    ).annotate(
        vendor_count=Count('vendor', distinct=True),
        avg_price=Avg('price')
    ).order_by('-vendor_count')[:10]
    
    context = {
        'market': market,
        'products_by_category': products_by_category,
        'vendors': vendors,
        'popular_products': popular_products,
        'total_products': products.count(),
        'total_vendors': len(vendors),
    }
    
    return render(request, 'dashboards/consumer/market_detail.html', context)


@login_required
def category_detail_view(request, category_slug):
    """View all products in a category with filtering"""
    
    # Verify consumer access
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    category = get_object_or_404(Category, slug=category_slug)
    
    products = VendorProduct.objects.filter(
        product__category=category,
        vendor__is_verified=True
    ).select_related(
        'product', 'vendor__user', 'market'
    ).order_by('price')
    
    # Filter by market
    market_id = request.GET.get('market')
    if market_id:
        products = products.filter(market_id=market_id)
    
    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Get page parameter
    page = request.GET.get('page', 1)
    
    # Pagination
    paginator = Paginator(products, 12)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    # Get available markets for filtering
    markets = Market.objects.filter(
        vendorproduct__in=products,
        is_active=True
    ).distinct()
    
    # Calculate price range for filtering
    price_range = products.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    context = {
        'category': category,
        'products': products_page,
        'page_obj': products_page,
        'markets': markets,
        'price_range': price_range,
        'selected_market': market_id,
        'min_price': min_price,
        'max_price': max_price,
        'total_products': products.count(),
    }
    
    return render(request, 'dashboards/consumer/category_detail.html', context)


# ============================================================================
# PRICE ALERTS VIEWS
# ============================================================================

@login_required
def price_alerts_view(request):
    """View and manage price alerts"""
    
    # Verify consumer access
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    # Get user's price alerts
    alerts = PriceAlert.objects.filter(
        user=request.user
    ).select_related(
        'product__product', 'product__market', 'product__vendor__user'
    ).order_by('-created_at')
    
    # Check for triggered alerts on each view
    for alert in alerts:
        if alert.status == 'active':
            alert.check_price()
    
    context = {
        'alerts': alerts,
        'active_count': alerts.filter(status='active').count(),
        'triggered_count': alerts.filter(status='triggered').count(),
    }
    
    return render(request, 'dashboards/consumer/price_alerts.html', context)


@login_required
def create_price_alert_view(request, product_id):
    """Create a new price alert for a product"""
    
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    product = get_object_or_404(
        VendorProduct, 
        id=product_id, 
        vendor__is_verified=True
    )
    
    if request.method == 'POST':
        target_price = request.POST.get('target_price')
        frequency = request.POST.get('frequency', 'instant')
        notes = request.POST.get('notes', '')
        
        # Validate target price
        try:
            target_price = float(target_price)
            if target_price <= 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, 'Please enter a valid target price.')
            return redirect('product_detail', product_id=product_id)
        
        # Check if alert already exists
        existing_alert = PriceAlert.objects.filter(
            user=request.user,
            product=product,
            target_price=target_price,
            status='active'
        ).first()
        
        if existing_alert:
            messages.info(request, f'You already have an active alert for {product.product.name} at ₦{target_price}')
            return redirect('consumer_price_alerts')
        
        # Create new alert
        alert = PriceAlert.objects.create(
            user=request.user,
            product=product,
            target_price=target_price,
            current_price=product.price,
            frequency=frequency,
            notes=notes
        )
        
        messages.success(
            request, 
            f'Price alert created! We\'ll notify you when {product.product.name} drops to ₦{target_price}'
        )
        
        # Check immediately if current price already meets target
        if product.price <= target_price:
            alert.check_price()
        
        return redirect('consumer_price_alerts')
    
    return redirect('product_detail', product_id=product_id)


@login_required
def edit_price_alert_view(request, alert_id):
    """Edit an existing price alert"""
    
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    
    if request.method == 'POST':
        target_price = request.POST.get('target_price')
        frequency = request.POST.get('frequency')
        notes = request.POST.get('notes', '')
        
        # Validate target price
        try:
            target_price = float(target_price)
            if target_price <= 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, 'Please enter a valid target price.')
            return redirect('consumer_price_alerts')
        
        # Update alert
        alert.target_price = target_price
        alert.frequency = frequency
        alert.notes = notes
        alert.status = 'active'  # Reactivate if it was triggered
        alert.save()
        
        messages.success(request, 'Price alert updated successfully!')
        
        # Check if price already meets new target
        if alert.product.price <= target_price:
            alert.check_price()
        
        return redirect('consumer_price_alerts')
    
    context = {
        'alert': alert,
        'product': alert.product,
    }
    return render(request, 'dashboards/consumer/edit_price_alert.html', context)


@login_required
def delete_price_alert_view(request, alert_id):
    """Delete a price alert"""
    
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    
    if request.method == 'POST':
        product_name = alert.product.product.name
        alert.delete()
        messages.success(request, f'Price alert for {product_name} deleted.')
        return redirect('consumer_price_alerts')
    
    context = {
        'alert': alert,
    }
    return render(request, 'dashboards/consumer/delete_price_alert.html', context)


@login_required
def pause_price_alert_view(request, alert_id):
    """Pause a price alert"""
    
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    alert.status = 'paused'
    alert.save()
    messages.info(request, 'Price alert paused.')
    return redirect('consumer_price_alerts')


@login_required
def resume_price_alert_view(request, alert_id):
    """Resume a paused price alert"""
    
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    alert.status = 'active'
    alert.save()
    
    # Check immediately if price meets target
    alert.check_price()
    
    messages.success(request, 'Price alert resumed.')
    return redirect('consumer_price_alerts')


# ============================================================================
# FAVORITES VIEWS
# ============================================================================

@login_required
def favorites_view(request):
    """View and manage favorite products and vendors"""
    
    # Verify consumer access
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    # Get favorite products
    favorite_products = FavoriteProduct.objects.filter(
        user=request.user
    ).select_related(
        'product__product', 
        'product__market', 
        'product__vendor__user'
    ).order_by('-created_at')
    
    # Get favorite vendors
    favorite_vendors = FavoriteVendor.objects.filter(
        user=request.user
    ).select_related(
        'vendor__user'
    ).prefetch_related(
        'vendor__products__product'
    ).order_by('-created_at')
    
    # Get recent products from favorite vendors
    recent_from_favorites = []
    if favorite_vendors:
        vendor_ids = [fv.vendor.id for fv in favorite_vendors]
        recent_from_favorites = VendorProduct.objects.filter(
            vendor_id__in=vendor_ids,
            vendor__is_verified=True
        ).select_related(
            'product', 'market'
        ).order_by('-last_updated')[:10]
    
    context = {
        'favorite_products': favorite_products,
        'favorite_vendors': favorite_vendors,
        'recent_from_favorites': recent_from_favorites,
        'products_count': favorite_products.count(),
        'vendors_count': favorite_vendors.count(),
    }
    
    return render(request, 'dashboards/consumer/favorites.html', context)


@login_required
def add_favorite_product_view(request, product_id):
    """Add a product to favorites"""
    
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    product = get_object_or_404(
        VendorProduct, 
        id=product_id, 
        vendor__is_verified=True
    )
    
    # Check if already favorited
    favorite, created = FavoriteProduct.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        messages.success(request, f'{product.product.name} added to favorites!')
    else:
        messages.info(request, f'{product.product.name} is already in your favorites.')
    
    # Redirect back
    next_url = request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('product_detail', product_id=product_id)


@login_required
def remove_favorite_product_view(request, favorite_id):
    """Remove a product from favorites"""
    
    favorite = get_object_or_404(FavoriteProduct, id=favorite_id, user=request.user)
    product_name = favorite.product.product.name
    favorite.delete()
    messages.success(request, f'{product_name} removed from favorites.')
    return redirect('consumer_favorites')


@login_required
def add_favorite_vendor_view(request, vendor_id):
    """Add a vendor to favorites"""
    
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    vendor = get_object_or_404(VendorProfile, id=vendor_id, is_verified=True)
    
    # Check if already favorited
    favorite, created = FavoriteVendor.objects.get_or_create(
        user=request.user,
        vendor=vendor
    )
    
    if created:
        messages.success(request, f'{vendor.user.get_full_name() or vendor.user.username} added to favorite vendors!')
    else:
        messages.info(request, 'This vendor is already in your favorites.')
    
    # Redirect back
    next_url = request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('consumer_product_search')


@login_required
def remove_favorite_vendor_view(request, favorite_id):
    """Remove a vendor from favorites"""
    
    favorite = get_object_or_404(FavoriteVendor, id=favorite_id, user=request.user)
    vendor_name = favorite.vendor.user.get_full_name() or favorite.vendor.user.username
    favorite.delete()
    messages.success(request, f'{vendor_name} removed from favorite vendors.')
    return redirect('consumer_favorites')


@login_required
def update_favorite_notes_view(request, favorite_type, favorite_id):
    """Update notes on a favorite item"""
    
    if favorite_type == 'product':
        favorite = get_object_or_404(FavoriteProduct, id=favorite_id, user=request.user)
    elif favorite_type == 'vendor':
        favorite = get_object_or_404(FavoriteVendor, id=favorite_id, user=request.user)
    else:
        messages.error(request, 'Invalid favorite type.')
        return redirect('consumer_favorites')
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        favorite.notes = notes
        favorite.save()
        messages.success(request, 'Notes updated successfully.')
    
    return redirect('consumer_favorites')


@login_required
def toggle_favorite_product(request, product_id):
    """Toggle product favorite status"""
    
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    product = get_object_or_404(
        VendorProduct, 
        id=product_id, 
        vendor__is_verified=True
    )
    
    favorite, created = FavoriteProduct.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if not created:
        favorite.delete()
        messages.success(request, f'{product.product.name} removed from favorites.')
    else:
        messages.success(request, f'{product.product.name} added to favorites!')
    
    # Fix the redirect - use reverse with proper arguments
    from django.urls import reverse
    
    # Get the referring URL, fallback to product detail
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    else:
        return redirect('product_detail', product_id=product_id)
    
    
@login_required
def toggle_favorite_vendor(request, vendor_id):
    """Toggle vendor favorite status"""
    
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    vendor = get_object_or_404(
        VendorProfile, 
        id=vendor_id, 
        is_verified=True
    )
    
    favorite, created = FavoriteVendor.objects.get_or_create(
        user=request.user,
        vendor=vendor
    )
    
    vendor_name = vendor.user.get_full_name() or vendor.user.username
    
    if not created:
        favorite.delete()
        messages.success(request, f'{vendor_name} removed from favorite vendors.')
    else:
        messages.success(request, f'{vendor_name} added to favorite vendors!')
    
    # Fix the redirect
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    else:
        # Fallback to search page or vendor detail if you have one
        return redirect('consumer_product_search')

@login_required
def comparison_detail_view(request, comparison_id):
    """View a specific saved comparison"""
    
    # Check if user is a vendor
    if request.user.groups.filter(name='VENDOR').exists():
        messages.info(request, 'Vendors cannot access the comparison feature.')
        return redirect('vendor_dashboard')
    
    # Get the comparison
    comparison = get_object_or_404(
        Comparison.objects.prefetch_related(
            'products__product', 
            'products__market', 
            'products__vendor__user'
        ),
        id=comparison_id,
        user=request.user
    )
    
    products = comparison.products.filter(vendor__is_verified=True)
    
    # Calculate statistics
    stats = {}
    if products:
        prices = [p.price for p in products]
        stats['min_price'] = min(prices)
        stats['max_price'] = max(prices)
        stats['avg_price'] = sum(prices) / len(prices)
        stats['price_diff'] = stats['max_price'] - stats['min_price']
    
    context = {
        'comparison': comparison,
        'products': products,
        'stats': stats,
        'count': len(products),
        'is_owner': True,
    }
    
    return render(request, 'core/comparison_detail.html', context)

# ============================================================================
# STATIC PAGES (Resources & Legal)
# ============================================================================

def how_to_use_view(request):
    """How to Use MarketLens - Guide for users"""
    context = {
        'title': 'How to Use MarketLens',
        'description': 'Learn how to make the most of MarketLens for transparent market pricing in Alimosho',
    }
    return render(request, 'core/how_to_use.html', context)


def vendor_guidelines_view(request):
    """Vendor Guidelines - Rules and best practices for vendors"""
    context = {
        'title': 'Vendor Guidelines',
        'description': 'Guidelines and best practices for vendors on MarketLens',
    }
    return render(request, 'core/vendor_guidelines.html', context)


def price_update_policy_view(request):
    """Price Update Policy - How prices are managed on the platform"""
    context = {
        'title': 'Price Update Policy',
        'description': 'Learn about how prices are updated and managed on MarketLens',
    }
    return render(request, 'core/price_update_policy.html', context)


def faq_view(request):
    """Frequently Asked Questions"""
    
    faqs = [
        {
            'question': 'What is MarketLens?',
            'answer': 'MarketLens is a platform that helps residents of Alimosho access transparent market prices, compare prices across different markets, and connect with verified vendors.'
        },
        {
            'question': 'Is MarketLens free to use?',
            'answer': 'Yes! MarketLens is completely free for both shoppers and vendors. We believe market transparency should be accessible to everyone.'
        },
        {
            'question': 'How do I become a vendor?',
            'answer': 'To become a vendor, register for an account and select "Vendor" as your role. You\'ll need to complete KYC verification with a valid ID (NIN, BVN, or Government ID) before you can start listing products.'
        },
        {
            'question': 'How long does KYC verification take?',
            'answer': 'KYC verification typically takes 24-48 hours. You\'ll receive a notification once your documents have been reviewed and verified.'
        },
        {
            'question': 'Can I compare prices from different vendors?',
            'answer': 'Yes! Consumers can compare prices from multiple verified vendors side-by-side to find the best deals across different markets in Alimosho.'
        },
        {
            'question': 'Do vendors see each other\'s prices?',
            'answer': 'No. Vendor privacy is a core feature of MarketLens. Vendors can only see their own listings and cannot access competitor pricing information.'
        },
        {
            'question': 'How often are prices updated?',
            'answer': 'Vendors can update their prices in real-time. You\'ll always see the most current prices when you search.'
        },
        {
            'question': 'What markets are covered?',
            'answer': 'We currently cover major markets in Alimosho LGA including Ikotun, Egbeda, Igando, LASU, Iyana Ipaja, Shasha, Baruwa, Meiran, Oke Odo, and Alimosho Central Market.'
        },
        {
            'question': 'Can I use MarketLens on my phone?',
            'answer': 'Yes! MarketLens is fully responsive and works on all devices. You can also install it as a Progressive Web App (PWA) for an app-like experience on your mobile device.'
        },
        {
            'question': 'How do I report incorrect pricing?',
            'answer': 'If you notice incorrect pricing, please contact our support team at support@marketlens.com with details about the product and vendor.'
        },
    ]
    
    context = {
        'title': 'Frequently Asked Questions',
        'description': 'Find answers to common questions about MarketLens',
        'faqs': faqs,
    }
    return render(request, 'core/faq.html', context)


def privacy_policy_view(request):
    """Privacy Policy"""
    context = {
        'title': 'Privacy Policy',
        'description': 'Learn about how we collect, use, and protect your personal information',
        'last_updated': 'March 1, 2025',
    }
    return render(request, 'core/privacy_policy.html', context)


def terms_of_service_view(request):
    """Terms of Service"""
    context = {
        'title': 'Terms of Service',
        'description': 'Terms and conditions for using MarketLens',
        'last_updated': 'March 1, 2025',
    }
    return render(request, 'core/terms_of_service.html', context)


def cookie_policy_view(request):
    """Cookie Policy"""
    context = {
        'title': 'Cookie Policy',
        'description': 'Learn about how we use cookies on MarketLens',
        'last_updated': 'March 1, 2025',
    }
    return render(request, 'core/cookie_policy.html', context)


def contact_us_view(request):
    """Contact Us page with form"""
    if request.method == 'POST':
        # Process contact form
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Here you would typically send an email or save to database
        # For now, just show success message
        messages.success(request, 'Thank you for contacting us! We\'ll get back to you soon.')
        return redirect('contact_us')
    
    context = {
        'title': 'Contact Us',
        'description': 'Get in touch with the MarketLens team',
    }
    return render(request, 'core/contact_us.html', context)


# ============================================================================
# API-LIKE ENDPOINTS FOR AJAX
# ============================================================================

@login_required
def get_price_history_view(request, product_id):
    """Get price history for a product (AJAX endpoint)"""
    
    # Verify consumer access
    if not request.user.groups.filter(name='CONSUMER').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Placeholder for price history
    # This would require a PriceHistory model
    
    data = {
        'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        'prices': [1000, 950, 1100, 1050],
    }
    
    return JsonResponse(data)


# ============================================================================
# COOKIE CONSENT API
# ============================================================================

@csrf_exempt
def cookie_consent_api(request):
    """API endpoint to save cookie consent preferences"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # You can save this to database if you want
            # For now, just return success
            return JsonResponse({'status': 'success'})
        except:
            return JsonResponse({'status': 'error'}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ============================================================================
# ERROR HANDLER VIEWS
# ============================================================================

def handler404(request, exception):
    context = {
        'title': 'Page Not Found',
        'message': 'The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.'
    }
    return render(request, 'errors/404.html', context, status=404)


def handler500(request):
    context = {
        'title': 'Server Error',
        'message': 'An unexpected error has occurred. Our team has been notified and is working on it.'
    }
    return render(request, 'errors/500.html', context, status=500)


def handler403(request, exception):
    context = {
        'title': 'Access Denied',
        'message': 'You do not have permission to access this page.'
    }
    return render(request, 'errors/403.html', context, status=403)


def handler400(request, exception):
    context = {
        'title': 'Bad Request',
        'message': 'The request could not be understood by the server.'
    }
    return render(request, 'errors/400.html', context, status=400)


# Optional: If you want explicit error pages you can visit directly
def error_404_view(request):
    return handler404(request, None)


def error_500_view(request):
    return handler500(request)


def error_403_view(request):
    return handler403(request, None)


def error_400_view(request):
    return handler400(request, None)

