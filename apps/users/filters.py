"""
Filters for Users app.
"""
from django_filters import rest_framework as filters
from .models import User


class UserFilter(filters.FilterSet):
    """
    Filter for User model.
    """
    username = filters.CharFilter(lookup_expr='icontains')
    email = filters.CharFilter(lookup_expr='icontains')
    first_name = filters.CharFilter(lookup_expr='icontains')
    last_name = filters.CharFilter(lookup_expr='icontains')
    organization = filters.CharFilter(lookup_expr='icontains')
    role = filters.ChoiceFilter(choices=User.UserRole.choices)
    is_verified = filters.BooleanFilter()
    is_active = filters.BooleanFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'organization',
            'role',
            'is_verified',
            'is_active',
        ]
