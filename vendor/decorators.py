from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def vendor_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name='VENDOR').exists():
            return redirect('login')

        vendor = request.user.vendorprofile
        if not vendor.is_verified:
            return redirect('vendor_pending')

        return view_func(request, *args, **kwargs)
    return wrapper
