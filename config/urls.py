import os
"""
URL configuration for SMGI project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .api_root import api_root

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API Root
    path('api/v1/', api_root, name='api-root'),
    
    # Authentication (JWT)
    path('api/v1/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API v1 Apps
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/geodata/', include('apps.geodata.urls')),
    path('api/v1/agents/', include('apps.agents.urls')),
    path('api/v1/monitoring/', include('apps.monitoring.urls')),
    path('api/v1/alerts/', include('apps.alerts.urls')),
    path('api/v1/automation/', include('apps.automation.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Agregar ruta para descargas
from django.views.static import serve

if settings.DEBUG:
    urlpatterns += [
        path('downloads/<path:path>', serve, {
            'document_root': os.path.join(settings.BASE_DIR, 'data/exports'),
        }),
    ]