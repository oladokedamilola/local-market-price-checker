from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from vendor.models import VendorProduct
from .forms import PriceSearchForm

@login_required
def price_search(request):
    form = PriceSearchForm(request.GET or None)
    results = VendorProduct.objects.none()

    user = request.user
    is_vendor = user.groups.filter(name='VENDOR').exists()

    if form.is_valid():
        results = VendorProduct.objects.select_related(
            'vendor', 'product', 'market'
        )

        # Role-based filtering
        if is_vendor:
            results = results.filter(vendor=user.vendorprofile)

        # Apply search filters
        product = form.cleaned_data.get('product')
        market = form.cleaned_data.get('market')

        if product:
            results = results.filter(product=product)

        if market:
            results = results.filter(market=market)

    context = {
        'form': form,
        'results': results,
        'is_vendor': is_vendor
    }
    return render(request, 'market/price_search.html', context)
