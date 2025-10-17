# apps/notifications/admin.py
"""
SMGI Backend - Notifications Admin
Sistema de Monitoreo Geoespacial Inteligente
Configuración del panel de administración de Django para la app de notificaciones.
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Notification, EmailNotification, WebhookNotification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin para notificaciones in-app."""
    
    list_display = (
        'title', 'user_email', 'notification_type', 'priority',
        'is_read', 'short_message_display', 'created'
    )
    list_filter = (
        'notification_type', 'priority', 'is_read', 'created'
    )
    search_fields = (
        'title', 'message', 'short_message',
        'user__email', 'user__username',
        'alert__title', 'alert__alert_id'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'read_at', 'alert_link'
    )
    raw_id_fields = ('user', 'alert')
    date_hierarchy = 'created'
    ordering = ['-created']
    list_editable = ('is_read',) # Permite marcar como leído directamente desde la lista
    list_select_related = ('user', 'alert') # Optimiza consultas

    fieldsets = (
        ('Información Principal', {
            'fields': ('title', 'message', 'short_message', 'notification_type', 'priority')
        }),
        ('Destinatario y Estado', {
            'fields': ('user', 'is_read', 'read_at', 'expires_at', 'group_key')
        }),
        ('Contenido Adicional', {
            'fields': ('link', 'action_text', 'action_url', 'metadata', 'alert_link')
        }),
        ('Fechas', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',) # Oculto por defecto
        }),
    )

    def user_email(self, obj):
        """Muestra el email del usuario."""
        return obj.user.email if obj.user else '-'
    user_email.short_description = 'Usuario'
    user_email.admin_order_field = 'user__email'

    def short_message_display(self, obj):
        """Muestra un preview del mensaje corto."""
        msg = obj.short_message or (obj.message[:50] + '...') if obj.message else '-'
        return msg
    short_message_display.short_description = 'Mensaje Preview'

    def alert_link(self, obj):
        """Crea un enlace al admin del Alert relacionado, si existe."""
        if obj.alert:
            alert_admin_url = reverse('admin:alerts_alert_change', args=[obj.alert.id])
            return format_html('<a href="{}">{}</a>', alert_admin_url, obj.alert.alert_id)
        return "-"
    alert_link.short_description = 'Alerta Relacionada'


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    """Admin para notificaciones por email."""
    
    list_display = (
        'subject', 'recipient_email', 'status', 'priority',
        'sent_at', 'delivery_status', 'created'
    )
    list_filter = (
        'status', 'priority', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at'
    )
    search_fields = (
        'subject', 'recipient_email', 'recipient_name',
        'user__email', 'user__username', 'external_id'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'sent_at', 'delivered_at',
        'opened_at', 'clicked_at', 'error_message', 'retry_count',
        'next_retry_at', 'external_id', 'alert_link'
    )
    raw_id_fields = ('user', 'alert')
    date_hierarchy = 'created'
    ordering = ['-created']
    list_select_related = ('user', 'alert')

    fieldsets = (
        ('Contenido del Email', {
            'fields': ('subject', 'body_text', 'body_html')
        }),
        ('Destinatarios', {
            'fields': ('recipient_email', 'recipient_name', 'user', 'cc_emails', 'bcc_emails')
        }),
        ('Archivos Adjuntos', {
            'fields': ('has_attachments', 'attachments')
        }),
        ('Estado de Envío', {
            'fields': (
                'status', 'sent_at', 'delivered_at', 'opened_at',
                'clicked_at', 'error_message', 'retry_count',
                'next_retry_at', 'external_id'
            )
        }),
        ('Configuración', {
            'fields': ('priority', 'template_name', 'template_context', 'alert_link')
        }),
        ('Fechas', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )

    def delivery_status(self, obj):
        """Muestra un indicador visual del estado de entrega."""
        if obj.status == 'sent':
            if obj.delivered_at:
                return format_html('<span style="color: green;">✓ Entregado</span>')
            elif obj.opened_at:
                return format_html('<span style="color: blue;">👁 Abierto</span>')
            else:
                return format_html('<span style="color: orange;">⚠ Enviado</span>')
        elif obj.status == 'failed':
            return format_html('<span style="color: red;">✗ Fallido</span>')
        elif obj.status == 'pending':
            return format_html('<span style="color: gray;">🕒 Pendiente</span>')
        return obj.get_status_display()
    delivery_status.short_description = 'Estado de Entrega'


@admin.register(WebhookNotification)
class WebhookNotificationAdmin(admin.ModelAdmin):
    """Admin para notificaciones webhook."""
    
    list_display = (
        'webhook_url_short', 'method', 'status',
        'response_status_code', 'response_time_ms', 'sent_at'
    )
    list_filter = ('method', 'status', 'sent_at')
    search_fields = ('webhook_url', 'alert__title', 'alert__alert_id')
    readonly_fields = (
        'id', 'created', 'modified', 'sent_at',
        'response_status_code', 'response_body', 'response_time_ms',
        'error_message', 'retry_count', 'alert_link'
    )
    raw_id_fields = ('alert',)
    date_hierarchy = 'created'
    ordering = ['-created']
    list_select_related = ('alert',)

    fieldsets = (
        ('Configuración del Webhook', {
            'fields': ('webhook_url', 'method', 'headers', 'payload', 'auth_type', 'auth_credentials')
        }),
        ('Resultado del Envío', {
            'fields': (
                'status', 'sent_at', 'response_status_code',
                'response_body', 'response_time_ms', 'error_message', 'retry_count'
            )
        }),
        ('Relaciones', {
            'fields': ('alert_link',)
        }),
        ('Fechas', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )

    def webhook_url_short(self, obj):
        """Muestra una versión corta de la URL del webhook."""
        return (obj.webhook_url[:50] + '...') if len(obj.webhook_url) > 50 else obj.webhook_url
    webhook_url_short.short_description = 'Webhook URL'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin para preferencias de notificación."""
    
    list_display = (
        'user_email', 'email_enabled', 'sms_enabled', 'push_enabled',
        'in_app_enabled', 'quiet_hours_enabled', 'digest_enabled'
    )
    list_filter = (
        'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
        'quiet_hours_enabled', 'digest_enabled'
    )
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('id', 'created', 'modified')
    raw_id_fields = ('user',)
    ordering = ['user__email']
    list_select_related = ('user',)

    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Canales Habilitados', {
            'fields': ('email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled')
        }),
        ('Tipos de Notificaciones por Canal', {
            'fields': (
                'email_alert_notifications', 'email_report_notifications',
                'email_system_notifications'
            )
        }),
        ('Horarios y Frecuencia', {
            'fields': (
                'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
                'digest_enabled', 'digest_frequency'
            )
        }),
        ('Severidad Mínima', {
            'fields': ('min_alert_severity',)
        }),
        ('Fechas', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        """Muestra el email del usuario."""
        return obj.user.email if obj.user else '-'
    user_email.short_description = 'Usuario'
    user_email.admin_order_field = 'user__email'
