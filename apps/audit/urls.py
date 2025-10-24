# apps/audit/urls.py
"""
SMGI Backend - Audit URLs
Sistema de Monitoreo Geoespacial Inteligente
URLs para el sistema de auditoría
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.utils import extend_schema

from apps.audit import views

# --- MEJORA: Crear router para ViewSets ---
router = DefaultRouter()

# Registrar ViewSets con nombres base descriptivos
router.register(r'logs', views.AuditLogViewSet, basename='audit-log')
router.register(r'trails', views.AuditTrailViewSet, basename='audit-trail')
router.register(r'policies', views.AuditPolicyViewSet, basename='audit-policy')
router.register(r'configurations', views.AuditConfigurationViewSet, basename='audit-configuration')

# --- MEJORA: Definir urlpatterns ---
urlpatterns = [
    # Incluir rutas generadas por el router
    path('', include(router.urls)),
    
    # --- MEJORA: Rutas para vistas de función ---
    # Estas rutas apuntan a vistas de función (@api_view) definidas en views.py
    path('statistics/', views.audit_statistics, name='audit-statistics'),
    path('trigger/', views.trigger_audit, name='trigger-audit'),
    path('download/', views.download_audit_log, name='download-audit-log'),
    
    # --- MEJORA: Rutas para acciones personalizadas en ViewSets ---
    # El DefaultRouter se encarga de registrar automáticamente las rutas @action
    # definidas dentro de los ViewSets. Por ejemplo:
    # - /logs/{id}/mark-read/ (definida en AuditLogViewSet)
    # - /logs/{id}/mark-unread/ (definida en AuditLogViewSet)
    # - /logs/{id}/archive/ (definida en AuditLogViewSet)
    # - /logs/{id}/unarchive/ (definida en AuditLogViewSet)
    # - /logs/{id}/delete/ (definida en AuditLogViewSet)
    # - /logs/bulk-action/ (definida en AuditLogViewSet)
    # - /logs/stats/ (definida en AuditLogViewSet)
    # - /logs/trends/ (definida en AuditLogViewSet)
    # - /logs/filters/ (definida en AuditLogViewSet)
    # - /logs/search/ (definida en AuditLogViewSet)
    # - /logs/sort/ (definida en AuditLogViewSet)
    # - /logs/paginate/ (definida en AuditLogViewSet)
    # - /logs/export/ (definida en AuditLogViewSet)
    # - /logs/import/ (definida en AuditLogViewSet)
    # - /logs/sync/ (definida en AuditLogViewSet)
    # - /logs/validate/ (definida en AuditLogViewSet)
    # - /logs/transform/ (definida en AuditLogViewSet)
    # - /logs/aggregate/ (definida en AuditLogViewSet)
    # - /logs/group-by/ (definida en AuditLogViewSet)
    # - /logs/join/ (definida en AuditLogViewSet)
    # - /trails/{id}/mark-read/ (definida en AuditTrailViewSet)
    # - /trails/{id}/mark-unread/ (definida en AuditTrailViewSet)
    # - /trails/{id}/archive/ (definida en AuditTrailViewSet)
    # - /trails/{id}/unarchive/ (definida en AuditTrailViewSet)
    # - /trails/{id}/delete/ (definida en AuditTrailViewSet)
    # - /trails/bulk-action/ (definida en AuditTrailViewSet)
    # - /trails/stats/ (definida en AuditTrailViewSet)
    # - /trails/trends/ (definida en AuditTrailViewSet)
    # - /trails/filters/ (definida en AuditTrailViewSet)
    # - /trails/search/ (definida en AuditTrailViewSet)
    # - /trails/sort/ (definida en AuditTrailViewSet)
    # - /trails/paginate/ (definida en AuditTrailViewSet)
    # - /trails/export/ (definida en AuditTrailViewSet)
    # - /trails/import/ (definida en AuditTrailViewSet)
    # - /trails/sync/ (definida en AuditTrailViewSet)
    # - /trails/validate/ (definida en AuditTrailViewSet)
    # - /trails/transform/ (definida en AuditTrailViewSet)
    # - /trails/aggregate/ (definida en AuditTrailViewSet)
    # - /trails/group-by/ (definida en AuditTrailViewSet)
    # - /trails/join/ (definida en AuditTrailViewSet)
    # - /policies/{id}/mark-active/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/mark-inactive/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/toggle-status/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/enable/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/disable/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/activate/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/deactivate/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/run-now/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/schedule/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/unschedule/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/execute/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/test/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/validate/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/preview/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/clone/ (definida en AuditPolicyViewSet)
    # - /policies/{id}/delete/ (definida en AuditPolicyViewSet)
    # - /policies/bulk-action/ (definida en AuditPolicyViewSet)
    # - /policies/stats/ (definida en AuditPolicyViewSet)
    # - /policies/trends/ (definida en AuditPolicyViewSet)
    # - /policies/filters/ (definida en AuditPolicyViewSet)
    # - /policies/search/ (definida en AuditPolicyViewSet)
    # - /policies/sort/ (definida en AuditPolicyViewSet)
    # - /policies/paginate/ (definida en AuditPolicyViewSet)
    # - /policies/export/ (definida en AuditPolicyViewSet)
    # - /policies/import/ (definida en AuditPolicyViewSet)
    # - /policies/sync/ (definida en AuditPolicyViewSet)
    # - /policies/validate/ (definida en AuditPolicyViewSet)
    # - /policies/transform/ (definida en AuditPolicyViewSet)
    # - /policies/aggregate/ (definida en AuditPolicyViewSet)
    # - /policies/group-by/ (definida en AuditPolicyViewSet)
    # - /policies/join/ (definida en AuditPolicyViewSet)
    # - /configurations/{id}/mark-active/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/mark-inactive/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/toggle-status/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/enable/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/disable/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/activate/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/deactivate/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/run-now/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/schedule/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/unschedule/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/execute/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/test/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/validate/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/preview/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/clone/ (definida en AuditConfigurationViewSet)
    # - /configurations/{id}/delete/ (definida en AuditConfigurationViewSet)
    # - /configurations/bulk-action/ (definida en AuditConfigurationViewSet)
    # - /configurations/stats/ (definida en AuditConfigurationViewSet)
    # - /configurations/trends/ (definida en AuditConfigurationViewSet)
    # - /configurations/filters/ (definida en AuditConfigurationViewSet)
    # - /configurations/search/ (definida en AuditConfigurationViewSet)
    # - /configurations/sort/ (definida en AuditConfigurationViewSet)
    # - /configurations/paginate/ (definida en AuditConfigurationViewSet)
    # - /configurations/export/ (definida en AuditConfigurationViewSet)
    # - /configurations/import/ (definida en AuditConfigurationViewSet)
    # - /configurations/sync/ (definida en AuditConfigurationViewSet)
    # - /configurations/validate/ (definida en AuditConfigurationViewSet)
    # - /configurations/transform/ (definida en AuditConfigurationViewSet)
    # - /configurations/aggregate/ (definida en AuditConfigurationViewSet)
    # - /configurations/group-by/ (definida en AuditConfigurationViewSet)
    # - /configurations/join/ (definida en AuditConfigurationViewSet)
]

# --- MEJORA: Definir app_name para namespacing ---
# Esto permite referenciar las URLs con 'audit:url_name'
app_name = 'audit'
