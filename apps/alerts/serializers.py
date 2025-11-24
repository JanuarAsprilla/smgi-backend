"""
Serializers for Alerts app.
"""
from rest_framework import serializers
from .models import (
    AlertChannel,
    AlertRule,
    Alert,
    AlertLog,
    AlertSubscription,
    AlertTemplate
)


class AlertChannelSerializer(serializers.ModelSerializer):
    """Serializer for AlertChannel Model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertChannel
        fields = [
            'id',
            'name',
            'description',
            'channel_type',
            'configuration',
            'is_enabled',
            'is_active',
            'last_used',
            'total_sent',
            'total_failed',
            'success_rate',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_used', 'total_sent', 'total_failed', 'created_at', 'updated_at']
        extra_kwargs = {
            'configuration': {'write_only': True}
        }
    
    def get_success_rate(self, obj) -> float:
        """Calculate success rate percentage."""
        if obj.total_sent == 0:
            return 0.0
        success = obj.total_sent - obj.total_failed
        return round((success / obj.total_sent) * 100, 2)


class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for AlertRule model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    channel_names = serializers.SerializerMethodField()
    recipient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertRule
        fields = [
            'id',
            'name',
            'description',
            'severity',
            'trigger_type',
            'conditions',
            'monitors',
            'projects',
            'recipients',
            'channels',
            'channel_names',
            'recipient_count',
            'message_template',
            'throttle_minutes',
            'is_enabled',
            'is_active',
            'trigger_count',
            'last_triggered',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'trigger_count', 'last_triggered', 'created_at', 'updated_at']
    
    def get_channel_names(self, obj) -> list:
        """Get list of channel names."""
        return [channel.name for channel in obj.channels.all()]
    
    def get_recipient_count(self, obj) -> int:
        """Get number of recipients."""
        return obj.recipients.count()


class AlertLogSerializer(serializers.ModelSerializer):
    """Serializer for AlertLog model."""
    alert_title = serializers.CharField(source='alert.title', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    
    class Meta:
        model = AlertLog
        fields = [
            'id',
            'alert',
            'alert_title',
            'channel',
            'channel_name',
            'recipient',
            'recipient_username',
            'status',
            'sent_at',
            'response',
            'error_message',
            'retry_count',
            'metadata',
        ]
        read_only_fields = ['id', 'sent_at']


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert model."""
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    detection_title = serializers.CharField(source='detection.title', read_only=True, allow_null=True)
    monitor_name = serializers.CharField(source='monitor.name', read_only=True, allow_null=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    acknowledged_by_username = serializers.CharField(source='acknowledged_by.username', read_only=True, allow_null=True)
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Alert
        fields = [
            'id',
            'rule',
            'rule_name',
            'title',
            'message',
            'severity',
            'status',
            'detection',
            'detection_title',
            'monitor',
            'monitor_name',
            'alert_data',
            'sent_at',
            'delivery_details',
            'acknowledged_by',
            'acknowledged_by_username',
            'acknowledged_at',
            'resolved_by',
            'resolved_by_username',
            'resolved_at',
            'resolution_notes',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'sent_at',
            'delivery_details',
            'acknowledged_by',
            'acknowledged_at',
            'resolved_by',
            'resolved_at',
            'created_at'
        ]


class AlertDetailSerializer(AlertSerializer):
    """Detailed serializer for Alert with logs."""
    logs = AlertLogSerializer(many=True, read_only=True)
    
    class Meta(AlertSerializer.Meta):
        fields = AlertSerializer.Meta.fields + ['logs']


class AlertSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for AlertSubscription model."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    channel_names = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertSubscription
        fields = [
            'id',
            'user',
            'user_username',
            'projects',
            'monitors',
            'min_severity',
            'channels',
            'channel_names',
            'quiet_hours_start',
            'quiet_hours_end',
            'is_enabled',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_channel_names(self, obj) -> list:
        """Get list of channel names."""
        return [channel.name for channel in obj.channels.all()]


class AlertTemplateSerializer(serializers.ModelSerializer):
    """Serializer for AlertTemplate model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = AlertTemplate
        fields = [
            'id',
            'name',
            'description',
            'subject_template',
            'body_template',
            'variables',
            'is_default',
            'is_active',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class AlertStatisticsSerializer(serializers.Serializer):
    """Serializer for alert statistics."""
    total_alerts = serializers.IntegerField()
    pending_alerts = serializers.IntegerField()
    sent_alerts = serializers.IntegerField()
    failed_alerts = serializers.IntegerField()
    acknowledged_alerts = serializers.IntegerField()
    alerts_by_severity = serializers.DictField()
    alerts_by_status = serializers.DictField()
    recent_alerts = serializers.ListField()
    top_rules = serializers.ListField()
