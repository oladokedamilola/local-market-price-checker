# market/urls.py
from django.urls import path
from .views import price_search

urlpatterns = [
    path('search/', price_search, name='price_search'),
]
