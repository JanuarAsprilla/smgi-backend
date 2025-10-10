"""
SMGI Backend - Main URLs Configuration
Sistema de Monitoreo Geoespacial Inteligente
Configuración profesional de URLs
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for monitoring
    """
    from django.db import connection
    from django.core.cache import cache
    
    health_status = {
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': '',
        'checks': {}
    }
    
    # Check database
    try:
        connection.ensure_connection()
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check cache
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health_status['checks']['cache'] = 'healthy'
        else:
            health_status['checks']['cache'] = 'unhealthy'
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['checks']['cache'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'
    
    from django.utils import timezone
    health_status['timestamp'] = timezone.now().isoformat()
    
    status_code = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return Response(health_status, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    API root endpoint with available endpoints
    """
    return Response({
        'message': 'SMGI Backend API',
        'version': '1.0.0',
        'endpoints': {
            'documentation': {
                'swagger': request.build_absolute_uri('/api/docs/'),
                'redoc': request.build_absolute_uri('/api/redoc/'),
                'schema': request.build_absolute_uri('/api/schema/'),
            },
            'authentication': request.build_absolute_uri('/api/v1/auth/'),
            'services': request.build_absolute_uri('/api/v1/services/'),
            'layers': request.build_absolute_uri('/api/v1/layers/'),
            'monitoring': request.build_absolute_uri('/api/v1/monitoring/'),
            'alerts': request.build_absolute_uri('/api/v1/alerts/'),
            'reports': request.build_absolute_uri('/api/v1/reports/'),
            'health': request.build_absolute_uri('/health/'),
        }
    })


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Health check
    path('health/', health_check, name='health-check'),
    
    # API root
    path('api/', api_root, name='api-root'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API v1 endpoints
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/services/', include('apps.gis_services.urls')),
    path('api/v1/layers/', include(('apps.gis_services.views', 'layers'), namespace='layers')),
    path('api/v1/monitoring/', include('apps.monitoring.urls')),
    path('api/v1/alerts/', include('apps.alerts.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Add debug toolbar if installed
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Custom admin site configuration
admin.site.site_header = "SMGI - Sistema de Monitoreo Geoespacial Inteligente"
admin.site.site_title = "SMGI Admin"
admin.site.index_title = "Panel de Administración"