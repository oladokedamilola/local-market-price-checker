from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in with their email address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Allow passing email as 'username' or 'email'
        email = kwargs.get('email') or username
        
        if email is None or password is None:
            return None
        
        try:
            # Try to find user by email (case-insensitive)
            user = User.objects.get(email__iexact=email)
            
            # Check password
            if user.check_password(password):
                return user
                
        except User.DoesNotExist:
            # Run the default password hasher once to reduce timing
            # difference between existing and non-existing users
            User().set_password(password)
            return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None