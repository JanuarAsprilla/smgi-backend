"""
SMGI Backend - Notifications Serializers
Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.notifications.models import (
    Notification, EmailNotification, WebhookNotification,
    NotificationPreference
)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones in-app"""
    
    # --- MEJORA: Usar SerializerMethodField para manejar alert=None de forma segura ---
    alert_title = serializers.CharField(source='alert.title', read_only=True, allow_null=True)
    alert_title = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'short_message', 'notification_type',
            'priority', 'is_read', 'read_at', 'link', 'action_text',
            'action_url', 'metadata', 'alert', 'alert_title', 'expires_at',
            'group_key', 'is_expired', 'created'
        ]
        read_only_fields = ['id', 'read_at', 'created']

    def get_alert_title(self, obj):
        """Get the title of the related alert, handling null cases safely."""
        # obj.alert puede ser None. Acceder a .title en None lanza AttributeError.
        # Esta forma es explícita y segura.
        return obj.alert.title if obj.alert else None


class EmailNotificationSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones por email"""
    
    recipient_name = serializers.SerializerMethodField()
    can_retry = serializers.ReadOnlyField()
    
    class Meta:
        model = EmailNotification
        fields = [
            'id', 'subject', 'recipient_email', 'recipient_name',
            'status', 'sent_at', 'delivered_at', 'opened_at',
            'clicked_at', 'error_message', 'retry_count',
            'max_retries', 'can_retry', 'priority', 'created'
        ]
        read_only_fields = fields
    
    def get_recipient_name(self, obj):
        # --- MEJORA: Lógica ligeramente más concisa ---
        # Asumimos que recipient_name o user.get_full_name() siempre devuelven un string.
        # Si ambos son None/empty, devolverá un string vacío.
        name_from_user = obj.user.get_full_name() if obj.user else ''
        return obj.recipient_name or name_from_user


class WebhookNotificationSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones webhook"""
    
    class Meta:
        model = WebhookNotification
        fields = [
            'id', 'webhook_url', 'method', 'status', 'sent_at',
            'response_status_code', 'response_time_ms', 'error_message',
            'retry_count', 'created'
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer para preferencias de notificación"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            # --- MEJORA: Incluir 'id' para identificación clara del recurso ---
            'id',
            'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
            'email_alert_notifications', 'email_report_notifications',
            'email_system_notifications', 'quiet_hours_enabled',
            'quiet_hours_start', 'quiet_hours_end', 'digest_enabled',
            'digest_frequency', 'min_alert_severity'
        ]
        # Si se desea que algunos campos sean de solo lectura, se pueden añadir aquí.
        read_only_fields = ['id'] # Opcional, si 'id' no debe ser modificado nunca por la API


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de notificaciones"""
    
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    notifications_today = serializers.IntegerField()
    emails_sent_today = serializers.IntegerField()
    failed_emails = serializers.IntegerField()
