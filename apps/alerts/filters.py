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
    has_channels = filters.BooleanFilter(method='filter_has_channels')
    has_recipients = filters.BooleanFilter(method='filter_has_recipients')
    
    class Meta:
        model = AlertRule
        fields = ['name', 'severity', 'trigger_type', 'is_enabled', 'is_active']
    
    def filter_has_channels(self, queryset, name, value):
        """Filter rules that have channels configured."""
        if value:
            return queryset.filter(channels__isnull=False).distinct()
        return queryset.filter(channels__isnull=True)
    
    def filter_has_recipients(self, queryset, name, value):
        """Filter rules that have recipients configured."""
        if value:
            return queryset.filter(recipients__isnull=False).distinct()
        return queryset.filter(recipients__isnull=True)


class AlertFilter(filters.FilterSet):
    """
    Filter for Alert model.
    """
    title = filters.CharFilter(lookup_expr='icontains')
    message = filters.CharFilter(lookup_expr='icontains')
    rule = filters.NumberFilter()
    severity = filters.ChoiceFilter(choices=AlertRule.Severity.choices)
    status = filters.ChoiceFilter(choices=Alert.Status.choices)
    detection = filters.NumberFilter()
    monitor = filters.NumberFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    sent_after = filters.DateTimeFilter(field_name='sent_at', lookup_expr='gte')
    sent_before = filters.DateTimeFilter(field_name='sent_at', lookup_expr='lte')
    is_acknowledged = filters.BooleanFilter(method='filter_acknowledged')
    is_resolved = filters.BooleanFilter(method='filter_resolved')
    is_critical = filters.BooleanFilter(method='filter_critical')
    age_hours = filters.NumberFilter(method='filter_age_hours')
    
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
    
    def filter_critical(self, queryset, name, value):
        """Filter critical alerts."""
        if value:
            return queryset.filter(severity='critical')
        return queryset.exclude(severity='critical')
    
    def filter_age_hours(self, queryset, name, value):
        """Filter alerts older than specified hours."""
        from django.utils import timezone
        from datetime import timedelta
        threshold = timezone.now() - timedelta(hours=value)
        return queryset.filter(created_at__lt=threshold)
