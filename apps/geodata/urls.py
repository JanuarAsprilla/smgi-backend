from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DataSourceViewSet,
    LayerViewSet,
    FeatureViewSet,
    DatasetViewSet,
    SyncLogViewSet
)

router = DefaultRouter()
router.register(r'datasources', DataSourceViewSet, basename='datasource')
router.register(r'layers', LayerViewSet, basename='layer')
router.register(r'features', FeatureViewSet, basename='feature')
router.register(r'datasets', DatasetViewSet, basename='dataset')
router.register(r'synclogs', SyncLogViewSet, basename='synclog')

urlpatterns = [
    path('', include(router.urls)),
]
