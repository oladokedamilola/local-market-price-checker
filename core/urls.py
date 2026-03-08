# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Search & Product Details
    path('search/', views.search_view, name='search'),
    path('product/<int:product_id>/', views.product_detail_view, name='consumer_product_detail'),
    
    # Market & Category Browsing
    path('market/<int:market_id>/', views.market_detail_view, name='consumer_market_detail'),
    path('category/<slug:category_slug>/', views.category_detail_view, name='consumer_category_detail'),
    
    # Comparison URLs
    path('compare/', views.compare_view, name='compare'),
    path('compare/add/<int:product_id>/', views.add_to_comparison, name='add_to_comparison'),
    path('compare/remove/<int:product_id>/', views.remove_from_comparison, name='remove_from_comparison'),
    path('compare/clear/', views.clear_comparison, name='clear_comparison'),
    path('compare/save/', views.save_comparison, name='save_comparison'),
    path('compare/share/<uuid:share_uuid>/', views.shared_comparison_view, name='shared_comparison'),
    path('compare/my-comparisons/', views.my_comparisons_view, name='my_comparisons'),
    path('compare/<int:comparison_id>/', views.comparison_detail_view, name='comparison_detail'),  # Add this line

    # Price Alerts URLs
    path('price-alerts/', views.price_alerts_view, name='consumer_price_alerts'),
    path('price-alerts/create/<int:product_id>/', views.create_price_alert_view, name='consumer_create_price_alert'),
    path('price-alerts/edit/<int:alert_id>/', views.edit_price_alert_view, name='consumer_edit_price_alert'),
    path('price-alerts/delete/<int:alert_id>/', views.delete_price_alert_view, name='consumer_delete_price_alert'),
    path('price-alerts/pause/<int:alert_id>/', views.pause_price_alert_view, name='consumer_pause_price_alert'),
    path('price-alerts/resume/<int:alert_id>/', views.resume_price_alert_view, name='consumer_resume_price_alert'),
    
    # Favorites URLs
    path('favorites/', views.favorites_view, name='consumer_favorites'),
    path('favorites/product/add/<int:product_id>/', views.add_favorite_product_view, name='consumer_add_favorite_product'),
    path('favorites/product/remove/<int:favorite_id>/', views.remove_favorite_product_view, name='consumer_remove_favorite_product'),
    path('favorites/vendor/add/<int:vendor_id>/', views.add_favorite_vendor_view, name='consumer_add_favorite_vendor'),
    path('favorites/vendor/remove/<int:favorite_id>/', views.remove_favorite_vendor_view, name='consumer_remove_favorite_vendor'),
    path('favorites/notes/<str:favorite_type>/<int:favorite_id>/', views.update_favorite_notes_view, name='consumer_update_favorite_notes'),
    # Favorites toggle URLs
    path('favorites/product/toggle/<int:product_id>/', views.toggle_favorite_product, name='toggle_favorite_product'),
    path('favorites/vendor/toggle/<int:vendor_id>/', views.toggle_favorite_vendor, name='toggle_favorite_vendor'),
    # AJAX endpoints
    path('api/price-history/<int:product_id>/', views.get_price_history_view, name='consumer_price_history'),
]