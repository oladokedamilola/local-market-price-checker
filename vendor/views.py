# vendor/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Avg, Min, Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from notifications.services import NotificationService
from .models import VendorProduct, VendorKYC
from .forms import VendorProductForm, CategoryRequestForm
from .decorators import vendor_required
from market.models import Product, Market, Category
from accounts.models import CategoryRequest
import logging

logger = logging.getLogger(__name__)


@vendor_required
def vendor_dashboard(request):
    """Vendor dashboard showing all products and statistics"""
    vendor = request.user.vendorprofile
    
    # Get all vendor products
    products = VendorProduct.objects.filter(
        vendor=vendor
    ).select_related('product', 'market', 'product__category').order_by('-last_updated')
    
    # Calculate statistics
    total_products = products.count()
    
    # Products by category
    products_by_category = {}
    for product in products:
        category_name = product.product.category.name if product.product.category else 'Uncategorized'
        if category_name not in products_by_category:
            products_by_category[category_name] = 0
        products_by_category[category_name] += 1
    
    # Products by market
    products_by_market = {}
    for product in products:
        market_name = product.market.name
        if market_name not in products_by_market:
            products_by_market[market_name] = 0
        products_by_market[market_name] += 1
    
    # Price statistics
    price_stats = products.aggregate(
        avg_price=Avg('price'),
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    # Recent products (last 5)
    recent_products = products[:5]
    
    # Price update stats (last 7 days)
    last_week = timezone.now() - timedelta(days=7)
    recent_updates = products.filter(last_updated__gte=last_week).count()
    
    # Products that haven't been updated in 30+ days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    stale_products = products.filter(last_updated__lte=thirty_days_ago).count()
    
    # Get KYC status
    try:
        kyc = VendorKYC.objects.get(vendor=vendor)
        kyc_status = 'approved' if kyc.is_approved else 'pending' if kyc.submitted_at else 'not_submitted'
    except VendorKYC.DoesNotExist:
        kyc_status = 'not_submitted'
    
    context = {
        'products': products,
        'total_products': total_products,
        'products_by_category': products_by_category,
        'products_by_market': products_by_market,
        'price_stats': price_stats,
        'recent_products': recent_products,
        'recent_updates': recent_updates,
        'stale_products': stale_products,
        'kyc_status': kyc_status,
        'markets_count': len(products_by_market),
        'categories_count': len(products_by_category),
    }
    
    return render(request, 'vendor/dashboard.html', context)

@vendor_required
def vendor_analytics_view(request):
    """Comprehensive analytics dashboard for vendor"""
    vendor = request.user.vendorprofile
    from django.db.models import Count, Avg, Min, Max, Q
    from datetime import datetime, timedelta
    import json
    
    # Get date range from request or default to last 30 days
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Basic Statistics
    products = VendorProduct.objects.filter(vendor=vendor)
    total_products = products.count()
    
    # Products by category
    category_data = products.values(
        'product__category__name'
    ).annotate(
        count=Count('id'),
        avg_price=Avg('price')
    ).order_by('-count')
    
    categories_labels = [item['product__category__name'] or 'Uncategorized' for item in category_data]
    categories_counts = [item['count'] for item in category_data]
    
    # Products by market
    market_data = products.values(
        'market__name'
    ).annotate(
        count=Count('id'),
        avg_price=Avg('price')
    ).order_by('-count')
    
    markets_labels = [item['market__name'] for item in market_data]
    markets_counts = [item['count'] for item in market_data]
    
    # Price distribution
    price_ranges = [
        {'min': 0, 'max': 500, 'label': '₦0 - ₦500'},
        {'min': 501, 'max': 1000, 'label': '₦501 - ₦1,000'},
        {'min': 1001, 'max': 2000, 'label': '₦1,001 - ₦2,000'},
        {'min': 2001, 'max': 5000, 'label': '₦2,001 - ₦5,000'},
        {'min': 5001, 'max': 10000, 'label': '₦5,001 - ₦10,000'},
        {'min': 10001, 'max': 999999, 'label': '₦10,001+'},
    ]
    
    price_distribution = []
    for range_item in price_ranges:
        count = products.filter(
            price__gte=range_item['min'],
            price__lte=range_item['max']
        ).count()
        price_distribution.append({
            'label': range_item['label'],
            'count': count
        })
    
    # Update frequency analysis
    update_data = []
    current_date = start_date
    while current_date <= end_date:
        next_date = current_date + timedelta(days=1)
        count = products.filter(
            last_updated__gte=current_date,
            last_updated__lt=next_date
        ).count()
        update_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': count
        })
        current_date = next_date
    
    # Price statistics
    price_stats = products.aggregate(
        overall_avg=Avg('price'),
        overall_min=Min('price'),
        overall_max=Max('price')
    )
    
    # Top products (by price)
    top_products = products.select_related(
        'product', 'market'
    ).order_by('-price')[:5]
    
    # Recently updated products
    recent_updates = products.filter(
        last_updated__gte=start_date
    ).select_related(
        'product', 'market'
    ).order_by('-last_updated')[:10]
    
    # Market comparison (compare with other vendors)
    from django.db.models import FloatField
    from django.db.models.functions import Cast
    
    market_comparison = []
    for product in products[:10]:  # Limit to 10 products for performance
        competitors = VendorProduct.objects.filter(
            product=product.product,
            market=product.market
        ).exclude(
            vendor=vendor
        ).aggregate(
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            competitor_count=Count('id')
        )
        
        if competitors['competitor_count'] > 0:
            price_position = 'below' if product.price < competitors['avg_price'] else 'above' if product.price > competitors['avg_price'] else 'equal'
            market_comparison.append({
                'product': product.product.name,
                'market': product.market.name,
                'your_price': float(product.price),
                'avg_price': float(competitors['avg_price'] or 0),
                'min_price': float(competitors['min_price'] or 0),
                'max_price': float(competitors['max_price'] or 0),
                'competitors': competitors['competitor_count'],
                'price_position': price_position,
                'savings_potential': float(product.price - (competitors['avg_price'] or product.price))
            })
    
    # Sort by savings potential (products where you could adjust price)
    market_comparison.sort(key=lambda x: abs(x['savings_potential']), reverse=True)
    
    # Update recommendations
    thirty_days_ago = end_date - timedelta(days=30)
    stale_products_count = products.filter(last_updated__lte=thirty_days_ago).count()
    
    # Products with no competitors (potential to be the only vendor)
    products_with_competitors = 0
    for product in products:
        competitor_count = VendorProduct.objects.filter(
            product=product.product,
            market=product.market
        ).exclude(vendor=vendor).count()
        if competitor_count > 0:
            products_with_competitors += 1
    
    unique_products_count = total_products - products_with_competitors
    
    context = {
        # Chart data
        'categories_labels': json.dumps(categories_labels),
        'categories_counts': json.dumps(categories_counts),
        'markets_labels': json.dumps(markets_labels),
        'markets_counts': json.dumps(markets_counts),
        'price_distribution': price_distribution,
        'update_data': json.dumps(update_data),
        
        # Statistics
        'total_products': total_products,
        'total_categories': len(categories_labels),
        'total_markets': len(markets_labels),
        'price_stats': price_stats,
        'avg_price_per_category': category_data,
        'avg_price_per_market': market_data,
        
        # Lists
        'top_products': top_products,
        'recent_updates': recent_updates,
        'market_comparison': market_comparison[:10],  # Top 10 comparison insights
        
        # Insights
        'stale_products_count': stale_products_count,
        'unique_products_count': unique_products_count,
        'products_with_competitors': products_with_competitors,
        
        # Date range
        'days': days,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    
    return render(request, 'dashboards/vendor/analytics.html', context)

@vendor_required
def product_list_view(request):
    """View all vendor products with filtering and pagination"""
    vendor = request.user.vendorprofile
    
    # Get filter parameters
    search = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    market_id = request.GET.get('market', '')
    sort_by = request.GET.get('sort', '-last_updated')
    
    # Base queryset
    products = VendorProduct.objects.filter(
        vendor=vendor
    ).select_related(
        'product', 'market', 'product__category'
    )
    
    # Apply filters
    if search:
        products = products.filter(
            Q(product__name__icontains=search) |
            Q(product__description__icontains=search) |
            Q(market__name__icontains=search)
        )
    
    if category_id:
        products = products.filter(product__category_id=category_id)
    
    if market_id:
        products = products.filter(market_id=market_id)
    
    # Apply sorting
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'name_asc':
        products = products.order_by('product__name')
    elif sort_by == 'name_desc':
        products = products.order_by('-product__name')
    elif sort_by == 'oldest':
        products = products.order_by('created_at')
    else:  # default: newest first
        products = products.order_by('-last_updated')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 10)  # Show 10 products per page
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    # Get filter options
    categories = Category.objects.filter(
        product__vendorproduct__vendor=vendor
    ).distinct().annotate(
        product_count=Count('product__vendorproduct')
    )
    
    markets = Market.objects.filter(
        vendorproduct__vendor=vendor
    ).distinct().annotate(
        product_count=Count('vendorproduct')
    )
    
    context = {
        'products': products_page,
        'categories': categories,
        'markets': markets,
        'search': search,
        'selected_category': category_id,
        'selected_market': market_id,
        'sort_by': sort_by,
        'total_results': products.count(),
        'paginator': paginator,
    }
    
    return render(request, 'dashboards/vendor/product_list.html', context)


@vendor_required
def product_detail_view(request, pk):
    """View detailed information about a specific product"""
    
    # Check if user is a consumer (should not access this page)
    if request.user.groups.filter(name='CONSUMER').exists():
        # Redirect consumers to the core product detail page
        from django.shortcuts import redirect
        messages.info(request, 'Redirecting to consumer product view.')
        return redirect('product_detail', product_id=pk)
    
    vendor = request.user.vendorprofile
    product = get_object_or_404(
        VendorProduct.objects.select_related(
            'product', 'market', 'product__category', 'vendor__user'
        ),
        pk=pk,
        vendor=vendor
    )
    
    # Get price history (would need a PriceHistory model for real data)
    # For now, we'll create sample data based on last_updated
    price_history = {
        'labels': ['6 months', '5 months', '4 months', '3 months', '2 months', '1 month', 'Now'],
        'prices': [
            float(product.price) * 0.85,
            float(product.price) * 0.88,
            float(product.price) * 0.92,
            float(product.price) * 0.95,
            float(product.price) * 0.98,
            float(product.price) * 0.99,
            float(product.price)
        ]
    }
    
    # Find same product from other vendors for comparison
    competitors = VendorProduct.objects.filter(
        product=product.product,
        market=product.market
    ).exclude(
        id=product.id
    ).select_related(
        'vendor__user'
    ).order_by('price')[:5]
    
    # Calculate price position
    all_prices = list(VendorProduct.objects.filter(
        product=product.product,
        market=product.market
    ).values_list('price', flat=True))
    
    if all_prices:
        sorted_prices = sorted(all_prices)
        try:
            position = sorted_prices.index(float(product.price)) + 1
            total_sellers = len(sorted_prices)
            percentile = (position / total_sellers) * 100
        except ValueError:
            position = None
            percentile = None
    else:
        position = None
        percentile = None
    
    # Get similar products (same category, different markets)
    similar_products = VendorProduct.objects.filter(
        product__category=product.product.category,
        vendor=vendor
    ).exclude(
        id=product.id
    ).select_related('product', 'market')[:3]
    
    context = {
        'product': product,
        'price_history': price_history,
        'competitors': competitors,
        'similar_products': similar_products,
        'price_position': position,
        'price_percentile': percentile,
        'total_competitors': len(all_prices),
    }
    
    return render(request, 'dashboards/vendor/product_detail.html', context)

@vendor_required
def add_product(request):
    """Add a new product listing"""
    vendor = request.user.vendorprofile
    
    # Check if vendor has approved KYC
    try:
        kyc = VendorKYC.objects.get(vendor=vendor, is_approved=True)
    except VendorKYC.DoesNotExist:
        messages.error(request, 'You must complete KYC verification before adding products.')
        return redirect('vendor_kyc')
    
    if request.method == 'POST':
        form = VendorProductForm(request.POST, request.FILES, vendor=vendor)
        if form.is_valid():
            # Get or create the base product
            product_name = form.cleaned_data['product_name']
            category = form.cleaned_data['category']
            unit = form.cleaned_data['unit']
            description = form.cleaned_data['description']
            image = form.cleaned_data.get('image')
            
            # Check if product already exists
            existing_product = form.cleaned_data.get('existing_product')
            
            if existing_product:
                # Use existing product
                product = existing_product
                # Update category if changed
                if product.category != category:
                    product.category = category
                
                # Update image if new one provided
                if image:
                    product.image = image
                
                product.description = description
                product.save()
            else:
                # Create new product
                product = Product.objects.create(
                    name=product_name,
                    category=category,
                    unit=unit,
                    description=description,
                    image=image
                )
            
            # Determine market from KYC
            market_location = kyc.market_location
            market_name = market_location.split(',')[0].strip() if ',' in market_location else market_location
            
            try:
                market = Market.objects.get(name__icontains=market_name, is_active=True)
            except Market.DoesNotExist:
                market = Market.objects.filter(is_active=True).first()
                logger.warning(f"Market '{market_name}' not found for vendor {vendor.user.username}")
            
            # Create vendor product
            vendor_product = VendorProduct.objects.create(
                vendor=vendor,
                product=product,
                market=market,
                price=form.cleaned_data['price']
            )
            
            # Send notification to admins
            try:
                NotificationService.notify_admin_new_product(vendor_product)
                logger.info(f"Admin notified about new product: {vendor_product.product.name}")
            except Exception as e:
                logger.error(f"Failed to notify admins about new product: {str(e)}")
            
            messages.success(request, 'Product added successfully!')
            return redirect('product_list')
    else:
        form = VendorProductForm(vendor=vendor)
    
    context = {
        'form': form,
        'vendor_market': form.vendor_market_full if hasattr(form, 'vendor_market_full') else None,
        'is_update': False,
    }
    return render(request, 'dashboards/vendor/product_form.html', context)
@vendor_required
def update_product(request, pk):
    """Update an existing product listing"""
    vendor = request.user.vendorprofile
    vendor_product = get_object_or_404(VendorProduct, pk=pk, vendor=vendor)
    
    # Check if vendor has approved KYC
    try:
        kyc = VendorKYC.objects.get(vendor=vendor, is_approved=True)
    except VendorKYC.DoesNotExist:
        messages.error(request, 'You must complete KYC verification before managing products.')
        return redirect('vendor_kyc')
    
    if request.method == 'POST':
        # Pass is_update=True for updates
        form = VendorProductForm(request.POST, request.FILES, vendor=vendor, is_update=True, product_id=pk)
        
        if form.is_valid():
            # Get cleaned data
            product_name = form.cleaned_data['product_name']
            category = form.cleaned_data['category']
            unit = form.cleaned_data['unit']
            description = form.cleaned_data['description']
            image = form.cleaned_data.get('image')
            price = form.cleaned_data['price']
            
            # Check if we should use existing product or create new
            existing_product = form.cleaned_data.get('existing_product')
            
            if existing_product and existing_product != vendor_product.product:
                # Switch to existing product
                product = existing_product
                if image:
                    product.image = image
                product.save()
            else:
                # Update current product
                product = vendor_product.product
                product.name = product_name
                product.category = category
                product.unit = unit
                product.description = description
                if image:
                    product.image = image
                product.save()
            
            # Update vendor product
            vendor_product.product = product
            vendor_product.price = price
            vendor_product.save()
            
            messages.success(request, 'Product updated successfully!')
            return redirect('product_detail', pk=vendor_product.pk)
    else:
        # Pre-populate form with existing data
        initial_data = {
            'product_name': vendor_product.product.name,
            'category': vendor_product.product.category,
            'unit': vendor_product.product.unit,
            'description': vendor_product.product.description,
            'price': vendor_product.price,
            'is_update': True,
        }
        form = VendorProductForm(
            initial=initial_data, 
            vendor=vendor, 
            is_update=True,
            product_id=pk
        )
    
    context = {
        'form': form,
        'product': vendor_product,
        'vendor_market': kyc.market_location,
        'is_update': True,
    }
    return render(request, 'dashboards/vendor/product_form.html', context)

@vendor_required
def delete_product(request, pk):
    """Delete a product listing"""
    vendor = request.user.vendorprofile
    product = get_object_or_404(VendorProduct, pk=pk, vendor=vendor)
    
    if request.method == 'POST':
        product_name = str(product)
        
        # Optional: Check if this is the only vendor using this product
        other_vendors = VendorProduct.objects.filter(
            product=product.product
        ).exclude(vendor=vendor).count()
        
        product.delete()
        
        # If no other vendors are using this product, you might want to delete the base product too
        # if other_vendors == 0:
        #     product.product.delete()
        
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('product_list')
    
    context = {
        'product': product,
    }
    return render(request, 'dashboards/vendor/delete_product.html', context)


@vendor_required
def request_category(request):
    """Allow vendors to request new categories"""
    vendor = request.user.vendorprofile
    
    # Check if vendor has approved KYC
    try:
        kyc = VendorKYC.objects.get(vendor=vendor, is_approved=True)
    except VendorKYC.DoesNotExist:
        messages.warning(request, 'You need to complete KYC verification before requesting categories.')
        return redirect('vendor_kyc')
    
    if request.method == 'POST':
        form = CategoryRequestForm(request.POST)
        if form.is_valid():
            # Check if category already exists
            category_name = form.cleaned_data['name']
            if Category.objects.filter(name__iexact=category_name).exists():
                messages.error(request, f'A category named "{category_name}" already exists.')
                return redirect('request_category')
            
            # Create category request record
            category_request = form.save(commit=False)
            category_request.vendor = vendor
            
            # Capture request metadata
            category_request.ip_address = request.META.get('REMOTE_ADDR')
            category_request.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
            
            category_request.save()
            
            messages.success(
                request, 
                f'Your request for category "{category_request.name}" has been submitted. '
                f'Admin will review it soon and notify you of the decision.'
            )
            return redirect('add_product')
    else:
        form = CategoryRequestForm()
    
    # Get user's previous category requests
    previous_requests = CategoryRequest.objects.filter(
        vendor=vendor
    ).order_by('-created_at')[:5]
    
    context = {
        'form': form,
        'previous_requests': previous_requests,
    }
    return render(request, 'dashboards/vendor/request_category.html', context)


@vendor_required
def bulk_price_update_view(request):
    """Bulk update prices for multiple products"""
    vendor = request.user.vendorprofile
    
    # Check if vendor has approved KYC
    try:
        kyc = VendorKYC.objects.get(vendor=vendor, is_approved=True)
    except VendorKYC.DoesNotExist:
        messages.error(request, 'You must complete KYC verification before managing products.')
        return redirect('vendor_kyc')
    
    if request.method == 'POST':
        # Get selected products and new price
        product_ids = request.POST.getlist('selected_products')
        price_type = request.POST.get('price_type')  # 'fixed', 'percentage_increase', 'percentage_decrease'
        price_value = request.POST.get('price_value')
        
        if not product_ids:
            messages.error(request, 'Please select at least one product.')
            return redirect('bulk_price_update')
        
        try:
            price_value = float(price_value)
            if price_value < 0:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, 'Please enter a valid positive price value.')
            return redirect('bulk_price_update')
        
        products = VendorProduct.objects.filter(id__in=product_ids, vendor=vendor)
        
        if not products.exists():
            messages.error(request, 'No valid products selected.')
            return redirect('bulk_price_update')
        
        updated_count = 0
        updated_products = []
        significant_changes = []
        
        for product in products:
            old_price = float(product.price)
            new_price = old_price
            
            if price_type == 'fixed':
                new_price = price_value
            elif price_type == 'percentage_increase':
                new_price = old_price * (1 + price_value / 100)
            elif price_type == 'percentage_decrease':
                new_price = old_price * (1 - price_value / 100)
            
            # Round to 2 decimal places
            new_price = round(new_price, 2)
            
            # Only update if price actually changed
            if abs(new_price - old_price) > 0.01:
                product.price = new_price
                product.save()
                updated_count += 1
                updated_products.append(product)
                
                # Check for significant changes (>20%)
                change_percent = abs((new_price - old_price) / old_price * 100)
                if change_percent > 20:
                    significant_changes.append({
                        'product': product.product.name,
                        'old_price': old_price,
                        'new_price': new_price,
                        'change_percent': round(change_percent, 1)
                    })
        
        # Send notifications for updates
        if updated_products:
            try:
                for product in updated_products:
                    NotificationService.notify_admin_product_update(product)
                logger.info(f"Admins notified about bulk price update for {updated_count} products")
            except Exception as e:
                logger.error(f"Failed to notify admins about bulk price update: {str(e)}")
        
        # Show appropriate message
        if updated_count > 0:
            message = f'Successfully updated {updated_count} product(s).'
            if significant_changes:
                message += f' Warning: {len(significant_changes)} product(s) had price changes over 20%.'
            messages.success(request, message)
            
            # Log significant changes for auditing
            if significant_changes:
                logger.info(f"Significant price changes by vendor {vendor.user.username}: {significant_changes}")
        else:
            messages.info(request, 'No products were updated. Prices may already be at the specified values.')
        
        return redirect('product_list')
    
    # GET request - show form with products
    products = VendorProduct.objects.filter(
        vendor=vendor
    ).select_related('product', 'market').order_by('product__name')
    
    # Calculate some stats for the template
    total_products = products.count()
    avg_price = products.aggregate(Avg('price'))['price__avg'] or 0
    
    context = {
        'products': products,
        'total_products': total_products,
        'avg_price': round(avg_price, 2),
        'min_price': products.aggregate(Min('price'))['price__min'] or 0,
        'max_price': products.aggregate(Max('price'))['price__max'] or 0,
    }
    return render(request, 'dashboards/vendor/bulk_price_update.html', context)

@vendor_required
def export_products_view(request):
    """Export products to CSV"""
    import csv
    from django.http import HttpResponse
    from django.utils import timezone
    
    vendor = request.user.vendorprofile
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vendor_products_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Product Name', 'Category', 'Market', 'Price (₦)', 'Last Updated'])
    
    products = VendorProduct.objects.filter(
        vendor=vendor
    ).select_related('product', 'product__category', 'market').order_by('product__name')
    
    for product in products:
        writer.writerow([
            product.product.name,
            product.product.category.name if product.product.category else 'Uncategorized',
            product.market.name,
            str(product.price),
            product.last_updated.strftime('%Y-%m-%d %H:%M'),
        ])
    
    messages.success(request, 'Products exported successfully!')
    return response


@vendor_required
def duplicate_product_view(request, pk):
    """Duplicate an existing product listing"""
    vendor = request.user.vendorprofile
    original_product = get_object_or_404(VendorProduct, pk=pk, vendor=vendor)
    
    if request.method == 'POST':
        # Create duplicate with same details
        new_product = VendorProduct.objects.create(
            vendor=vendor,
            product=original_product.product,
            market=original_product.market,
            price=original_product.price
        )
        messages.success(request, 'Product duplicated successfully! You can now edit it.')
        return redirect('update_product', pk=new_product.pk)
    
    context = {
        'original_product': original_product,
    }
    return render(request, 'dashboards/vendor/duplicate_product.html', context)


@vendor_required
def low_stock_alert_view(request):
    """View for products that might need price updates (not updated recently)"""
    vendor = request.user.vendorprofile
    
    # Products not updated in 30+ days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    stale_products = VendorProduct.objects.filter(
        vendor=vendor,
        last_updated__lte=thirty_days_ago
    ).select_related('product', 'market', 'product__category').order_by('last_updated')
    
    # Calculate days since update for each product
    for product in stale_products:
        delta = timezone.now() - product.last_updated
        product.days_since_update = delta.days
    
    context = {
        'stale_products': stale_products,
        'days_threshold': 30,
        'total_stale': stale_products.count(),
    }
    return render(request, 'dashboards/vendor/low_stock_alert.html', context)