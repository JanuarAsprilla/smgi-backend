"""
URLs for Monitoring app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MonitoringProjectViewSet,
    MonitorViewSet,
    DetectionViewSet,
    ChangeRecordViewSet,
    MonitoringReportViewSet,
    BaselineViewSet,
    MonitoringStatisticsViewSet,
)

router = DefaultRouter()
router.register(r'projects', MonitoringProjectViewSet, basename='monitoringproject')
router.register(r'monitors', MonitorViewSet, basename='monitor')
router.register(r'detections', DetectionViewSet, basename='detection')
router.register(r'changes', ChangeRecordViewSet, basename='changerecord')
router.register(r'reports', MonitoringReportViewSet, basename='monitoringreport')
router.register(r'baselines', BaselineViewSet, basename='baseline')
router.register(r'statistics', MonitoringStatisticsViewSet, basename='monitoringstatistics')

urlpatterns = [
    path('', include(router.urls)),
]
