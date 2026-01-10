# # onion_forecast/urls.py - FINAL
# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns = [
#     path('admin/', admin.site.urls),  # Django admin
#     path('admin-panel/', include('custom_admin.urls')),  # Custom admin - NOT 'forecast_app.custom_admin'
#     path('', include('forecast_app.urls')),  # Main app
# ]

# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# onion_forecast/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),  # Django admin
    path('admin-panel/', include('custom_admin.urls')),  # Custom admin
    path('', include('forecast_app.urls')),  # Main app
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)