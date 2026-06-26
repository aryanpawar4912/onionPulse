# forecast_app/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views  # Add this import
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('historical/', views.historical_data, name='historical'),
    path('predict/', views.predict_price, name='predict'),
    path('predictions/', views.prediction_results, name='prediction_results'),
    path('recommendations/', views.user_recommendations, name='recommendations'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact_view, name='contact'),
    # Add authentication URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
     path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    # API endpoints
    path('api/prices/', views.api_get_prices, name='api_prices'),
    path('api/predict/', views.api_get_prediction, name='api_predict'),
]


   
