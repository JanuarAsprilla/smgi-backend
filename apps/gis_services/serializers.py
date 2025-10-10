"""
SMGI Backend - GIS Services Serializers
Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.utils.translation import gettext_lazy as _

from apps.gis_services.models import (
    ArcGISService, SpatialLayer, LayerField,
    ServiceEndpoint, ServiceConfiguration,
    ServiceTag, ServiceMetrics
)


class ServiceTagSerializer(serializers.ModelSerializer):
    """Serializer for Service Tags"""
    
    class Meta:
        model = ServiceTag
        fields = ['id', 'name', 'color', 'description', 'created', 'modified']
        read_only_fields = ['id', 'created', 'modified']


class ServiceConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for Service Configuration"""
    
    class Meta:
        model = ServiceConfiguration
        fields = [
            'id', 'headers', 'query_parameters', 'max_retries',
            'retry_delay', 'backoff_factor', 'cache_responses',
            'cache_duration', 'requests_per_minute', 'data_format',
            'health_check_interval', 'performance_monitoring',
            'notification_settings'
        ]
        read_only_fields = ['id']


class ArcGISServiceListSerializer(serializers.ModelSerializer):
    """Simplified serializer for service listing"""
    
    tags = ServiceTagSerializer(many=True, read_only=True)
    layer_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ArcGISService
        fields = [
            'id', 'name', 'service_type', 'base_url', 'status',
            'is_monitored', 'last_check', 'last_successful_check',
            'tags', 'layer_count', 'created', 'modified'
        ]
        read_only_fields = ['id', 'status', 'last_check', 'last_successful_check', 'created', 'modified']
    
    def get_layer_count(self, obj):
        return obj.spatial_layers.filter(is_removed=False).count()


class ArcGISServiceDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for service"""
    
    tags = ServiceTagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=ServiceTag.objects.all(),
        source='tags',
        required=False
    )
    configuration = ServiceConfigurationSerializer(read_only=True)
    layer_count = serializers.SerializerMethodField()
    monitored_layer_count = serializers.SerializerMethodField()
    is_online = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ArcGISService
        fields = [
            'id', 'name', 'description', 'base_url', 'service_type',
            'requires_authentication', 'timeout_seconds', 'max_record_count',
            'is_monitored', 'monitoring_interval', 'version', 'capabilities',
            'metadata', 'status', 'last_check', 'last_successful_check',
            'consecutive_failures', 'extent', 'tags', 'tag_ids',
            'configuration', 'layer_count', 'monitored_layer_count',
            'is_online', 'created_by', 'created_by_name',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'status', 'last_check', 'last_successful_check',
            'consecutive_failures', 'version', 'capabilities', 'is_online',
            'created', 'modified'
        ]
    
    def get_layer_count(self, obj):
        return obj.spatial_layers.filter(is_removed=False).count()
    
    def get_monitored_layer_count(self, obj):
        return obj.spatial_layers.filter(is_monitored=True, is_removed=False).count()
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class ArcGISServiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating services"""
    
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=ServiceTag.objects.all(),
        source='tags',
        required=False
    )
    
    # Optional credentials
    username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = ArcGISService
        fields = [
            'name', 'description', 'base_url', 'service_type',
            'requires_authentication', 'username', 'password',
            'timeout_seconds', 'max_record_count',
            'is_monitored', 'monitoring_interval',
            'metadata', 'tag_ids'
        ]
    
    def create(self, validated_data):
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        tags = validated_data.pop('tags', [])
        
        # Set created_by from request context
        validated_data['created_by'] = self.context['request'].user
        
        service = ArcGISService.objects.create(**validated_data)
        
        # Add tags
        if tags:
            service.tags.set(tags)
        
        # Create credentials if provided
        if username or password:
            from apps.gis_services.models import ServiceCredential
            ServiceCredential.objects.create(
                service=service,
                username=username or '',
                password=password or ''  # Should be encrypted in production
            )
        
        # Create default configuration
        ServiceConfiguration.objects.create(service=service)
        
        return service


class LayerFieldSerializer(serializers.ModelSerializer):
    """Serializer for Layer Fields"""
    
    class Meta:
        model = LayerField
        fields = [
            'id', 'name', 'alias', 'field_type', 'length',
            'is_nullable', 'default_value', 'monitor_for_changes',
            'change_threshold'
        ]
        read_only_fields = ['id']


class SpatialLayerListSerializer(serializers.ModelSerializer):
    """Simplified serializer for layer listing"""
    
    service_name = serializers.CharField(source='service.name', read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = SpatialLayer
        fields = [
            'id', 'service', 'service_name', 'layer_id', 'name',
            'display_name', 'full_name', 'geometry_type',
            'is_monitored', 'monitoring_enabled', 'feature_count',
            'last_check', 'last_successful_check', 'created', 'modified'
        ]
        read_only_fields = [
            'id', 'feature_count', 'last_check', 'last_successful_check',
            'created', 'modified'
        ]


class SpatialLayerDetailSerializer(GeoFeatureModelSerializer):
    """Detailed serializer for spatial layer with geometry"""
    
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_status = serializers.CharField(source='service.status', read_only=True)
    fields = LayerFieldSerializer(source='layer_fields', many=True, read_only=True)
    full_name = serializers.ReadOnlyField()
    should_be_monitored = serializers.ReadOnlyField()
    change_percentage = serializers.ReadOnlyField()
    has_significant_change = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()
    snapshot_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SpatialLayer
        geo_field = 'extent'
        fields = [
            'id', 'service', 'service_name', 'service_status',
            'layer_id', 'name', 'display_name', 'description',
            'full_name', 'geometry_type', 'min_scale', 'max_scale',
            'extent', 'spatial_reference', 'supports_query',
            'supports_statistics', 'can_modify_layer', 'fields',
            'is_monitored', 'monitoring_enabled', 'change_detection_enabled',
            'change_detection_fields', 'change_threshold',
            'feature_count', 'last_feature_count', 'last_updated',
            'last_check', 'last_successful_check', 'check_failures',
            'alert_on_change', 'alert_on_error', 'alert_thresholds',
            'should_be_monitored', 'change_percentage', 'has_significant_change',
            'created_by', 'created_by_name', 'snapshot_count',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'feature_count', 'last_feature_count', 'last_updated',
            'last_check', 'last_successful_check', 'check_failures',
            'created', 'modified'
        ]
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def get_snapshot_count(self, obj):
        return obj.snapshots.count()


class SpatialLayerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating spatial layers"""
    
    class Meta:
        model = SpatialLayer
        fields = [
            'service', 'layer_id', 'name', 'display_name', 'description',
            'geometry_type', 'is_monitored', 'monitoring_enabled',
            'change_detection_enabled', 'change_detection_fields',
            'change_threshold', 'alert_on_change', 'alert_on_error',
            'alert_thresholds'
        ]
    
    def validate(self, attrs):
        # Check if layer with same service and layer_id already exists
        service = attrs.get('service')
        layer_id = attrs.get('layer_id')
        
        if self.instance:
            # Updating existing layer
            existing = SpatialLayer.objects.filter(
                service=service,
                layer_id=layer_id,
                is_removed=False
            ).exclude(id=self.instance.id)
        else:
            # Creating new layer
            existing = SpatialLayer.objects.filter(
                service=service,
                layer_id=layer_id,
                is_removed=False
            )
        
        if existing.exists():
            raise serializers.ValidationError({
                'layer_id': _('Layer with this ID already exists for this service')
            })
        
        return attrs
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ServiceEndpointSerializer(serializers.ModelSerializer):
    """Serializer for Service Endpoints"""
    
    full_url = serializers.ReadOnlyField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    
    class Meta:
        model = ServiceEndpoint
        fields = [
            'id', 'service', 'service_name', 'name', 'path',
            'method', 'parameters', 'is_monitored', 'timeout_seconds',
            'last_response_time', 'last_status_code', 'last_check',
            'full_url', 'created', 'modified'
        ]
        read_only_fields = [
            'id', 'last_response_time', 'last_status_code',
            'last_check', 'created', 'modified'
        ]


class ServiceMetricsSerializer(serializers.ModelSerializer):
    """Serializer for Service Metrics"""
    
    service_name = serializers.CharField(source='service.name', read_only=True)
    
    class Meta:
        model = ServiceMetrics
        fields = [
            'id', 'service', 'service_name', 'response_time_ms',
            'status_code', 'success', 'endpoint', 'method',
            'request_size_bytes', 'response_size_bytes',
            'error_message', 'error_type', 'created'
        ]
        read_only_fields = fields


class ServiceHealthSerializer(serializers.Serializer):
    """Serializer for service health status"""
    
    service_id = serializers.UUIDField()
    service_name = serializers.CharField()
    status = serializers.CharField()
    is_online = serializers.BooleanField()
    last_check = serializers.DateTimeField()
    last_successful_check = serializers.DateTimeField(allow_null=True)
    consecutive_failures = serializers.IntegerField()
    average_response_time = serializers.FloatField()
    success_rate = serializers.FloatField()
    monitored_layers = serializers.IntegerField()


class TestConnectionSerializer(serializers.Serializer):
    """Serializer for testing service connection"""
    
    base_url = serializers.URLField(required=True)
    requires_authentication = serializers.BooleanField(default=False)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, style={'input_type': 'password'})
    timeout_seconds = serializers.IntegerField(default=30, min_value=1, max_value=300)


class SyncLayersSerializer(serializers.Serializer):
    """Serializer for syncing layers from service"""
    
    auto_monitor = serializers.BooleanField(default=False)
    layer_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='Specific layer IDs to sync. If empty, sync all layers.'
    )