"""
SMGI Backend - Alerts URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.alerts import views

# Create router for viewsets
router = DefaultRouter()
router.register(r'alerts', views.AlertViewSet, basename='alert')
# --- REMOVED: ViewSets not belonging to 'alerts' app ---
# router.register(r'rules', views.AlertRuleViewSet, basename='alert-rule')
# router.register(r'channels', views.NotificationChannelViewSet, basename='notification-channel')

urlpatterns = [
    path('', include(router.urls)),
]
