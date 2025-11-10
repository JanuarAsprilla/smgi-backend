"""
URLs for Automation app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkflowViewSet,
    WorkflowTaskViewSet,
    WorkflowExecutionViewSet,
    AutomationRuleViewSet,
    WorkflowScheduleViewSet,
    AutomationStatisticsViewSet,
)

router = DefaultRouter()
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'tasks', WorkflowTaskViewSet, basename='workflowtask')
router.register(r'executions', WorkflowExecutionViewSet, basename='workflowexecution')
router.register(r'rules', AutomationRuleViewSet, basename='automationrule')
router.register(r'schedules', WorkflowScheduleViewSet, basename='workflowschedule')
router.register(r'statistics', AutomationStatisticsViewSet, basename='automationstatistics')

urlpatterns = [
    path('', include(router.urls)),
]
