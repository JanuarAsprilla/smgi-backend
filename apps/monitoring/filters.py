"""
Filters for Monitoring app.
"""
from django_filters import rest_framework as filters
from .models import MonitoringProject, Monitor, Detection


class MonitoringProjectFilter(filters.FilterSet):
    """
    Filter for MonitoringProject model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=MonitoringProject.Status.choices)
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    start_after = filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_before = filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')
    tags = filters.CharFilter(method='filter_tags')
    
    class Meta:
        model = MonitoringProject
        fields = ['name', 'status', 'is_active']
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags containing the value."""
        return queryset.filter(tags__contains=[value])


class MonitorFilter(filters.FilterSet):
    """
    Filter for Monitor model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    project = filters.NumberFilter()
    project_name = filters.CharFilter(field_name='project__name', lookup_expr='icontains')
    monitor_type = filters.ChoiceFilter(choices=Monitor.MonitorType.choices)
    status = filters.ChoiceFilter(choices=Monitor.Status.choices)
    agent = filters.NumberFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    tags = filters.CharFilter(method='filter_tags')
    
    class Meta:
        model = Monitor
        fields = ['name', 'project', 'monitor_type', 'status', 'agent', 'is_active']
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags containing the value."""
        return queryset.filter(tags__contains=[value])


class DetectionFilter(filters.FilterSet):
    """
    Filter for Detection model.
    """
    title = filters.CharFilter(lookup_expr='icontains')
    monitor = filters.NumberFilter()
    monitor_name = filters.CharFilter(field_name='monitor__name', lookup_expr='icontains')
    project = filters.NumberFilter(field_name='monitor__project')
    severity = filters.ChoiceFilter(choices=Detection.Severity.choices)
    status = filters.ChoiceFilter(choices=Detection.Status.choices)
    detected_after = filters.DateTimeFilter(field_name='detected_at', lookup_expr='gte')
    detected_before = filters.DateTimeFilter(field_name='detected_at', lookup_expr='lte')
    min_confidence = filters.NumberFilter(field_name='confidence_score', lookup_expr='gte')
    
    class Meta:
        model = Detection
        fields = ['title', 'monitor', 'severity', 'status', 'is_active']
