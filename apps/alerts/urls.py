# apps/alerts/urls.py
"""
SMGI Backend - Alerts URLs
Sistema de Monitoreo Geoespacial Inteligente
URLs para el sistema de alertas
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.alerts import views

# --- MEJORA: Definir app_name para namespacing (opcional pero recomendado) ---
app_name = 'alerts'

# Create router for viewsets
router = DefaultRouter()
router.register(r'alerts', views.AlertViewSet, basename='alert')
# --- REMOVED: ViewSets not belonging to 'alerts' app ---
# router.register(r'rules', views.AlertRuleViewSet, basename='alert-rule')
# router.register(r'channels', views.NotificationChannelViewSet, basename='notification-channel')

# --- MEJORA: Espacio para registrar más ViewSets en el futuro ---
# Ejemplo:
# router.register(r'actions', views.AlertActionViewSet, basename='alert-action')
# router.register(r'comments', views.AlertCommentViewSet, basename='alert-comment')

urlpatterns = [
    path('', include(router.urls)),
    
    # --- MEJORA: Espacio para rutas de vistas basadas en funciones o APIViews ---
    # Ejemplo:
    # path('statistics/', views.alert_statistics, name='alert-statistics'),
    # path('bulk-actions/', views.bulk_alert_actions, name='bulk-alert-actions'),
]
