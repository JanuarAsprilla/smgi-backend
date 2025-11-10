"""
URLs for Agents app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AgentCategoryViewSet,
    AgentViewSet,
    AgentExecutionViewSet,
    AgentScheduleViewSet,
    AgentTemplateViewSet,
)

router = DefaultRouter()
router.register(r'categories', AgentCategoryViewSet, basename='agentcategory')
router.register(r'agents', AgentViewSet, basename='agent')
router.register(r'executions', AgentExecutionViewSet, basename='agentexecution')
router.register(r'schedules', AgentScheduleViewSet, basename='agentschedule')
router.register(r'templates', AgentTemplateViewSet, basename='agenttemplate')

urlpatterns = [
    path('', include(router.urls)),
]
