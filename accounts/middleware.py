# from django.shortcuts import redirect
# from django.urls import reverse
# import logging

# logger = logging.getLogger(__name__)

# class SocialLoginRedirectMiddleware:
#     """
#     Middleware to redirect new social users to complete their profile
#     """
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         response = self.get_response(request)
#         return response

#     def process_view(self, request, view_func, view_args, view_kwargs):
#         # Skip for admin and static files
#         if request.path.startswith('/admin/') or request.path.startswith('/static/'):
#             return None
            
#         # Check if user is authenticated and has social login flag
#         if request.user.is_authenticated:
#             social_in_progress = request.session.get('social_login_in_progress')
            
#             # If this is a social login in progress and not already on the complete page
#             if social_in_progress and request.path != reverse('social_complete_profile'):
#                 print(f"🔴 Redirecting to complete profile from {request.path}")
#                 # Clear the flag to prevent infinite redirects
#                 del request.session['social_login_in_progress']
#                 return redirect('social_complete_profile')
        
#         return None