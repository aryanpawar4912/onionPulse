# forecast_app/admin.py

from django.contrib import admin
from .models import *

class OnionPriceAdmin(admin.ModelAdmin):
    list_display = ('date', 'market', 'state', 'modal_price', 'arrival_quantity')
    list_filter = ('state', 'market', 'date')
    search_fields = ('market', 'state', 'district')
    list_per_page = 50

class PricePredictionAdmin(admin.ModelAdmin):
    list_display = ('forecast_date', 'market', 'predicted_modal_price', 'confidence_interval', 'created_at')
    list_filter = ('market', 'forecast_date')
    search_fields = ('market',)
    readonly_fields = ('created_at',)

class MarketFactorAdmin(admin.ModelAdmin):
    list_display = ('name', 'factor_type', 'impact_score', 'is_active')
    list_filter = ('factor_type', 'is_active')
    search_fields = ('name', 'description')

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'phone', 'location')
    list_filter = ('user_type',)
    search_fields = ('user__username', 'location')

admin.site.register(OnionPrice, OnionPriceAdmin)
admin.site.register(WeatherData)
admin.site.register(PredictionModel)
admin.site.register(PricePrediction, PricePredictionAdmin)
admin.site.register(MarketFactor, MarketFactorAdmin)
admin.site.register(UserProfile, UserProfileAdmin)