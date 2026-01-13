# custom_admin/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    # Dashboard
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Price Data Management
    path('onion-prices/', views.manage_onion_prices, name='manage_onion_prices'),
    path('onion-prices/add/', views.add_onion_price, name='add_onion_price'),
    path('onion-prices/delete/<int:price_id>/', views.delete_onion_price, name='delete_onion_price'),
    path('onion-prices/edit/<int:price_id>/', views.edit_onion_price, name='edit_onion_price'),
    
    # Import/Export URLs
    path('onion-prices/export/csv/', views.export_prices_csv, name='export_prices_csv'),
    path('onion-prices/export/excel/', views.export_prices_excel, name='export_prices_excel'),
    path('onion-prices/import/', views.import_prices_csv, name='import_prices_csv'),
    path('onion-prices/sample-csv/', views.download_sample_csv, name='download_sample_csv'),
    path('onion-prices/bulk-delete/', views.bulk_delete_prices, name='bulk_delete_prices'),
    path('onion-prices/bulk-import/', views.bulk_import_prices, name='bulk_import_prices'),

    # Predictions Management
    path('predictions/', views.manage_predictions, name='manage_predictions'),
    path('predictions/generate/', views.generate_prediction, name='generate_prediction'),
    path('predictions/export-csv/', views.export_predictions_csv, name='export_predictions_csv'),
    path('predictions/export-excel/', views.export_predictions_excel, name='export_predictions_excel'),
    path('predictions/bulk-delete/', views.bulk_delete_predictions, name='bulk_delete_predictions'),
    path('predictions/<int:prediction_id>/details/', views.prediction_details, name='prediction_details'),
    
    # Users Management
    path('users/', views.manage_users, name='manage_users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/deactivate/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('users/activate/<int:user_id>/', views.activate_user, name='activate_user'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    
    # Market Factors Management
    path('factors/', views.manage_factors, name='manage_factors'),
    path('factors/add/', views.add_factor, name='add_factor'),
    path('factors/edit/<int:factor_id>/', views.edit_factor, name='edit_factor'),
    path('factors/delete/<int:factor_id>/', views.delete_factor, name='delete_factor'),
    
    # Additional pages
    path('settings/', views.system_settings, name='system_settings'),
    path('analytics/', views.system_analytics, name='system_analytics'),
]