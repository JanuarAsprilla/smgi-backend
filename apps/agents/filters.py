"""
Filters for Agents app.
"""
from django_filters import rest_framework as filters
from .models import Agent, AgentExecution, AgentSchedule


class AgentFilter(filters.FilterSet):
    """
    Filter for Agent model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    description = filters.CharFilter(lookup_expr='icontains')
    agent_type = filters.ChoiceFilter(choices=Agent.AgentType.choices)
    status = filters.ChoiceFilter(choices=Agent.Status.choices)
    category = filters.NumberFilter()
    is_public = filters.BooleanFilter()
    is_verified = filters.BooleanFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    min_rating = filters.NumberFilter(field_name='rating', lookup_expr='gte')
    tags = filters.CharFilter(method='filter_tags')
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = Agent
        fields = ['name', 'agent_type', 'status', 'category', 'is_public', 'is_verified', 'is_active']
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags containing the value."""
        return queryset.filter(tags__contains=[value])
    
    def filter_search(self, queryset, name, value):
        """Search in name, description, and tags."""
        return queryset.filter(
            models.Q(name__icontains=value) |
            models.Q(description__icontains=value) |
            models.Q(tags__contains=[value])
        )


class AgentExecutionFilter(filters.FilterSet):
    """
    Filter for AgentExecution model.
    """
    agent = filters.NumberFilter()
    agent_name = filters.CharFilter(field_name='agent__name', lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=AgentExecution.Status.choices)
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    started_after = filters.DateTimeFilter(field_name='started_at', lookup_expr='gte')
    started_before = filters.DateTimeFilter(field_name='started_at', lookup_expr='lte')
    
    class Meta:
        model = AgentExecution
        fields = ['agent', 'status', 'is_active']


class AgentScheduleFilter(filters.FilterSet):
    """
    Filter for AgentSchedule model.
    """
    agent = filters.NumberFilter()
    agent_name = filters.CharFilter(field_name='agent__name', lookup_expr='icontains')
    schedule_type = filters.ChoiceFilter(choices=AgentSchedule.ScheduleType.choices)
    is_enabled = filters.BooleanFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = AgentSchedule
        fields = ['agent', 'schedule_type', 'is_enabled', 'is_active']
