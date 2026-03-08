from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest

def handler404(request, exception):
    """Custom 404 error handler"""
    context = {
        'exception': str(exception) if exception else 'Page not found',
    }
    return render(request, 'errors/404.html', context, status=404)

def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'errors/500.html', status=500)

def handler403(request, exception):
    """Custom 403 error handler"""
    context = {
        'exception': str(exception) if exception else 'Permission denied',
    }
    return render(request, 'errors/403.html', context, status=403)

def handler400(request, exception):
    """Custom 400 error handler"""
    context = {
        'exception': str(exception) if exception else 'Bad request',
    }
    return render(request, 'errors/400.html', context, status=400)

# Optional: Direct error page views for testing
def error_404_view(request):
    """Direct view for testing 404 page"""
    return render(request, 'errors/404.html', status=404)

def error_500_view(request):
    """Direct view for testing 500 page"""
    return render(request, 'errors/500.html', status=500)

def error_403_view(request):
    """Direct view for testing 403 page"""
    return render(request, 'errors/403.html', status=403)

def error_400_view(request):
    """Direct view for testing 400 page"""
    return render(request, 'errors/400.html', status=400)