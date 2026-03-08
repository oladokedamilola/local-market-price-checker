from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
import logging
import uuid

logger = logging.getLogger(__name__)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle social account signup with unique username generation
    """
    
    def generate_unique_username(self, base_username):
        """Generate a unique username by appending numbers if needed"""
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return username
    
    def save_user(self, request, sociallogin, form=None):
        """
        Override save_user to handle username generation properly
        """
        # Get the user data from the social login
        user_data = sociallogin.account.extra_data
        email = user_data.get('email', '')
        
        # Generate a username from email or use a fallback
        if email:
            # Use email prefix as base username
            base_username = email.split('@')[0][:20]  # Max 20 chars
            # Remove any special characters
            base_username = ''.join(e for e in base_username if e.isalnum())
        else:
            # Fallback to random username
            base_username = f"user{uuid.uuid4().hex[:8]}"
        
        # Ensure username is unique
        username = self.generate_unique_username(base_username)
        
        # Prepare user data for creation
        user_kwargs = {
            'username': username,
            'email': email,
            'first_name': user_data.get('given_name', ''),
            'last_name': user_data.get('family_name', ''),
        }
        
        # Create the user
        user = User(**user_kwargs)
        user.set_unusable_password()
        user.save()
        
        # Connect the social account to the user
        sociallogin.user = user
        sociallogin.save(request)
        
        # Activate the user (Google already verified email)
        user.is_active = True
        user.save()
        
        print(f"✅ User created and activated: {user.email} (username: {user.username})")
        logger.info(f"Google user created: {user.email} (username: {user.username})")
        
        return user
    
    def pre_social_login(self, request, sociallogin):
        """
        Check if the user already exists with this email
        If yes, connect the social account to the existing user
        """
        email = sociallogin.account.extra_data.get('email')
        if email:
            try:
                # Try to find existing user by email
                existing_user = User.objects.get(email=email)
                # Connect this social account to the existing user
                sociallogin.connect(request, existing_user)
                print(f"✅ Connected Google account to existing user: {email}")
                logger.info(f"Connected Google account to existing user: {email}")
            except User.DoesNotExist:
                # New user - will be created in save_user
                pass
        
        return None