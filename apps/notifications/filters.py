"""
Filters for Notifications app.
"""
from django_filters import rest_framework as filters
from .models import Notification


class NotificationFilter(filters.FilterSet):
    """Filter for Notification model."""
    type = filters.ChoiceFilter(choices=Notification.NotificationType.choices)
    is_read = filters.BooleanFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Notification
        fields = ['type', 'is_read']
