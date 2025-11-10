"""
Filters for Geodata app.
"""
from django_filters import rest_framework as filters
from .models import DataSource, Layer, Feature, Dataset


class DataSourceFilter(filters.FilterSet):
    """
    Filter for DataSource model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    source_type = filters.ChoiceFilter(choices=DataSource.SourceType.choices)
    status = filters.ChoiceFilter(choices=DataSource.Status.choices)
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    tags = filters.CharFilter(method='filter_tags')
    
    class Meta:
        model = DataSource
        fields = ['name', 'source_type', 'status', 'is_active']
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags containing the value."""
        return queryset.filter(tags__contains=[value])


class LayerFilter(filters.FilterSet):
    """
    Filter for Layer model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    data_source = filters.NumberFilter()
    data_source_name = filters.CharFilter(field_name='data_source__name', lookup_expr='icontains')
    layer_type = filters.ChoiceFilter(choices=Layer.LayerType.choices)
    geometry_type = filters.ChoiceFilter(choices=Layer.GeometryType.choices)
    is_public = filters.BooleanFilter()
    is_queryable = filters.BooleanFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    tags = filters.CharFilter(method='filter_tags')
    
    class Meta:
        model = Layer
        fields = ['name', 'data_source', 'layer_type', 'geometry_type', 'is_public', 'is_queryable', 'is_active']
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags containing the value."""
        return queryset.filter(tags__contains=[value])


class FeatureFilter(filters.FilterSet):
    """
    Filter for Feature model.
    """
    layer = filters.NumberFilter()
    layer_name = filters.CharFilter(field_name='layer__name', lookup_expr='icontains')
    feature_id = filters.CharFilter(lookup_expr='icontains')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Feature
        fields = ['layer', 'feature_id', 'is_active']


class DatasetFilter(filters.FilterSet):
    """
    Filter for Dataset model.
    """
    name = filters.CharFilter(lookup_expr='icontains')
    is_public = filters.BooleanFilter()
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    tags = filters.CharFilter(method='filter_tags')
    
    class Meta:
        model = Dataset
        fields = ['name', 'is_public', 'is_active']
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags containing the value."""
        return queryset.filter(tags__contains=[value])
