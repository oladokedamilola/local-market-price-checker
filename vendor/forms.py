# vendor/forms.py
from django import forms
from market.models import Product, Market, Category
from accounts.models import CategoryRequest
from vendor.models import VendorKYC
import logging

logger = logging.getLogger(__name__)

class VendorProductForm(forms.Form): 
    """Form for vendors to add/edit their products"""
    
    # Product name - free text input
    product_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Fresh Tomatoes, Basmati Rice, etc.'
        }),
        label="Product Name"
    )
    
    # Category selection
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        empty_label="Select a category",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Category",
        required=True
    )
    
    # Unit/measurement
    unit = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., kg, basket, piece, cup'
        }),
        label="Unit",
        help_text="How is this product sold? (e.g., per kg, per basket)"
    )
    
    # Description (optional)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe your product (optional)'
        }),
        label="Description"
    )
    
    # Price
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter price in Naira'
        }),
        label="Price (₦)"
    )
    
    # Image - single image upload
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'id': 'product-image'
        }),
        label="Product Image",
        help_text="Upload a product image (JPG, PNG). Max size: 5MB"
    )
    
    # Add a field to track if this is an update (we'll pass this from the view)
    is_update = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        self.vendor = kwargs.pop('vendor', None)
        self.is_update_mode = kwargs.pop('is_update', False)  # Get update mode from kwargs
        self.existing_product_id = kwargs.pop('product_id', None)  # For updates
        super().__init__(*args, **kwargs)
        
        # If this is an update and we have a product ID, we'll populate fields later in the view
        # This is handled by passing initial data when creating the form
        
        # Get vendor's market from KYC
        if self.vendor:
            try:
                kyc = VendorKYC.objects.get(vendor=self.vendor, is_approved=True)
                market_location = kyc.market_location
                if ',' in market_location:
                    market_name = market_location.split(',')[0].strip()
                else:
                    market_name = market_location
                
                self.vendor_market = market_name
                self.vendor_market_full = market_location
            except VendorKYC.DoesNotExist:
                self.vendor_market = None
                self.vendor_market_full = None
        else:
            self.vendor_market = None
            self.vendor_market_full = None
    
    def clean_image(self):
        """Validate image"""
        image = self.cleaned_data.get('image')
        is_update = self.cleaned_data.get('is_update', False) or self.is_update_mode
        
        # For new products (not update mode), image is required
        if not is_update and not image:
            raise forms.ValidationError("Please upload a product image.")
        
        if image:
            # Validate file size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image size must be less than 5MB.")
            
            # Validate content type
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError("File must be an image (JPG, PNG, etc.).")
        
        return image
    
    def clean(self):
        cleaned_data = super().clean()
        product_name = cleaned_data.get('product_name')
        unit = cleaned_data.get('unit')
        
        # Check if product with same name and unit already exists
        if product_name and unit:
            existing_product = Product.objects.filter(
                name__iexact=product_name,
                unit__iexact=unit
            ).first()
            
            if existing_product:
                cleaned_data['existing_product'] = existing_product
            else:
                cleaned_data['existing_product'] = None
        
        return cleaned_data
    
    
class CategoryRequestForm(forms.ModelForm):
    """Form for vendors to request new categories"""
    
    class Meta:
        model = CategoryRequest
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Fresh Vegetables, Dairy Products, Spices'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Why do you need this category? What products would it include?'
            }),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description (Optional)',
        }
        help_texts = {
            'name': 'Enter a clear, descriptive name for the category',
            'description': 'Provide details about what products this category would contain',
        }
    
    def clean_name(self):
        """Validate that the category name doesn't already exist"""
        from market.models import Category
        name = self.cleaned_data.get('name')
        
        # Check if category already exists
        if Category.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(f'A category named "{name}" already exists.')
        
        # Check if there's already a pending request with this name
        if CategoryRequest.objects.filter(
            name__iexact=name, 
            status__in=['pending', 'in_review']
        ).exists():
            raise forms.ValidationError(f'A request for category "{name}" is already pending review.')
        
        return name