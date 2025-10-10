"""
SMGI Backend - Monitoring Serializers
Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.utils.translation import gettext_lazy as _

from apps.monitoring.models import (
    LayerSnapshot, ChangeDetectionResult, MonitoringJob,
    MonitoringJobExecution, DataQualityRule, DataQualityResult,
    SystemHealthMetric
)
from apps.gis_services.serializers import SpatialLayerListSerializer


class LayerSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for Layer Snapshots"""
    
    layer_name = serializers.CharField(source='layer.name', read_only=True)
    compression_ratio = serializers.ReadOnlyField()
    
    class Meta:
        model = LayerSnapshot
        fields = [
            'id', 'layer', 'layer_name', 'snapshot_hash',
            'feature_count', 'total_area', 'total_length',
            'extent_bounds', 'centroid', 'attribute_stats',
            'unique_values', 'null_count', 'invalid_geometries',
            'duplicate_records', 'data_checksum', 'schema_version',
            'collection_duration_ms', 'data_size_bytes',
            'compressed_size_bytes', 'compression_ratio',
            'is_valid', 'validation_errors', 'created'
        ]
        read_only_fields = fields


class ChangeDetectionResultListSerializer(serializers.ModelSerializer):
    """Simplified serializer for change detection results listing"""
    
    layer_name = serializers.CharField(source='current_snapshot.layer.name', read_only=True)
    service_name = serializers.CharField(source='current_snapshot.layer.service.name', read_only=True)
    change_severity = serializers.ReadOnlyField()
    
    class Meta:
        model = ChangeDetectionResult
        fields = [
            'id', 'layer_name', 'service_name', 'algorithm_used',
            'has_changes', 'change_types', 'feature_count_change',
            'feature_count_change_percent', 'confidence_score',
            'exceeds_threshold', 'change_severity', 'created'
        ]
        read_only_fields = fields


class ChangeDetectionResultDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for change detection results"""
    
    layer_name = serializers.CharField(source='current_snapshot.layer.name', read_only=True)
    service_name = serializers.CharField(source='current_snapshot.layer.service.name', read_only=True)
    layer = serializers.ReadOnlyField(source='current_snapshot.layer.id')
    change_severity = serializers.ReadOnlyField()
    total_features_affected = serializers.ReadOnlyField()
    change_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = ChangeDetectionResult
        fields = [
            'id', 'current_snapshot', 'previous_snapshot', 'layer',
            'layer_name', 'service_name', 'algorithm_used',
            'detection_duration_ms', 'confidence_score', 'has_changes',
            'change_types', 'feature_count_change', 'feature_count_change_percent',
            'area_change', 'area_change_percent', 'centroid_displacement',
            'modified_features', 'new_features', 'deleted_features',
            'total_features_affected', 'data_quality_score',
            'data_quality_change', 'change_details', 'affected_features',
            'statistical_significance', 'anomaly_score', 'exceeds_threshold',
            'threshold_values', 'change_severity', 'change_summary',
            'processing_status', 'error_message', 'created'
        ]
        read_only_fields = fields
    
    def get_change_summary(self, obj):
        return obj.get_change_summary()


class MonitoringJobListSerializer(serializers.ModelSerializer):
    """Simplified serializer for monitoring jobs listing"""
    
    total_layers = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MonitoringJob
        fields = [
            'id', 'name', 'schedule_expression', 'is_active',
            'status', 'total_layers', 'last_run', 'next_run',
            'is_overdue', 'consecutive_failures', 'created_by_name',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'last_run', 'next_run', 'consecutive_failures',
            'created', 'modified'
        ]
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class MonitoringJobDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for monitoring jobs"""
    
    layers = SpatialLayerListSerializer(many=True, read_only=True)
    layer_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=None,
        source='layers',
        required=False
    )
    total_layers = serializers.ReadOnlyField()
    total_services = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()
    recent_executions = serializers.SerializerMethodField()
    
    class Meta:
        model = MonitoringJob
        fields = [
            'id', 'name', 'description', 'layers', 'layer_ids', 'services',
            'schedule_expression', 'is_active', 'max_runtime_minutes',
            'detection_algorithm', 'change_threshold', 'alert_on_changes',
            'alert_on_errors', 'alert_threshold', 'last_run',
            'last_successful_run', 'next_run', 'consecutive_failures',
            'status', 'total_layers', 'total_services', 'is_overdue',
            'created_by', 'created_by_name', 'recent_executions',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'last_run', 'last_successful_run', 'next_run',
            'consecutive_failures', 'status', 'created', 'modified'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset for layer_ids dynamically to avoid circular import
        from apps.gis_services.models import SpatialLayer
        self.fields['layer_ids'].child_relation.queryset = SpatialLayer.objects.filter(is_removed=False)
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def get_recent_executions(self, obj):
        executions = obj.executions.all()[:5]
        return MonitoringJobExecutionSerializer(executions, many=True).data


class MonitoringJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating monitoring jobs"""
    
    layer_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=None,
        source='layers',
        required=False
    )
    
    class Meta:
        model = MonitoringJob
        fields = [
            'name', 'description', 'layer_ids', 'services',
            'schedule_expression', 'is_active', 'max_runtime_minutes',
            'detection_algorithm', 'change_threshold', 'alert_on_changes',
            'alert_on_errors', 'alert_threshold'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gis_services.models import SpatialLayer
        self.fields['layer_ids'].child_relation.queryset = SpatialLayer.objects.filter(is_removed=False)
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        layers = validated_data.pop('layers', [])
        services = validated_data.pop('services', [])
        
        job = MonitoringJob.objects.create(**validated_data)
        
        if layers:
            job.layers.set(layers)
        if services:
            job.services.set(services)
        
        # Calculate first next_run
        job.update_next_run()
        
        return job


class MonitoringJobExecutionSerializer(serializers.ModelSerializer):
    """Serializer for monitoring job executions"""
    
    job_name = serializers.CharField(source='job.name', read_only=True)
    
    class Meta:
        model = MonitoringJobExecution
        fields = [
            'id', 'job', 'job_name', 'started_at', 'completed_at',
            'duration_seconds', 'success', 'error_message',
            'layers_processed', 'snapshots_created', 'changes_detected',
            'alerts_created', 'memory_usage_mb', 'cpu_usage_percent',
            'execution_log', 'performance_metrics'
        ]
        read_only_fields = fields


class DataQualityRuleSerializer(serializers.ModelSerializer):
    """Serializer for data quality rules"""
    
    layer_name = serializers.CharField(source='layer.name', read_only=True, allow_null=True)
    service_name = serializers.CharField(source='service.name', read_only=True, allow_null=True)
    needs_check = serializers.ReadOnlyField()
    current_status = serializers.ReadOnlyField()
    
    class Meta:
        model = DataQualityRule
        fields = [
            'id', 'name', 'description', 'layer', 'layer_name',
            'service', 'service_name', 'rule_type', 'rule_expression',
            'warning_threshold', 'error_threshold', 'is_active',
            'check_frequency_hours', 'last_check', 'last_score',
            'needs_check', 'current_status', 'created', 'modified'
        ]
        read_only_fields = [
            'id', 'last_check', 'last_score', 'created', 'modified'
        ]


class DataQualityResultSerializer(serializers.ModelSerializer):
    """Serializer for data quality results"""
    
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    quality_grade = serializers.ReadOnlyField()
    issue_count = serializers.ReadOnlyField()
    
    class Meta:
        model = DataQualityResult
        fields = [
            'id', 'rule', 'rule_name', 'quality_score', 'quality_grade',
            'passed', 'total_records', 'valid_records', 'invalid_records',
            'completeness_score', 'accuracy_score', 'consistency_score',
            'validity_score', 'uniqueness_score', 'timeliness_score',
            'issues_found', 'issue_count', 'recommendations',
            'assessment_duration_ms', 'created'
        ]
        read_only_fields = fields


class SystemHealthMetricSerializer(serializers.ModelSerializer):
    """Serializer for system health metrics"""
    
    class Meta:
        model = SystemHealthMetric
        fields = [
            'id', 'cpu_usage_percent', 'memory_usage_percent',
            'disk_usage_percent', 'db_connections_active',
            'db_connections_idle', 'db_query_avg_time_ms',
            'redis_memory_usage_mb', 'redis_connected_clients',
            'redis_operations_per_sec', 'celery_active_tasks',
            'celery_pending_tasks', 'celery_failed_tasks',
            'active_users', 'api_requests_per_minute',
            'api_error_rate_percent', 'overall_health', 'created'
        ]
        read_only_fields = fields


class MonitoringStatisticsSerializer(serializers.Serializer):
    """Serializer for monitoring statistics"""
    
    total_snapshots = serializers.IntegerField()
    total_changes_detected = serializers.IntegerField()
    active_monitoring_jobs = serializers.IntegerField()
    monitored_layers = serializers.IntegerField()
    recent_changes = serializers.IntegerField()
    average_detection_time_ms = serializers.FloatField()
    change_detection_accuracy = serializers.FloatField()


class TriggerMonitoringSerializer(serializers.Serializer):
    """Serializer for triggering monitoring"""
    
    layer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text='Specific layer IDs to monitor. If empty, monitor all active layers.'
    )
    force = serializers.BooleanField(
        default=False,
        help_text='Force monitoring even if layers were recently checked'
    )