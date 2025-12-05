"""
Serializers for Monitoring app.
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework_gis.fields import GeometryField
from .models import (
    MonitoringProject,
    Monitor,
    Detection,
    ChangeRecord,
    MonitoringReport,
    Baseline
)


class MonitoringProjectSerializer(serializers.ModelSerializer):
    """Serializer for MonitoringProject model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    monitor_count = serializers.SerializerMethodField()
    detection_count = serializers.SerializerMethodField()
    area_of_interest = GeometryField(allow_null=True, required=False)
    
    class Meta:
        model = MonitoringProject
        fields = [
            'id',
            'name',
            'description',
            'status',
            'area_of_interest',
            'configuration',
            'tags',
            'metadata',
            'start_date',
            'end_date',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
            'monitor_count',
            'detection_count',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_monitor_count(self, obj) -> int:
        """Get number of monitors in this project."""
        return obj.monitors.filter(is_active=True).count()
    
    def get_detection_count(self, obj) -> int:
        """Get number of detections in this project."""
        return Detection.objects.filter(
            monitor__project=obj,
            is_active=True
        ).count()


class MonitorSerializer(serializers.ModelSerializer):
    """Serializer for Monitor model."""
    project_name = serializers.CharField(source='project.name', read_only=True)
    agent_name = serializers.CharField(source='agent.name', read_only=True, allow_null=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    detection_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Monitor
        fields = [
            'id',
            'project',
            'project_name',
            'name',
            'description',
            'monitor_type',
            'status',
            'layers',
            'data_sources',
            'agent',
            'agent_name',
            'parameters',
            'check_interval',
            'last_check',
            'next_check',
            'check_count',
            'detection_count',
            'tags',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_check', 'next_check', 'check_count', 'created_at', 'updated_at']
    
    def get_detection_count(self, obj) -> int:
        """Get number of detections for this monitor."""
        return obj.detections.filter(is_active=True).count()


class ChangeRecordSerializer(serializers.ModelSerializer):
    """Serializer for ChangeRecord model."""
    layer_name = serializers.CharField(source='layer.name', read_only=True)
    before_geometry = GeometryField(read_only=True, allow_null=True)
    after_geometry = GeometryField(read_only=True, allow_null=True)
    
    class Meta:
        model = ChangeRecord
        fields = [
            'id',
            'detection',
            'change_type',
            'feature_id',
            'layer',
            'layer_name',
            'before_geometry',
            'after_geometry',
            'before_attributes',
            'after_attributes',
            'change_magnitude',
            'metadata',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class DetectionSerializer(serializers.ModelSerializer):
    """Serializer for Detection model with geometry support."""
    monitor_name = serializers.CharField(source='monitor.name', read_only=True)
    project_name = serializers.CharField(source='monitor.project.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, allow_null=True)
    change_count = serializers.SerializerMethodField()
    affected_area = GeometryField(read_only=True, allow_null=True)
    
    class Meta:
        model = Detection
        fields = [
            'id',
            'monitor',
            'monitor_name',
            'project_name',
            'title',
            'description',
            'severity',
            'status',
            'detected_at',
            'affected_area',
            'analysis_data',
            'confidence_score',
            'related_layers',
            'evidence',
            'reviewed_by',
            'reviewed_by_username',
            'reviewed_at',
            'review_notes',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
            'change_count',
        ]
        read_only_fields = ['id', 'detected_at', 'created_at']
    
    def get_change_count(self, obj) -> int:
        """Get number of change records for this detection."""
        return obj.changes.count()


class DetectionDetailSerializer(DetectionSerializer):
    """Detailed serializer for Detection with change records."""
    changes = ChangeRecordSerializer(many=True, read_only=True)
    
    class Meta(DetectionSerializer.Meta):
        fields = DetectionSerializer.Meta.fields + ['changes']


class MonitoringReportSerializer(serializers.ModelSerializer):
    """Serializer for MonitoringReport model."""
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = MonitoringReport
        fields = [
            'id',
            'project',
            'project_name',
            'title',
            'report_type',
            'start_date',
            'end_date',
            'summary',
            'statistics',
            'detections_summary',
            'report_file',
            'generated_at',
            'created_by',
            'created_by_username',
        ]
        read_only_fields = ['id', 'generated_at']


class BaselineSerializer(serializers.ModelSerializer):
    """Serializer for Baseline model."""
    monitor_name = serializers.CharField(source='monitor.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Baseline
        fields = [
            'id',
            'monitor',
            'monitor_name',
            'name',
            'description',
            'baseline_date',
            'baseline_data',
            'feature_count',
            'area_coverage',
            'is_current',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MonitoringStatisticsSerializer(serializers.Serializer):
    """Serializer for monitoring statistics."""
    total_projects = serializers.IntegerField()
    active_monitors = serializers.IntegerField()
    total_detections = serializers.IntegerField()
    detections_by_severity = serializers.DictField()
    detections_by_status = serializers.DictField()
    recent_detections = serializers.ListField()
    top_monitors = serializers.ListField()
