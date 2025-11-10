"""
Filters for Alerts app.
"""
from django_filters import rest_framework as filters
from .models import AlertRule, Alert


class AlertRuleFilter(filters.FilterSet):
    """
    Filter for AlertRule model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    severity = filters.ChoiceFilter(choices=AlertRule.Severity.choices)
    trigger_type = filters.ChoiceFilter(choices=AlertRule.TriggerType.choices)
    is_enabled = filters.BooleanFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = AlertRule
        fields = ['name', 'severity', 'trigger_type', 'is_enabled', 'is_active']


class AlertFilter(filters.FilterSet):
    """
    Filter for Alert model.
    """
    title = filters.CharFilter(lookup_expr='icontains')
    rule = filters.NumberFilter()
    severity = filters.ChoiceFilter(choices=AlertRule.Severity.choices)
    status = filters.ChoiceFilter(choices=Alert.Status.choices)
    detection = filters.NumberFilter()
    monitor = filters.NumberFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    is_acknowledged = filters.BooleanFilter(method='filter_acknowledged')
    is_resolved = filters.BooleanFilter(method='filter_resolved')
    
    class Meta:
        model = Alert
        fields = ['title', 'rule', 'severity', 'status', 'detection', 'monitor', 'is_active']
    
    def filter_acknowledged(self, queryset, name, value):
        """Filter by acknowledged status."""
        if value:
            return queryset.exclude(acknowledged_at__isnull=True)
        return queryset.filter(acknowledged_at__isnull=True)
    
    def filter_resolved(self, queryset, name, value):
        """Filter by resolved status."""
        if value:
            return queryset.filter(status='resolved')
        return queryset.exclude(status='resolved')
