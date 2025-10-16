# apps/gis_services/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Crear un router para los ViewSets
router = DefaultRouter()
router.register(r'services', views.ArcGISServiceViewSet, basename='service')
router.register(r'layers', views.SpatialLayerViewSet, basename='layer')
router.register(r'tags', views.ServiceTagViewSet, basename='tag')
router.register(r'endpoints', views.ServiceEndpointViewSet, basename='endpoint')

# Patrón de URL principal para la app
urlpatterns = [
    # Incluir las URLs generadas por el router
    path('', include(router.urls)),
]