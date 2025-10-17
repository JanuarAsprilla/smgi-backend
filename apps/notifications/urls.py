# apps/notifications/urls.py
"""
SMGI Backend - Notifications URLs
Sistema de Monitoreo Geoespacial Inteligente
URLs para el sistema de notificaciones
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notifications import views

# --- MEJORA: Definir app_name para namespacing (opcional pero recomendado) ---
app_name = 'notifications'

# Crear el router
router = DefaultRouter()

# Registrar ViewSets
# Asumimos que views.NotificationViewSet existe
router.register(r'notifications', views.NotificationViewSet, basename='notification')
# --- MEJORA: Espacio para registrar más ViewSets en el futuro ---
# Ejemplo:
# router.register(r'email-notifications', views.EmailNotificationViewSet, basename='email-notification')
# router.register(r'webhook-notifications', views.WebhookNotificationViewSet, basename='webhook-notification')
# router.register(r'preferences', views.NotificationPreferenceViewSet, basename='notification-preference')

# Definir las rutas URL
urlpatterns = [
    # Incluir las rutas generadas por el router
    path('', include(router.urls)),
    
    # --- MEJORA: Espacio para rutas de vistas basadas en funciones o APIViews ---
    # Ejemplo:
    # path('stats/', views.notification_statistics, name='notification-stats'),
    # path('preferences/me/', views.my_notification_preferences, name='my-notification-preferences'),
    # path('send-test/', views.send_test_notification, name='send-test-notification'),
]
