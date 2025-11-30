"""
Serializers for Notifications app.
"""
from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'user',
            'type',
            'title',
            'message',
            'related_object_type',
            'related_object_id',
            'is_read',
            'read_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationPreferencesSerializer(serializers.Serializer):
    """Serializer for user notification preferences."""
    email_notifications = serializers.BooleanField()
    sms_notifications = serializers.BooleanField()
    push_notifications = serializers.BooleanField()
    notify_analysis_complete = serializers.BooleanField()
    notify_analysis_failed = serializers.BooleanField()
    notify_alerts_critical = serializers.BooleanField()
    notify_alerts_medium = serializers.BooleanField()
    notify_alerts_low = serializers.BooleanField()
    notify_resource_shared = serializers.BooleanField()
    notify_weekly_report = serializers.BooleanField()
