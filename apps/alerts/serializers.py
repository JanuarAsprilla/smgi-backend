"""
SMGI Backend - Alerts Serializers
Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.utils.translation import gettext_lazy as _

from apps.alerts.models import (
    Alert, AlertAction, AlertRule, NotificationChannel,
    AlertNotification, AlertStatus
)


class AlertListSerializer(serializers.ModelSerializer):
    """Simplified serializer for alert listing"""
    
    service_name = serializers.CharField(source='service.name', read_only=True, allow_null=True)
    layer_name = serializers.CharField(source='layer.name', read_only=True, allow_null=True)
    assigned_to_name = serializers.SerializerMethodField()
    age_hours = serializers.ReadOnlyField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_id', 'title', 'category', 'severity', 'status',
            'service', 'service_name', 'layer', 'layer_name',
            'affected_features_count', 'change_percentage',
            'assigned_to', 'assigned_to_name', 'first_detected',
            'acknowledged_at', 'resolved_at', 'age_hours', 'tags'
        ]
        read_only_fields = fields
    
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None


class AlertDetailSerializer(GeoFeatureModelSerializer):
    """Detailed serializer for alerts with geometry"""
    
    service_name = serializers.CharField(source='service.name', read_only=True, allow_null=True)
    layer_name = serializers.CharField(source='layer.name', read_only=True, allow_null=True)
    assigned_to_name = serializers.SerializerMethodField()
    acknowledged_by_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    age_hours = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    time_to_acknowledge = serializers.ReadOnlyField()
    time_to_resolve = serializers.ReadOnlyField()
    actions_count = serializers.SerializerMethodField()
    notifications_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        geo_field = 'alert_extent'
        fields = [
            'id', 'title', 'description', 'alert_id', 'category', 'severity',
            'service', 'service_name', 'layer', 'layer_name',
            'affected_features_count', 'change_percentage', 'threshold_value',
            'actual_value', 'alert_extent', 'metadata', 'tags', 'status',
            'first_detected', 'last_updated', 'acknowledged_at', 'resolved_at',
            'expires_at', 'assigned_to', 'assigned_to_name', 'acknowledged_by',
            'acknowledged_by_name', 'resolved_by', 'resolved_by_name',
            'auto_resolve', 'auto_resolve_duration', 'suppress_similar',
            'suppression_duration', 'notification_sent', 'notification_count',
            'last_notification_sent', 'external_ticket_id', 'age_hours',
            'is_expired', 'time_to_acknowledge', 'time_to_resolve',
            'actions_count', 'notifications_count', 'created', 'modified'
        ]
        read_only_fields = [
            'id', 'alert_id', 'first_detected', 'last_updated',
            'acknowledged_at', 'resolved_at', 'notification_sent',
            'notification_count', 'last_notification_sent',
            'created', 'modified'
        ]
    
    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None
    
    def get_acknowledged_by_name(self, obj):
        return obj.acknowledged_by.get_full_name() if obj.acknowledged_by else None
    
    def get_resolved_by_name(self, obj):
        return obj.resolved_by.get_full_name() if obj.resolved_by else None
    
    def get_actions_count(self, obj):
        return obj.actions.count()
    
    def get_notifications_count(self, obj):
        return obj.notifications.count()


class AlertActionSerializer(serializers.ModelSerializer):
    """Serializer for alert actions"""
    
    user_name = serializers.SerializerMethodField()
    alert_title = serializers.CharField(source='alert.title', read_only=True)
    
    class Meta:
        model = AlertAction
        fields = [
            'id', 'alert', 'alert_title', 'action_type', 'user',
            'user_name', 'notes', 'metadata', 'created'
        ]
        read_only_fields = ['id', 'created']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'


class AlertAcknowledgeSerializer(serializers.Serializer):
    """Serializer for acknowledging alerts"""
    
    notes = serializers.CharField(required=False, allow_blank=True)


class AlertResolveSerializer(serializers.Serializer):
    """Serializer for resolving alerts"""
    
    notes = serializers.CharField(required=False, allow_blank=True)


class AlertAssignSerializer(serializers.Serializer):
    """Serializer for assigning alerts"""
    
    user_id = serializers.UUIDField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class AlertCommentSerializer(serializers.Serializer):
    """Serializer for adding comments to alerts"""
    
    comment = serializers.CharField(required=True)


class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for alert rules"""
    
    services = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    layers = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=None,
        source='services',
        required=False
    )
    layer_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=None,
        source='layers',
        required=False
    )
    created_by_name = serializers.SerializerMethodField()
    alerts_in_last_hour = serializers.ReadOnlyField()
    can_generate_alert = serializers.ReadOnlyField()
    
    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'services', 'service_ids',
            'layers', 'layer_ids', 'category', 'severity',
            'trigger_condition', 'warning_threshold', 'critical_threshold',
            'is_active', 'auto_resolve', 'auto_resolve_hours',
            'send_notifications', 'notification_template',
            'max_alerts_per_hour', 'suppress_similar_minutes',
            'escalate_after_hours', 'escalate_to', 'last_triggered',
            'total_alerts_generated', 'alerts_in_last_hour',
            'can_generate_alert', 'created_by', 'created_by_name',
            'created', 'modified'
        ]
        read_only_fields = [
            'id', 'last_triggered', 'total_alerts_generated',
            'created', 'modified'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gis_services.models import ArcGISService, SpatialLayer
        self.fields['service_ids'].child_relation.queryset = ArcGISService.objects.filter(is_removed=False)
        self.fields['layer_ids'].child_relation.queryset = SpatialLayer.objects.filter(is_removed=False)
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class NotificationChannelSerializer(serializers.ModelSerializer):
    """Serializer for notification channels"""
    
    success_rate = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'description', 'channel_type', 'configuration',
            'severity_filter', 'category_filter', 'rate_limit_minutes',
            'max_notifications_per_hour', 'is_active', 'last_used',
            'success_count', 'failure_count', 'success_rate',
            'created_by', 'created_by_name', 'created', 'modified'
        ]
        read_only_fields = [
            'id', 'last_used', 'success_count', 'failure_count',
            'created', 'modified'
        ]
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class AlertNotificationSerializer(serializers.ModelSerializer):
    """Serializer for alert notifications"""
    
    alert_title = serializers.CharField(source='alert.title', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    
    class Meta:
        model = AlertNotification
        fields = [
            'id', 'alert', 'alert_title', 'channel', 'channel_name',
            'recipient', 'subject', 'message', 'sent_at', 'delivered_at',
            'read_at', 'status', 'error_message', 'external_id'
        ]
        read_only_fields = fields


class AlertStatisticsSerializer(serializers.Serializer):
    """Serializer for alert statistics"""
    
    total_alerts = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    critical_alerts = serializers.IntegerField()
    unacknowledged_alerts = serializers.IntegerField()
    resolved_today = serializers.IntegerField()
    average_resolution_time_hours = serializers.FloatField()
    alerts_by_severity = serializers.DictField()
    alerts_by_category = serializers.DictField()
    top_services_with_alerts = serializers.ListField()


class BulkAlertActionSerializer(serializers.Serializer):
    """Serializer for bulk alert actions"""
    
    alert_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )
    action = serializers.ChoiceField(
        choices=['acknowledge', 'resolve', 'dismiss'],
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)