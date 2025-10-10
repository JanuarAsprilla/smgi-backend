"""
SMGI Backend - GIS Services URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.gis_services import views

# Create router
router = DefaultRouter()
router.register(r'', views.ArcGISServiceViewSet, basename='service')
router.register(r'tags', views.ServiceTagViewSet, basename='service-tag')
router.register(r'endpoints', views.ServiceEndpointViewSet, basename='service-endpoint')

# Layer routes (separate from services)
layer_router = DefaultRouter()
layer_router.register(r'', views.SpatialLayerViewSet, basename='layer')

urlpatterns = [
    # Service routes
    path('', include(router.urls)),
]

# Add layer routes with different prefix
app_name = 'gis_services'