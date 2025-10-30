# apps/reports/serializers.py
"""
SMGI Backend - Reports Serializers
Sistema de Monitoreo Geoespacial Inteligente
Serializadores para el sistema de generación de informes
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.utils.translation import gettext_lazy as _
from apps.reports.models import (
    Report, ReportTemplate, GeneratedReport, ReportSchedule, ReportExecution,
    NotificationPreference, ReportType, ReportFormat, ReportStatus,
    ReportParameter, ReportSection
)
# Importar modelos relacionados
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert


class ReportListSerializer(serializers.ModelSerializer):
    """Simplified serializer for report listing"""
    
    service_name = serializers.CharField(source='service.name', read_only=True, allow_null=True)
    layer_name = serializers.CharField(source='layer.name', read_only=True, allow_null=True)
    created_by_name = serializers.SerializerMethodField()
    last_generated = serializers.ReadOnlyField()
    generation_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'format_type',
            'service', 'service_name', 'layer', 'layer_name',
            'is_scheduled', 'schedule_expression',
            'notify_on_completion', 'created_by', 'created_by_name',
            'last_generated', 'generation_count', 'created', 'modified'
        ]
        read_only_fields = fields
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class ReportDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for reports"""
    
    service_name = serializers.CharField(source='service.name', read_only=True, allow_null=True)
    layer_name = serializers.CharField(source='layer.name', read_only=True, allow_null=True)
    monitoring_job_name = serializers.CharField(source='monitoring_job.name', read_only=True, allow_null=True)
    alert_title = serializers.CharField(source='alert.title', read_only=True, allow_null=True)
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    created_by_name = serializers.SerializerMethodField()
    last_generated = serializers.ReadOnlyField()
    generation_count = serializers.ReadOnlyField()
    notify_users_emails = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'format_type',
            'service', 'service_name', 'layer', 'layer_name',
            'monitoring_job', 'monitoring_job_name', 'alert', 'alert_title',
            'template', 'template_name', 'parameters',
            'is_scheduled', 'schedule_expression',
            'notify_on_completion', 'notify_users', 'notify_users_emails',
            'created_by', 'created_by_name',
            'last_generated', 'generation_count', 'created', 'modified'
        ]
        read_only_fields = [
            'id', 'created_by', 'last_generated', 'generation_count',
            'created', 'modified'
        ]
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def get_notify_users_emails(self, obj):
        return [user.email for user in obj.notify_users.all()]


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating reports"""
    
    notify_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text=_('List of user IDs to notify on completion')
    )
    
    class Meta:
        model = Report
        fields = [
            'name', 'description', 'report_type', 'format_type',
            'service', 'layer', 'monitoring_job', 'alert',
            'template', 'parameters',
            'is_scheduled', 'schedule_expression',
            'notify_on_completion', 'notify_user_ids'
        ]
    
    def create(self, validated_data):
        notify_user_ids = validated_data.pop('notify_user_ids', [])
        report = Report.objects.create(
            created_by=self.context['request'].user,
            **validated_data
        )
        
        if notify_user_ids:
            users = User.objects.filter(id__in=notify_user_ids)
            report.notify_users.set(users)
        
        return report
    
    def update(self, instance, validated_data):
        notify_user_ids = validated_data.pop('notify_user_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if notify_user_ids is not None:
            users = User.objects.filter(id__in=notify_user_ids)
            instance.notify_users.set(users)
        
        return instance


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for report templates"""
    
    author_name = serializers.SerializerMethodField()
    default_parameters = serializers.JSONField(required=False)
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'template_type', 'format_type',
            'template_file', 'template_content', 'is_active',
            'default_parameters', 'version', 'author', 'author_name',
            'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified']
    
    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author else None


class GeneratedReportSerializer(serializers.ModelSerializer):
    """Serializer for generated reports"""
    
    report_name = serializers.CharField(source='report.name', read_only=True)
    generated_by_name = serializers.SerializerMethodField()
    file_name = serializers.ReadOnlyField()
    file_url = serializers.ReadOnlyField()
    is_complete = serializers.ReadOnlyField()
    is_failed = serializers.ReadOnlyField()
    generation_duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedReport
        fields = [
            'id', 'report', 'report_name', 'generated_by', 'generated_by_name',
            'report_id', 'file', 'file_name', 'file_url', 'file_size_bytes',
            'file_checksum', 'format_type', 'status', 'parameters_used',
            'generation_duration_ms', 'generation_duration_seconds',
            'started_at', 'completed_at', 'record_count', 'page_count',
            'error_message', 'notification_sent', 'is_complete', 'is_failed',
            'created', 'modified'
        ]
        read_only_fields = fields
    
    def get_generated_by_name(self, obj):
        return obj.generated_by.get_full_name() if obj.generated_by else None
    
    def get_generation_duration_seconds(self, obj):
        return obj.generation_duration_ms / 1000 if obj.generation_duration_ms else 0


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for report schedules"""
    
    report_name = serializers.CharField(source='report.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    next_run = serializers.ReadOnlyField()
    last_run = serializers.ReadOnlyField()
    last_successful_run = serializers.ReadOnlyField()
    consecutive_failures = serializers.ReadOnlyField()
    notify_users_emails = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'report', 'report_name', 'name', 'description',
            'schedule_expression', 'is_active', 'run_on_weekends',
            'run_on_holidays', 'max_runtime_minutes',
            'notify_on_completion', 'notify_on_failure', 'notify_users',
            'notify_users_emails', 'created_by', 'created_by_name',
            'last_run', 'last_successful_run', 'next_run', 'consecutive_failures',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'created_by', 'last_run', 'last_successful_run',
            'next_run', 'consecutive_failures', 'created', 'modified'
        ]
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def get_notify_users_emails(self, obj):
        return [user.email for user in obj.notify_users.all()]


class ReportExecutionSerializer(serializers.ModelSerializer):
    """Serializer for report executions"""
    
    schedule_name = serializers.CharField(source='schedule.name', read_only=True)
    report_name = serializers.CharField(source='schedule.report.name', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportExecution
        fields = [
            'id', 'schedule', 'schedule_name', 'report_name',
            'started_at', 'completed_at', 'duration_seconds',
            'success', 'error_message', 'reports_generated',
            'memory_usage_mb', 'cpu_usage_percent',
            'execution_log', 'performance_metrics', 'created', 'modified'
        ]
        read_only_fields = fields
    
    def get_duration_seconds(self, obj):
        return obj.duration_seconds or (obj.completed_at - obj.started_at).total_seconds() if obj.completed_at and obj.started_at else 0


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'user_email', 'email_enabled', 'sms_enabled',
            'push_enabled', 'in_app_enabled', 'email_alert_notifications',
            'email_report_notifications', 'email_system_notifications',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'digest_enabled', 'digest_frequency', 'min_alert_severity',
            'created', 'modified'
        ]
        read_only_fields = ['id', 'created', 'modified']


# --- Serializers for Custom Actions ---

class TriggerReportSerializer(serializers.Serializer):
    """Serializer for triggering report generation"""
    
    report_id = serializers.UUIDField(required=False, help_text=_('ID of the report to generate. If not provided, generates all active reports.'))
    parameters = serializers.JSONField(required=False, help_text=_('Parameters for report generation.'))
    force = serializers.BooleanField(default=False, help_text=_('Force generation even if recently generated.'))


class DownloadGeneratedReportSerializer(serializers.Serializer):
    """Serializer for downloading generated reports"""
    
    generated_report_id = serializers.UUIDField(required=False, help_text=_('ID of the specific generated report to download. If not provided, downloads the latest.'))


class RegenerateReportSerializer(serializers.Serializer):
    """Serializer for regenerating reports"""
    
    force = serializers.BooleanField(default=True, help_text=_('Force regeneration.'))


class ReportScheduleToggleSerializer(serializers.Serializer):
    """Serializer for toggling report schedule active status"""
    
    is_active = serializers.BooleanField(required=False, help_text=_('Set schedule to active (True) or inactive (False). If not provided, toggles current status.'))


class RunReportNowSerializer(serializers.Serializer):
    """Serializer for running reports immediately"""
    
    parameters = serializers.JSONField(required=False, help_text=_('Parameters for immediate report generation.'))


class ReportStatisticsSerializer(serializers.Serializer):
    """Serializer for report statistics"""
    
    total_reports = serializers.IntegerField()
    active_schedules = serializers.IntegerField()
    generated_today = serializers.IntegerField()
    average_generation_time_ms = serializers.FloatField()
    reports_by_type = serializers.DictField(child=serializers.IntegerField())
    reports_by_format = serializers.DictField(child=serializers.IntegerField())
    top_services_with_reports = serializers.ListField(child=serializers.DictField())
