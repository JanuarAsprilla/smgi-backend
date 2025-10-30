# apps/reports/urls.py
"""
SMGI Backend - Reports URLs
Sistema de Monitoreo Geoespacial Inteligente
URLs para el sistema de generación de informes
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.reports import views

# --- MEJORA: Definir app_name para namespacing ---
app_name = 'reports'

# Create router for viewsets
router = DefaultRouter()

# Register viewsets with descriptive basenames
router.register(r'reports', views.ReportViewSet, basename='report')
router.register(r'templates', views.ReportTemplateViewSet, basename='report-template')
router.register(r'generated', views.GeneratedReportViewSet, basename='generated-report')
router.register(r'schedules', views.ReportScheduleViewSet, basename='report-schedule')
router.register(r'executions', views.ReportExecutionViewSet, basename='report-execution')
router.register(r'preferences', views.NotificationPreferenceViewSet, basename='notification-preference')

# --- MEJORA: Añadir rutas para vistas de función ---
# Estas rutas son para vistas de función definidas en views.py
# que no están registradas en el router porque no son ViewSets.

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # --- MEJORA: Rutas para vistas de función ---
    # Estas rutas apuntan a vistas de función (@api_view) definidas en views.py
    path('statistics/', views.report_statistics, name='report-statistics'),
    path('trigger/', views.trigger_report_generation, name='trigger-report-generation'),
    path('download/', views.download_generated_report, name='download-generated-report'),
    
    # --- MEJORA: Rutas para acciones personalizadas en ViewSets ---
    # El DefaultRouter se encarga de registrar automáticamente las rutas @action
    # definidas dentro de los ViewSets. Por ejemplo:
    # - /reports/{id}/generate/ (definida en ReportViewSet)
    # - /reports/{id}/download/ (definida en ReportViewSet)
    # - /reports/{id}/schedule/ (definida en ReportViewSet)
    # - /reports/{id}/unschedule/ (definida en ReportViewSet)
    # - /reports/{id}/run-now/ (definida en ReportViewSet)
    # - /reports/statistics/ (definida en ReportViewSet)
    # - /reports/my-reports/ (definida en ReportViewSet)
    # - /reports/active-schedules/ (definida en ReportViewSet)
    # - /reports/recent-executions/ (definida en ReportViewSet)
    # - /templates/{id}/preview/ (definida en ReportTemplateViewSet)
    # - /templates/{id}/validate/ (definida en ReportTemplateViewSet)
    # - /generated/{id}/download/ (definida en GeneratedReportViewSet)
    # - /generated/{id}/re-generate/ (definida en GeneratedReportViewSet)
    # - /generated/{id}/details/ (definida en GeneratedReportViewSet)
    # - /schedules/{id}/toggle-active/ (definida en ReportScheduleViewSet)
    # - /schedules/{id}/run-now/ (definida en ReportScheduleViewSet)
    # - /schedules/{id}/executions/ (definida en ReportScheduleViewSet)
    # - /schedules/{id}/statistics/ (definida en ReportScheduleViewSet)
    
    # --- MEJORA: Rutas para documentación de la API (opcional, si se usa drf-spectacular) ---
    # Estas rutas son opcionales y dependen de la configuración global de drf-spectacular
    # en settings.py. Se incluyen aquí como ejemplo de buenas prácticas.
    # path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='reports:schema'), name='swagger-ui'),
    # path('schema/redoc/', SpectacularRedocView.as_view(url_name='reports:schema'), name='redoc'),
]
