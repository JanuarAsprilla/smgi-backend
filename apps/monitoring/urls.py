"""
SMGI Backend - Monitoring URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.monitoring import views

# Create router for viewsets
router = DefaultRouter()
router.register(r'snapshots', views.LayerSnapshotViewSet, basename='snapshot')
router.register(r'changes', views.ChangeDetectionResultViewSet, basename='change-detection')
router.register(r'jobs', views.MonitoringJobViewSet, basename='monitoring-job')
router.register(r'quality-rules', views.DataQualityRuleViewSet, basename='quality-rule')
router.register(r'system-health', views.SystemHealthMetricViewSet, basename='system-health')
# router.register(r'statistics', views.MonitoringStatisticsView, basename='statistics') # Incorrecto
# router.register(r'trigger-monitoring', views.trigger_monitoring, basename='trigger-monitoring') # Incorrecto
# router.register(r'dashboard', views.monitoring_dashboard, basename='dashboard') # Incorrecto

urlpatterns = [
    path('', include(router.urls)),
    # Añadir las vistas de función o APIView explícitamente
    path('statistics/', views.monitoring_statistics, name='monitoring-statistics'),
    path('trigger-monitoring/', views.trigger_monitoring, name='trigger-monitoring'),
    path('dashboard/', views.monitoring_dashboard, name='monitoring-dashboard'),
]