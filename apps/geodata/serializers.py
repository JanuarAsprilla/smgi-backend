"""
Serializers for Geodata app.
"""
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from .models import DataSource, Layer, Feature, Dataset, SyncLog
from rest_framework_gis.serializers import GeoFeatureModelSerializer


class DataSourceSerializer(serializers.ModelSerializer):
    """Serializer for DataSource model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    layer_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'description', 'source_type', 'url', 'credentials',
            'configuration', 'status', 'refresh_interval', 'last_sync', 'metadata',
            'tags', 'is_active', 'created_by', 'created_by_username', 
            'created_at', 'updated_at', 'layer_count'
        ]
        read_only_fields = ['id', 'last_sync', 'status', 'created_at', 'updated_at']
        extra_kwargs = {
            'credentials': {'write_only': True}
        }
    
    def get_layer_count(self, obj) -> int:
        """Get number of layers for this data source."""
        return obj.layers.filter(is_active=True).count()


class LayerSerializer(serializers.ModelSerializer):
    """Serializer for Layer model."""
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    feature_count = serializers.SerializerMethodField()
    extent = GeometryField(required=False, allow_null=True)
    
    class Meta:
        model = Layer
        fields = [
            'id', 'data_source', 'data_source_name', 'name', 'description',
            'layer_type', 'geometry_type', 'srid', 'extent', 'style',
            'metadata', 'is_public', 'is_active', 'created_by',
            'created_by_username', 'created_at', 'updated_at', 'feature_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_feature_count(self, obj) -> int:
        """Get number of features in this layer."""
        return obj.features.filter(is_active=True).count()


class FeatureSerializer(serializers.ModelSerializer):
    """Serializer for Feature model."""
    layer_name = serializers.CharField(source='layer.name', read_only=True)
    geometry = GeometryField(required=False, allow_null=True)
    
    class Meta:
        model = Feature
        fields = [
            'id', 'layer', 'layer_name', 'feature_id', 'geometry',
            'properties', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FeatureCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating features."""
    geometry = GeometryField()
    
    class Meta:
        model = Feature
        fields = ['layer', 'feature_id', 'geometry', 'properties']


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for Dataset model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    layer_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description', 'source_type', 'file_path',
            'metadata', 'is_active', 'created_by',
            'created_by_username', 'created_at', 'updated_at', 'layer_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_layer_count(self, obj) -> int:
        """Get number of layers in this dataset."""
        return obj.layers.filter(is_active=True).count()


class SyncLogSerializer(serializers.ModelSerializer):
    """Serializer for SyncLog model."""
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    
    class Meta:
        model = SyncLog
        fields = [
            'id', 'data_source', 'data_source_name', 'sync_type',
            'status', 'started_at', 'completed_at', 'records_processed',
            'records_added', 'records_updated', 'records_deleted',
            'error_message', 'metadata'
        ]
        read_only_fields = ['id']
        
class FeatureGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for Feature."""

    class Meta:
        model = Feature
        geo_field = "geometry"
        fields = [
            'id',
            'layer',
            'feature_id',
            'geometry',
            'properties',
            'is_active',
            'created_at',
            'updated_at'
        ]