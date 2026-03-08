# accounts/forms.py
from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from .models import ConsumerProfile, VendorProfile, Profile
from django import forms
from django.contrib.auth.models import User
from django.core.validators import validate_email
import re
from market.models import Market



class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    
    ROLE_CHOICES = (
        ('consumer', 'Shopper (I want to compare prices)'),
        ('vendor', 'Vendor (I want to list my products)'),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number', 'role', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the username field since we'll generate it automatically
        self.fields.pop('username', None)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email
    
    def generate_username(self, email):
        """Generate a unique username from email"""
        # Use the part before @ as base username
        base_username = email.split('@')[0]
        # Remove any special characters
        base_username = re.sub(r'[^a-zA-Z0-9_]', '', base_username)
        # Truncate to max length (150 is Django's max)
        base_username = base_username[:150]
        
        # Check if username exists
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            # Prevent infinite loop (should never happen)
            if counter > 1000:
                username = f"user{counter}"
                break
        
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Generate username from email
        user.username = self.generate_username(self.cleaned_data['email'])
        
        if commit:
            user.save()
            self.save_m2m()
        return user
    

from django import forms
from market.models import Market

class VendorKYCForm(forms.Form):
    # KYC Options
    KYC_TYPE_CHOICES = (
        ('nin', 'National Identity Number (NIN)'),
        ('bvn', 'Bank Verification Number (BVN)'),
        ('id_card', 'Government Issued ID Card'),
    )
    
    kyc_type = forms.ChoiceField(
        choices=KYC_TYPE_CHOICES,
        label='KYC Document Type',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    document_image = forms.FileField(  # Changed from ImageField to FileField
        label='Upload Document',
        help_text='Upload a clear photo or scan of your ID document (JPG, PNG, PDF)',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    business_name = forms.CharField(
        max_length=200,
        label='Business Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Your business/shop name'
        })
    )
    
    market = forms.ModelChoiceField(
        queryset=Market.objects.filter(is_active=True).order_by('name'),
        label='Market Location',
        empty_label="Select your market",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    stall_number = forms.CharField(
        max_length=50,
        label='Stall/Shop Number',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g., Stall 45, Shop B12 (optional)'
        })
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        label='I agree to the terms and conditions',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_document_image(self):
        """Custom validation for uploaded file"""
        file = self.cleaned_data.get('document_image')
        
        if file:
            # Check file size (5MB limit)
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 5MB')
            
            # Check file extension
            ext = file.name.split('.')[-1].lower()
            valid_extensions = ['jpg', 'jpeg', 'png', 'pdf']
            if ext not in valid_extensions:
                raise forms.ValidationError('Only JPG, PNG, and PDF files are allowed')
            
            # Check content type (basic validation)
            content_type = file.content_type
            valid_content_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
            if content_type not in valid_content_types:
                raise forms.ValidationError('Invalid file type. Please upload a valid image or PDF')
        
        return file

class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        
        
class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'id': 'profilePictureInput',
            'accept': 'image/*',
            'style': 'display: none;'  # Hide the actual input
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            # Initialize phone_number from profile
            try:
                self.fields['phone_number'].initial = self.instance.profile.phone_number
            except Profile.DoesNotExist:
                pass
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Update profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            
            # Handle profile picture
            if self.cleaned_data.get('profile_picture'):
                profile.profile_picture = self.cleaned_data['profile_picture']
            
            profile.save()
        return user



class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your email address',
            'autofocus': True
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            validate_email(email)
        except:
            raise forms.ValidationError('Please enter a valid email address.')
        return email


class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter new password',
            'minlength': 8
        })
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirm new password',
            'minlength': 8
        })
    )
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        
        # Password validation
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')
        
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('Password must contain at least one uppercase letter.')
        
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('Password must contain at least one lowercase letter.')
        
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError('Password must contain at least one number.')
        
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data