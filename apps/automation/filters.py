"""
Filters for Automation app.
"""
from django_filters import rest_framework as filters
from .models import Workflow, WorkflowExecution, AutomationRule


class WorkflowFilter(filters.FilterSet):
    """
    Filter for Workflow model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=Workflow.Status.choices)
    trigger_type = filters.CharFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    tags = filters.CharFilter(method='filter_tags')
    
    class Meta:
        model = Workflow
        fields = ['name', 'status', 'trigger_type', 'is_active']
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags containing the value."""
        return queryset.filter(tags__contains=[value])


class WorkflowExecutionFilter(filters.FilterSet):
    """
    Filter for WorkflowExecution model.
    """
    workflow = filters.NumberFilter()
    workflow_name = filters.CharFilter(field_name='workflow__name', lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=WorkflowExecution.Status.choices)
    trigger_source = filters.CharFilter(lookup_expr='icontains')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    started_after = filters.DateTimeFilter(field_name='started_at', lookup_expr='gte')
    started_before = filters.DateTimeFilter(field_name='started_at', lookup_expr='lte')
    
    class Meta:
        model = WorkflowExecution
        fields = ['workflow', 'status', 'trigger_source', 'is_active']


class AutomationRuleFilter(filters.FilterSet):
    """
    Filter for AutomationRule model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=AutomationRule.Status.choices)
    trigger_event = filters.CharFilter()
    workflow = filters.NumberFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = AutomationRule
        fields = ['name', 'status', 'trigger_event', 'workflow', 'is_active']
