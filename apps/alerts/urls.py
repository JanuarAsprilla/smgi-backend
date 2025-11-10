"""
URLs for Alerts app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AlertChannelViewSet,
    AlertRuleViewSet,
    AlertViewSet,
    AlertLogViewSet,
    AlertSubscriptionViewSet,
    AlertTemplateViewSet,
    AlertStatisticsViewSet,
)

router = DefaultRouter()
router.register(r'channels', AlertChannelViewSet, basename='alertchannel')
router.register(r'rules', AlertRuleViewSet, basename='alertrule')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'logs', AlertLogViewSet, basename='alertlog')
router.register(r'subscriptions', AlertSubscriptionViewSet, basename='alertsubscription')
router.register(r'templates', AlertTemplateViewSet, basename='alerttemplate')
router.register(r'statistics', AlertStatisticsViewSet, basename='alertstatistics')

urlpatterns = [
    path('', include(router.urls)),
]
