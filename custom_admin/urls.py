# custom_admin/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Data Management
    path('onion-prices/', views.manage_onion_prices, name='manage_onion_prices'),
    path('predictions/', views.manage_predictions, name='manage_predictions'),
    path('users/', views.manage_users, name='manage_users'),
    
    # Actions
    path('add-user/', views.add_user, name='add_user'),
    path('generate-prediction/', views.generate_prediction, name='generate_prediction'),
    
    # Additional pages
    path('factors/', views.manage_factors, name='manage_factors'),
    path('settings/', views.system_settings, name='system_settings'),
    path('analytics/', views.system_analytics, name='system_analytics'),
]