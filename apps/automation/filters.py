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
    description = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=Workflow.Status.choices)
    trigger_type = filters.CharFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    tags = filters.CharFilter(method='filter_tags')
    created_by = filters.NumberFilter()
    has_executions = filters.BooleanFilter(method='filter_has_executions')
    success_rate_min = filters.NumberFilter(method='filter_success_rate_min')
    
    class Meta:
        model = Workflow
        fields = ['name', 'status', 'trigger_type', 'is_active']
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags containing the value."""
        return queryset.filter(tags__contains=[value])
    
    def filter_has_executions(self, queryset, name, value):
        """Filter workflows that have or haven't been executed."""
        if value:
            return queryset.filter(execution_count__gt=0)
        return queryset.filter(execution_count=0)
    
    def filter_success_rate_min(self, queryset, name, value):
        """Filter workflows with minimum success rate."""
        from django.db.models import F, Case, When, FloatField
        return queryset.annotate(
            calculated_success_rate=Case(
                When(execution_count=0, then=0),
                default=(F('success_count') * 100.0) / F('execution_count'),
                output_field=FloatField()
            )
        ).filter(calculated_success_rate__gte=value)


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
    completed_after = filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_before = filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')
    created_by = filters.NumberFilter()
    duration_min = filters.NumberFilter(method='filter_duration_min')
    duration_max = filters.NumberFilter(method='filter_duration_max')
    has_errors = filters.BooleanFilter(method='filter_has_errors')
    
    class Meta:
        model = WorkflowExecution
        fields = ['workflow', 'status', 'trigger_source', 'is_active']
    
    def filter_duration_min(self, queryset, name, value):
        """Filter executions with minimum duration."""
        from django.db.models import F, ExpressionWrapper, DurationField
        from django.db.models.functions import Extract
        return queryset.filter(
            started_at__isnull=False,
            completed_at__isnull=False
        ).annotate(
            duration_seconds=Extract(
                ExpressionWrapper(F('completed_at') - F('started_at'), output_field=DurationField()),
                'epoch'
            )
        ).filter(duration_seconds__gte=value)
    
    def filter_duration_max(self, queryset, name, value):
        """Filter executions with maximum duration."""
        from django.db.models import F, ExpressionWrapper, DurationField
        from django.db.models.functions import Extract
        return queryset.filter(
            started_at__isnull=False,
            completed_at__isnull=False
        ).annotate(
            duration_seconds=Extract(
                ExpressionWrapper(F('completed_at') - F('started_at'), output_field=DurationField()),
                'epoch'
            )
        ).filter(duration_seconds__lte=value)
    
    def filter_has_errors(self, queryset, name, value):
        """Filter executions that have or haven't errors."""
        if value:
            return queryset.exclude(error_message='').exclude(error_message__isnull=True)
        return queryset.filter(error_message__in=['', None])


class AutomationRuleFilter(filters.FilterSet):
    """
    Filter for AutomationRule model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=AutomationRule.Status.choices)
    trigger_event = filters.CharFilter()
    workflow = filters.NumberFilter()
    workflow_name = filters.CharFilter(field_name='workflow__name', lookup_expr='icontains')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    created_by = filters.NumberFilter()
    has_been_triggered = filters.BooleanFilter(method='filter_has_been_triggered')
    trigger_count_min = filters.NumberFilter(field_name='trigger_count', lookup_expr='gte')
    
    class Meta:
        model = AutomationRule
        fields = ['name', 'status', 'trigger_event', 'workflow', 'is_active']
    
    def filter_has_been_triggered(self, queryset, name, value):
        """Filter rules that have or haven't been triggered."""
        if value:
            return queryset.filter(trigger_count__gt=0)
        return queryset.filter(trigger_count=0)
