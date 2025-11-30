"""
Serializers for Geodata app.
SMGI - Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from django.contrib.gis.geos import GEOSGeometry
import json
from .models import DataSource, Layer, Feature, Dataset, SyncLog


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
        return obj.layers.filter(is_active=True).count()


class LayerSerializer(serializers.ModelSerializer):
    """Serializer for Layer model."""
    data_source_name = serializers.CharField(source='data_source.name', read_only=True, allow_null=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    extent = GeometryField(required=False, allow_null=True)
    
    class Meta:
        model = Layer
        fields = [
            'id', 'data_source', 'data_source_name', 'name', 'description',
            'layer_type', 'geometry_type', 'srid', 'feature_count', 'extent', 'style',
            'properties_schema', 'metadata', 'is_public', 'is_queryable', 'is_active',
            'tags', 'original_filename', 'file_size',
            'created_by', 'created_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'feature_count',
            'original_filename', 'file_size'
        ]
    
    def to_representation(self, instance):
        """Custom representation to handle null data_source."""
        data = super().to_representation(instance)
        if instance.data_source is None:
            data['data_source_name'] = None
        return data


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
    geometry = serializers.JSONField()
    
    class Meta:
        model = Feature
        fields = ['layer', 'feature_id', 'geometry', 'properties']
    
    def validate_geometry(self, value):
        """Validate and convert GeoJSON geometry to GEOS geometry."""
        if value is None:
            raise serializers.ValidationError("La geometría es requerida")
        
        try:
            if isinstance(value, dict):
                geom = GEOSGeometry(json.dumps(value), srid=4326)
            elif isinstance(value, str):
                try:
                    geom = GEOSGeometry(value, srid=4326)
                except:
                    geom = GEOSGeometry(value, srid=4326)
            else:
                raise serializers.ValidationError("Formato de geometría no válido")
            
            return geom
        except Exception as e:
            raise serializers.ValidationError(f"Error al procesar geometría: {str(e)}")
    
    def create(self, validated_data):
        """Create feature with geometry."""
        return Feature.objects.create(**validated_data)


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for Dataset model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    layer_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Dataset
        fields = [
            'id', 'name', 'description', 'layers', 'is_public', 
            'metadata', 'tags', 'is_active', 'created_by', 'created_by_username',
            'created_at', 'updated_at', 'layer_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_layer_count(self, obj) -> int:
        return obj.layers.filter(is_active=True).count()


class SyncLogSerializer(serializers.ModelSerializer):
    """Serializer for SyncLog model."""
    data_source_name = serializers.CharField(source='data_source.name', read_only=True, allow_null=True)
    layer_name = serializers.CharField(source='layer.name', read_only=True, allow_null=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = SyncLog
        fields = [
            'id', 'data_source', 'data_source_name', 'layer', 'layer_name',
            'status', 'started_at', 'completed_at', 'duration',
            'records_processed', 'records_added', 'records_updated',
            'records_failed', 'error_message', 'details'
        ]
        read_only_fields = ['id', 'started_at']
    
    def get_duration(self, obj):
        """Calculate duration in seconds."""
        if obj.completed_at and obj.started_at:
            delta = obj.completed_at - obj.started_at
            return delta.total_seconds()
        return None