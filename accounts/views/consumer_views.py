# accounts/views/consumer_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, Min, Max
from django.utils import timezone
from datetime import timedelta

from vendor.models import VendorProduct
from market.models import Category, Market, Product
from core.models import Comparison
import logging

logger = logging.getLogger(__name__)


@login_required
def consumer_dashboard_view(request):
    """Consumer-specific dashboard with product browsing, price comparisons, and saved items"""
    
    # Verify consumer access
    if not request.user.groups.filter(name='CONSUMER').exists():
        messages.error(request, 'Access denied. Consumer privileges required.')
        return redirect('dashboard')
    
    # Get current date for calculations
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    
    # ===== FEATURED PRODUCTS =====
    # Products with recent price updates
    featured_products = VendorProduct.objects.filter(
        vendor__is_verified=True,
        last_updated__date__gte=last_week
    ).select_related(
        'product', 'vendor__user', 'market'
    ).order_by('-last_updated')[:6]
    
    # ===== CATEGORIES WITH PRODUCT COUNTS =====
    categories = Category.objects.annotate(
        product_count=Count('product')
    ).filter(product_count__gt=0).order_by('name')[:8]
    
    # ===== MARKETS WITH VENDOR COUNTS =====
    markets = Market.objects.filter(
        is_active=True
    ).annotate(
        vendor_count=Count('vendorproduct__vendor', distinct=True),
        product_count=Count('vendorproduct')
    ).filter(product_count__gt=0).order_by('name')[:5]
    
    # ===== PRICE ALERTS / RECENT PRICE CHANGES =====
    recent_price_changes = VendorProduct.objects.filter(
        vendor__is_verified=True
    ).select_related(
        'product', 'vendor__user', 'market'
    ).order_by('-last_updated')[:10]
    
    # ===== CONSUMER'S RECENT COMPARISONS =====
    recent_comparisons = Comparison.objects.filter(
        user=request.user
    ).annotate(
        product_count=Count('products')
    ).order_by('-updated_at')[:5]
    
    # ===== LOWEST PRICES FOR POPULAR PRODUCTS =====
    # Get top 5 products with most vendor listings
    popular_products = Product.objects.filter(
        is_active=True,
        vendorproduct__vendor__is_verified=True
    ).annotate(
        vendor_count=Count('vendorproduct__vendor', distinct=True),
        avg_price=Avg('vendorproduct__price'),
        min_price=Min('vendorproduct__price'),
        max_price=Max('vendorproduct__price')
    ).filter(
        vendor_count__gt=0
    ).order_by('-vendor_count')[:5]
    
    # ===== NEARBY MARKETS (based on location - would need user location data) =====
    # For now, just show active markets
    nearby_markets = Market.objects.filter(
        is_active=True
    ).annotate(
        product_count=Count('vendorproduct')
    ).filter(product_count__gt=0)[:3]
    
    # ===== RECENTLY VIEWED PRODUCTS (from session) =====
    recently_viewed_ids = request.session.get('recently_viewed_products', [])
    recently_viewed = []
    if recently_viewed_ids:
        recently_viewed = VendorProduct.objects.filter(
            id__in=recently_viewed_ids[:5],
            vendor__is_verified=True
        ).select_related('product', 'vendor__user', 'market')
    
    # ===== STATISTICS =====
    stats = {
        'total_markets': Market.objects.filter(is_active=True).count(),
        'total_products': Product.objects.filter(is_active=True).count(),
        'total_vendors': VendorProduct.objects.filter(vendor__is_verified=True).values('vendor').distinct().count(),
        'total_listings': VendorProduct.objects.filter(vendor__is_verified=True).count(),
    }
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'markets': markets,
        'recent_price_changes': recent_price_changes,
        'recent_comparisons': recent_comparisons,
        'popular_products': popular_products,
        'nearby_markets': nearby_markets,
        'recently_viewed': recently_viewed,
        'stats': stats,
    }
    
    return render(request, 'dashboards/consumer/consumer_dashboard.html', context)