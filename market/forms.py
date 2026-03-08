from django import forms
from .models import Product, Market, Category

class PriceSearchForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        required=False,
        empty_label="All Products"
    )
    market = forms.ModelChoiceField(
        queryset=Market.objects.filter(is_active=True),
        required=False,
        empty_label="All Markets"
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'icon']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('A category with this name already exists.')
        return name


class MarketForm(forms.ModelForm):
    class Meta:
        model = Market
        fields = ['name', 'location', 'address', 'description', 'cover_image', 
                 'opening_hours', 'contact_number', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if Market.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('A market with this name already exists.')
        return name


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'unit', 'is_active']  # Removed 'image'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        unit = cleaned_data.get('unit')
        
        if name and unit:
            # Check for existing product with same name and unit
            if Product.objects.filter(name__iexact=name, unit__iexact=unit).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(f'A product with name "{name}" and unit "{unit}" already exists.')
        return cleaned_data