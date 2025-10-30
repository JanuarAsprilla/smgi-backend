# apps/audit/serializers.py
"""
SMGI Backend - Audit Serializers
Sistema de Monitoreo Geoespacial Inteligente
Serializadores para el sistema de auditoría
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from apps.audit.models import (
    AuditLog, AuditTrail, AuditPolicy, AuditConfiguration,
    AuditEventType, AuditEventSeverity, AuditEventStatus, DataClassification
)
# Importar modelos relacionados
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert
from apps.reports.models import Report
from apps.notifications.models import Notification, EmailNotification, WebhookNotification

User = get_user_model()


class AuditLogListSerializer(serializers.ModelSerializer):
    """Simplified serializer for audit log listing"""
    
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    alert_title = serializers.CharField(source='alert.title', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'event_id', 'title', 'user', 'user_email', 'alert', 'alert_title',
            'event_type', 'severity', 'status', 'is_read', 'read_at',
            'resource_type', 'resource_id', 'action', 'description',
            'timestamp', 'duration_ms', 'success', 'error_message',
            'created'
        ]
        read_only_fields = fields


class AuditLogDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for audit logs"""
    
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    alert_title = serializers.CharField(source='alert.title', read_only=True, allow_null=True)
    parent_event_title = serializers.CharField(source='parent_event.title', read_only=True, allow_null=True)
    archived_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'event_id', 'title', 'message', 'short_message',
            'event_type', 'severity', 'status', 'is_read', 'read_at',
            'user', 'user_email', 'ip_address', 'user_agent',
            'resource_type', 'resource_id', 'action', 'description',
            'details', 'timestamp', 'duration_ms', 'success', 'error_message',
            'metadata', 'tags', 'related_events', 'parent_event', 'parent_event_title',
            'external_reference_id', 'external_system',
            'is_archived', 'archived_at', 'archived_by', 'archived_by_name',
            'retention_policy', 'data_classification',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'event_id', 'created', 'modified', 'read_at', 'alert_link',
            'archived_at', 'archived_by_name'
        ]
    
    def get_archived_by_name(self, obj):
        return obj.archived_by.get_full_name() if obj.archived_by else None


class AuditLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating audit logs"""
    
    class Meta:
        model = AuditLog
        fields = [
            'title', 'message', 'short_message',
            'event_type', 'severity', 'status', 'is_read',
            'user', 'user_email', 'ip_address', 'user_agent',
            'resource_type', 'resource_id', 'action', 'description',
            'details', 'timestamp', 'duration_ms', 'success', 'error_message',
            'metadata', 'tags', 'related_events', 'parent_event',
            'external_reference_id', 'external_system',
            'is_archived', 'archived_at', 'archived_by',
            'retention_policy', 'data_classification'
        ]


class AuditLogUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating audit logs"""
    
    class Meta:
        model = AuditLog
        fields = [
            'title', 'message', 'short_message',
            'event_type', 'severity', 'status', 'is_read',
            'user', 'user_email', 'ip_address', 'user_agent',
            'resource_type', 'resource_id', 'action', 'description',
            'details', 'timestamp', 'duration_ms', 'success', 'error_message',
            'metadata', 'tags', 'related_events', 'parent_event',
            'external_reference_id', 'external_system',
            'is_archived', 'archived_at', 'archived_by',
            'retention_policy', 'data_classification'
        ]


class AuditTrailListSerializer(serializers.ModelSerializer):
    """Simplified serializer for audit trail listing"""
    
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    model_name_display = serializers.ReadOnlyField()
    
    class Meta:
        model = AuditTrail
        fields = [
            'id', 'model_name', 'model_name_display', 'object_id', 'field_name',
            'change_type', 'user', 'user_email', 'timestamp',
            'ip_address', 'user_agent', 'session_key', 'request_id', 'correlation_id',
            'is_archived', 'archived_at', 'archived_by',
            'retention_policy', 'data_classification',
            'created'
        ]
        read_only_fields = fields


class AuditTrailDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for audit trails"""
    
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    archived_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditTrail
        fields = [
            'id', 'model_name', 'object_id', 'field_name',
            'old_value', 'new_value', 'change_type',
            'user', 'user_email', 'timestamp',
            'ip_address', 'user_agent', 'session_key', 'request_id', 'correlation_id',
            'is_archived', 'archived_at', 'archived_by', 'archived_by_name',
            'retention_policy', 'data_classification',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'created', 'modified',
            'archived_at', 'archived_by_name'
        ]
    
    def get_archived_by_name(self, obj):
        return obj.archived_by.get_full_name() if obj.archived_by else None


class AuditTrailCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating audit trails"""
    
    class Meta:
        model = AuditTrail
        fields = [
            'model_name', 'object_id', 'field_name',
            'old_value', 'new_value', 'change_type',
            'user', 'user_email', 'timestamp',
            'ip_address', 'user_agent', 'session_key', 'request_id', 'correlation_id',
            'is_archived', 'archived_at', 'archived_by',
            'retention_policy', 'data_classification'
        ]


class AuditTrailUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating audit trails"""
    
    class Meta:
        model = AuditTrail
        fields = [
            'model_name', 'object_id', 'field_name',
            'old_value', 'new_value', 'change_type',
            'user', 'user_email', 'timestamp',
            'ip_address', 'user_agent', 'session_key', 'request_id', 'correlation_id',
            'is_archived', 'archived_at', 'archived_by',
            'retention_policy', 'data_classification'
        ]


class AuditPolicyListSerializer(serializers.ModelSerializer):
    """Simplified serializer for audit policy listing"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    modified_by_name = serializers.CharField(source='modified_by.get_full_name', read_only=True, allow_null=True)
    resource_count = serializers.ReadOnlyField()
    user_count = serializers.ReadOnlyField()
    ip_address_count = serializers.ReadOnlyField()
    user_agent_count = serializers.ReadOnlyField()
    
    class Meta:
        model = AuditPolicy
        fields = [
            'id', 'name', 'description', 'is_active',
            'resource_types', 'event_types', 'severity_levels', 'actions',
            'users', 'ip_addresses', 'user_agents',
            'retention_days', 'archive_after_days',
            'notify_on_events', 'notification_channels', 'notification_recipients',
            'created_by', 'created_by_name', 'modified_by', 'modified_by_name',
            'resource_count', 'user_count', 'ip_address_count', 'user_agent_count',
            'created', 'modified'
        ]
        read_only_fields = fields


class AuditPolicyDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for audit policies"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    modified_by_name = serializers.CharField(source='modified_by.get_full_name', read_only=True, allow_null=True)
    resource_count = serializers.ReadOnlyField()
    user_count = serializers.ReadOnlyField()
    ip_address_count = serializers.ReadOnlyField()
    user_agent_count = serializers.ReadOnlyField()
    notification_recipient_emails = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditPolicy
        fields = [
            'id', 'name', 'description', 'is_active',
            'resource_types', 'event_types', 'severity_levels', 'actions',
            'users', 'ip_addresses', 'user_agents',
            'retention_days', 'archive_after_days',
            'notify_on_events', 'notification_channels', 'notification_recipients',
            'notification_recipient_emails',
            'created_by', 'created_by_name', 'modified_by', 'modified_by_name',
            'resource_count', 'user_count', 'ip_address_count', 'user_agent_count',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'created', 'modified',
            'resource_count', 'user_count', 'ip_address_count', 'user_agent_count',
            'created_by_name', 'modified_by_name', 'notification_recipient_emails'
        ]
    
    def get_notification_recipient_emails(self, obj):
        return [user.email for user in obj.notification_recipients.all()]


class AuditPolicyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating audit policies"""
    
    notification_recipient_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text=_('List of user IDs to receive notifications for this policy')
    )
    
    class Meta:
        model = AuditPolicy
        fields = [
            'name', 'description', 'is_active',
            'resource_types', 'event_types', 'severity_levels', 'actions',
            'users', 'ip_addresses', 'user_agents',
            'retention_days', 'archive_after_days',
            'notify_on_events', 'notification_channels', 'notification_recipients',
            'notification_recipient_ids',
            'created_by', 'modified_by'
        ]
    
    def create(self, validated_data):
        notification_recipient_ids = validated_data.pop('notification_recipient_ids', [])
        policy = AuditPolicy.objects.create(**validated_data)
        
        if notification_recipient_ids:
            users = User.objects.filter(id__in=notification_recipient_ids)
            policy.notification_recipients.set(users)
        
        return policy


class AuditPolicyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating audit policies"""
    
    notification_recipient_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text=_('List of user IDs to receive notifications for this policy')
    )
    
    class Meta:
        model = AuditPolicy
        fields = [
            'name', 'description', 'is_active',
            'resource_types', 'event_types', 'severity_levels', 'actions',
            'users', 'ip_addresses', 'user_agents',
            'retention_days', 'archive_after_days',
            'notify_on_events', 'notification_channels', 'notification_recipients',
            'notification_recipient_ids',
            'created_by', 'modified_by'
        ]
    
    def update(self, instance, validated_data):
        notification_recipient_ids = validated_data.pop('notification_recipient_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if notification_recipient_ids is not None:
            users = User.objects.filter(id__in=notification_recipient_ids)
            instance.notification_recipients.set(users)
        
        return instance


class AuditConfigurationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for audit configuration listing"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    modified_by_name = serializers.CharField(source='modified_by.get_full_name', read_only=True, allow_null=True)
    total_storage_options_enabled = serializers.ReadOnlyField()
    total_sensitive_fields_excluded = serializers.ReadOnlyField()
    
    class Meta:
        model = AuditConfiguration
        fields = [
            'id', 'name', 'description', 'is_active',
            'default_retention_days', 'default_archive_after_days', 'default_data_classification',
            'enable_real_time_logging', 'enable_batch_logging', 'batch_size',
            'log_level',
            'exclude_sensitive_fields', 'mask_sensitive_data', 'encrypt_audit_logs',
            'store_audit_trails', 'store_user_sessions', 'store_api_calls',
            'store_external_api_calls', 'store_internal_api_calls',
            'store_database_queries', 'store_cache_operations',
            'store_file_operations', 'store_email_sending',
            'store_sms_sending', 'store_webhook_sending',
            'store_push_notification_sending', 'store_report_generation',
            'store_alert_triggering', 'store_monitoring_job_scheduling',
            'store_system_health_checks', 'store_data_validation',
            'store_gis_service_interaction', 'store_authentication',
            'store_authorization', 'store_error_handling',
            'store_performance_monitoring',
            'created_by', 'created_by_name', 'modified_by', 'modified_by_name',
            'total_storage_options_enabled', 'total_sensitive_fields_excluded',
            'created', 'modified'
        ]
        read_only_fields = fields


class AuditConfigurationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for audit configurations"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    modified_by_name = serializers.CharField(source='modified_by.get_full_name', read_only=True, allow_null=True)
    total_storage_options_enabled = serializers.ReadOnlyField()
    total_sensitive_fields_excluded = serializers.ReadOnlyField()
    
    class Meta:
        model = AuditConfiguration
        fields = [
            'id', 'name', 'description', 'is_active',
            'default_retention_days', 'default_archive_after_days', 'default_data_classification',
            'enable_real_time_logging', 'enable_batch_logging', 'batch_size',
            'log_level',
            'exclude_sensitive_fields', 'mask_sensitive_data', 'encrypt_audit_logs',
            'store_audit_trails', 'store_user_sessions', 'store_api_calls',
            'store_external_api_calls', 'store_internal_api_calls',
            'store_database_queries', 'store_cache_operations',
            'store_file_operations', 'store_email_sending',
            'store_sms_sending', 'store_webhook_sending',
            'store_push_notification_sending', 'store_report_generation',
            'store_alert_triggering', 'store_monitoring_job_scheduling',
            'store_system_health_checks', 'store_data_validation',
            'store_gis_service_interaction', 'store_authentication',
            'store_authorization', 'store_error_handling',
            'store_performance_monitoring',
            'created_by', 'created_by_name', 'modified_by', 'modified_by_name',
            'total_storage_options_enabled', 'total_sensitive_fields_excluded',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'created', 'modified',
            'total_storage_options_enabled', 'total_sensitive_fields_excluded',
            'created_by_name', 'modified_by_name'
        ]


class AuditConfigurationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating audit configurations"""
    
    class Meta:
        model = AuditConfiguration
        fields = [
            'name', 'description', 'is_active',
            'default_retention_days', 'default_archive_after_days', 'default_data_classification',
            'enable_real_time_logging', 'enable_batch_logging', 'batch_size',
            'log_level',
            'exclude_sensitive_fields', 'mask_sensitive_data', 'encrypt_audit_logs',
            'store_audit_trails', 'store_user_sessions', 'store_api_calls',
            'store_external_api_calls', 'store_internal_api_calls',
            'store_database_queries', 'store_cache_operations',
            'store_file_operations', 'store_email_sending',
            'store_sms_sending', 'store_webhook_sending',
            'store_push_notification_sending', 'store_report_generation',
            'store_alert_triggering', 'store_monitoring_job_scheduling',
            'store_system_health_checks', 'store_data_validation',
            'store_gis_service_interaction', 'store_authentication',
            'store_authorization', 'store_error_handling',
            'store_performance_monitoring',
            'created_by', 'modified_by'
        ]


class AuditConfigurationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating audit configurations"""
    
    class Meta:
        model = AuditConfiguration
        fields = [
            'name', 'description', 'is_active',
            'default_retention_days', 'default_archive_after_days', 'default_data_classification',
            'enable_real_time_logging', 'enable_batch_logging', 'batch_size',
            'log_level',
            'exclude_sensitive_fields', 'mask_sensitive_data', 'encrypt_audit_logs',
            'store_audit_trails', 'store_user_sessions', 'store_api_calls',
            'store_external_api_calls', 'store_internal_api_calls',
            'store_database_queries', 'store_cache_operations',
            'store_file_operations', 'store_email_sending',
            'store_sms_sending', 'store_webhook_sending',
            'store_push_notification_sending', 'store_report_generation',
            'store_alert_triggering', 'store_monitoring_job_scheduling',
            'store_system_health_checks', 'store_data_validation',
            'store_gis_service_interaction', 'store_authentication',
            'store_authorization', 'store_error_handling',
            'store_performance_monitoring',
            'created_by', 'modified_by'
        ]


# --- Serializadores para Acciones Personalizadas ---

class MarkAsReadSerializer(serializers.Serializer):
    """Serializer for marking audit logs as read"""
    
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text=_('List of audit log IDs to mark as read')
    )


class MarkAsUnreadSerializer(serializers.Serializer):
    """Serializer for marking audit logs as unread"""
    
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text=_('List of audit log IDs to mark as unread')
    )


class ArchiveSerializer(serializers.Serializer):
    """Serializer for archiving audit logs"""
    
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text=_('List of audit log IDs to archive')
    )


class UnarchiveSerializer(serializers.Serializer):
    """Serializer for unarchiving audit logs"""
    
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text=_('List of audit log IDs to unarchive')
    )


class DeleteSerializer(serializers.Serializer):
    """Serializer for deleting audit logs"""
    
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text=_('List of audit log IDs to delete')
    )


class BulkActionSerializer(serializers.Serializer):
    """Serializer for bulk actions on audit logs"""
    
    action = serializers.ChoiceField(
        choices=[
            ('mark_read', _('Mark as Read')),
            ('mark_unread', _('Mark as Unread')),
            ('archive', _('Archive')),
            ('unarchive', _('Unarchive')),
            ('delete', _('Delete')),
        ],
        required=True,
        help_text=_('Action to perform on selected audit logs')
    )
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text=_('List of audit log IDs to perform action on')
    )


class StatisticsSerializer(serializers.Serializer):
    """Serializer for audit log statistics"""
    
    total_logs = serializers.IntegerField()
    unread_logs = serializers.IntegerField()
    logs_today = serializers.IntegerField()
    average_duration_ms = serializers.FloatField()
    logs_by_type = serializers.DictField()
    logs_by_severity = serializers.DictField()
    top_users_with_logs = serializers.ListField()
    top_services_with_logs = serializers.ListField()


class TrendSerializer(serializers.Serializer):
    """Serializer for audit log trends"""
    
    period_hours = serializers.IntegerField()
    daily_trend = serializers.ListField()
    weekly_trend = serializers.ListField()
    monthly_trend = serializers.ListField()


class FilterSerializer(serializers.Serializer):
    """Serializer for filtering audit logs"""
    
    event_type = serializers.ChoiceField(
        choices=AuditEventType.choices,
        required=False,
        help_text=_('Filter by event type')
    )
    severity = serializers.ChoiceField(
        choices=AuditEventSeverity.choices,
        required=False,
        help_text=_('Filter by severity')
    )
    status = serializers.ChoiceField(
        choices=AuditEventStatus.choices,
        required=False,
        help_text=_('Filter by status')
    )
    is_read = serializers.BooleanField(
        required=False,
        help_text=_('Filter by read status')
    )
    user_id = serializers.UUIDField(
        required=False,
        help_text=_('Filter by user ID')
    )
    resource_type = serializers.CharField(
        max_length=100,
        required=False,
        help_text=_('Filter by resource type')
    )
    resource_id = serializers.CharField(
        max_length=255,
        required=False,
        help_text=_('Filter by resource ID')
    )
    action = serializers.CharField(
        max_length=50,
        required=False,
        help_text=_('Filter by action')
    )
    days = serializers.IntegerField(
        required=False,
        help_text=_('Filter by days (past N days)')
    )


class SearchSerializer(serializers.Serializer):
    """Serializer for searching audit logs"""
    
    query = serializers.CharField(
        max_length=255,
        required=True,
        help_text=_('Search query (title, message, description, user email, resource name)')
    )


class SortSerializer(serializers.Serializer):
    """Serializer for sorting audit logs"""
    
    sort_by = serializers.ChoiceField(
        choices=[
            ('created', _('Created')),
            ('-created', _('Created (Descending)')),
            ('event_type', _('Event Type')),
            ('-event_type', _('Event Type (Descending)')),
            ('severity', _('Severity')),
            ('-severity', _('Severity (Descending)')),
            ('status', _('Status')),
            ('-status', _('Status (Descending)')),
            ('is_read', _('Read Status')),
            ('-is_read', _('Read Status (Descending)')),
            ('user_email', _('User Email')),
            ('-user_email', _('User Email (Descending)')),
            ('resource_type', _('Resource Type')),
            ('-resource_type', _('Resource Type (Descending)')),
            ('resource_id', _('Resource ID')),
            ('-resource_id', _('Resource ID (Descending)')),
            ('action', _('Action')),
            ('-action', _('Action (Descending)')),
            ('duration_ms', _('Duration (ms)')),
            ('-duration_ms', _('Duration (ms) (Descending)')),
            ('success', _('Success')),
            ('-success', _('Success (Descending)')),
        ],
        required=False,
        default='-created',
        help_text=_('Sort audit logs by field')
    )


class PaginationSerializer(serializers.Serializer):
    """Serializer for paginating audit logs"""
    
    page = serializers.IntegerField(
        required=False,
        default=1,
        help_text=_('Page number')
    )
    limit = serializers.IntegerField(
        required=False,
        default=20,
        help_text=_('Number of items per page')
    )


class ExportSerializer(serializers.Serializer):
    """Serializer for exporting audit logs"""
    
    format = serializers.ChoiceField(
        choices=[
            ('json', _('JSON')),
            ('csv', _('CSV')),
            ('xlsx', _('Excel')),
            ('pdf', _('PDF')),
        ],
        required=False,
        default='json',
        help_text=_('Export format')
    )
    include_details = serializers.BooleanField(
        required=False,
        default=True,
        help_text=_('Include detailed information in export')
    )
    filter_criteria = FilterSerializer(
        required=False,
        help_text=_('Filter criteria for export')
    )


class ImportSerializer(serializers.Serializer):
    """Serializer for importing audit logs"""
    
    file = serializers.FileField(
        required=True,
        help_text=_('File to import (JSON, CSV, XLSX)')
    )
    format = serializers.ChoiceField(
        choices=[
            ('json', _('JSON')),
            ('csv', _('CSV')),
            ('xlsx', _('Excel')),
        ],
        required=True,
        help_text=_('Import format')
    )
    overwrite_existing = serializers.BooleanField(
        required=False,
        default=False,
        help_text=_('Overwrite existing audit logs with same ID')
    )


class SyncSerializer(serializers.Serializer):
    """Serializer for synchronizing audit logs"""
    
    source = serializers.ChoiceField(
        choices=[
            ('database', _('Database')),
            ('file', _('File')),
            ('api', _('API')),
        ],
        required=True,
        help_text=_('Source to synchronize from')
    )
    destination = serializers.ChoiceField(
        choices=[
            ('database', _('Database')),
            ('file', _('File')),
            ('api', _('API')),
        ],
        required=True,
        help_text=_('Destination to synchronize to')
    )
    sync_type = serializers.ChoiceField(
        choices=[
            ('full', _('Full Sync')),
            ('incremental', _('Incremental Sync')),
            ('delta', _('Delta Sync')),
        ],
        required=False,
        default='incremental',
        help_text=_('Type of synchronization')
    )
    filter_criteria = FilterSerializer(
        required=False,
        help_text=_('Filter criteria for sync')
    )


class ValidateSerializer(serializers.Serializer):
    """Serializer for validating audit logs"""
    
    validation_rules = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        help_text=_('List of validation rules to apply')
    )
    fix_errors = serializers.BooleanField(
        required=False,
        default=False,
        help_text=_('Automatically fix validation errors if possible')
    )


class TransformSerializer(serializers.Serializer):
    """Serializer for transforming audit logs"""
    
    transformation_rules = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        help_text=_('List of transformation rules to apply')
    )
    output_format = serializers.ChoiceField(
        choices=[
            ('json', _('JSON')),
            ('csv', _('CSV')),
            ('xlsx', _('Excel')),
            ('pdf', _('PDF')),
        ],
        required=False,
        default='json',
        help_text=_('Output format after transformation')
    )


class AggregateSerializer(serializers.Serializer):
    """Serializer for aggregating audit logs"""
    
    aggregation_functions = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            ('count', _('Count')),
            ('sum', _('Sum')),
            ('avg', _('Average')),
            ('min', _('Minimum')),
            ('max', _('Maximum')),
            ('stddev', _('Standard Deviation')),
            ('variance', _('Variance')),
        ]),
        required=True,
        help_text=_('List of aggregation functions to apply')
    )
    group_by_fields = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=[],
        help_text=_('List of fields to group by')
    )
    filter_criteria = FilterSerializer(
        required=False,
        help_text=_('Filter criteria for aggregation')
    )


class GroupBySerializer(serializers.Serializer):
    """Serializer for grouping audit logs"""
    
    group_by_field = serializers.CharField(
        max_length=100,
        required=True,
        help_text=_('Field to group by')
    )
    aggregation_function = serializers.ChoiceField(
        choices=[
            ('count', _('Count')),
            ('sum', _('Sum')),
            ('avg', _('Average')),
            ('min', _('Minimum')),
            ('max', _('Maximum')),
            ('stddev', _('Standard Deviation')),
            ('variance', _('Variance')),
        ],
        required=False,
        default='count',
        help_text=_('Aggregation function to apply')
    )
    filter_criteria = FilterSerializer(
        required=False,
        help_text=_('Filter criteria for grouping')
    )


class JoinSerializer(serializers.Serializer):
    """Serializer for joining audit logs with other data sources"""
    
    join_type = serializers.ChoiceField(
        choices=[
            ('inner', _('Inner Join')),
            ('left', _('Left Join')),
            ('right', _('Right Join')),
            ('full', _('Full Join')),
        ],
        required=True,
        help_text=_('Type of join to perform')
    )
    join_field = serializers.CharField(
        max_length=100,
        required=True,
        help_text=_('Field to join on')
    )
    join_with = serializers.ChoiceField(
        choices=[
            ('users', _('Users')),
            ('services', _('Services')),
            ('layers', _('Layers')),
            ('alerts', _('Alerts')),
            ('reports', _('Reports')),
            ('notifications', _('Notifications')),
            ('email_notifications', _('Email Notifications')),
            ('webhook_notifications', _('Webhook Notifications')),
        ],
        required=True,
        help_text=_('Data source to join with')
    )
    filter_criteria = FilterSerializer(
        required=False,
        help_text=_('Filter criteria for join')
    )
