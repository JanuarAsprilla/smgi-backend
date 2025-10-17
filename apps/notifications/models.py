"""
SMGI Backend - Notifications Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos completos para el sistema de notificaciones
"""
import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel, SoftDeletableModel

from apps.common.models import BaseModel
from apps.authentication.models import User
# Importar Alert con un alias para evitar conflictos de nombre si es necesario en este contexto
# from apps.alerts.models import Alert as AlertsAppAlert # Si se necesita desambiguar
from apps.alerts.models import Alert # Asumimos que el modelo Alert es accesible


class NotificationType(models.TextChoices):
    """Tipos de notificaciones"""
    ALERT = 'alert', _('Alert')
    INFO = 'info', _('Information')
    WARNING = 'warning', _('Warning')
    SUCCESS = 'success', _('Success')
    ERROR = 'error', _('Error')
    SYSTEM = 'system', _('System')


class NotificationPriority(models.TextChoices):
    """Prioridades de notificaciones"""
    LOW = 'low', _('Low')
    NORMAL = 'normal', _('Normal')
    HIGH = 'high', _('High')
    URGENT = 'urgent', _('Urgent')


class NotificationChannel(models.TextChoices):
    """Canales de notificación"""
    IN_APP = 'in_app', _('In-App')
    EMAIL = 'email', _('Email')
    SMS = 'sms', _('SMS')
    WEBHOOK = 'webhook', _('Webhook')
    PUSH = 'push', _('Push Notification')


class Notification(BaseModel):
    """
    Modelo principal para notificaciones en el sistema
    """
    # Identificación
    title = models.CharField(_('Title'), max_length=200)
    message = models.TextField(_('Message'))
    short_message = models.CharField(_('Short Message'), max_length=255, blank=True)
    
    # Clasificación
    notification_type = models.CharField(
        _('Type'),
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
        db_index=True
    )
    priority = models.CharField(
        _('Priority'),
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL,
        db_index=True
    )
    
    # Destinatario
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    
    # Estado
    is_read = models.BooleanField(_('Is Read'), default=False, db_index=True)
    read_at = models.DateTimeField(_('Read At'), null=True, blank=True)
    
    # Contenido adicional
    link = models.URLField(_('Link'), blank=True, help_text=_('URL to related resource'))
    action_text = models.CharField(_('Action Text'), max_length=50, blank=True)
    action_url = models.URLField(_('Action URL'), blank=True)
    
    # Metadata
    metadata = models.JSONField(
        _('Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional data for the notification')
    )
    
    # Relaciones
    # --- CORRECCIÓN: Cambiar related_name para evitar conflicto con apps.alerts.models.Alert ---
    # Original: related_name='in_app_notifications'
    # Conflictivo porque apps.alerts.models.Alert también tiene related_name='in_app_notifications'
    # Solución: Usar un nombre de related_name único para esta app.
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications_in_app', # Cambiado de 'in_app_notifications'
        help_text=_('The alert this notification is about.')
    )
    
    # Caducidad
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    
    # Agrupación
    group_key = models.CharField(
        _('Group Key'),
        max_length=100,
        blank=True,
        db_index=True,
        help_text=_('Key for grouping similar notifications')
    )
    
    class Meta:
        db_table = 'notifications_notification'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created']),
            models.Index(fields=['notification_type', '-created']),
            models.Index(fields=['priority', '-created']),
            models.Index(fields=['group_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_unread(self):
        """Mark notification as unread"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])


class EmailNotification(BaseModel):
    """
    Modelo para notificaciones por email
    """
    # Identificación
    subject = models.CharField(_('Subject'), max_length=255)
    body_text = models.TextField(_('Body (Plain Text)'))
    body_html = models.TextField(_('Body (HTML)'), blank=True)
    
    # Destinatarios
    recipient_email = models.EmailField(_('Recipient Email'))
    recipient_name = models.CharField(_('Recipient Name'), max_length=200, blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_notifications'
    )
    
    # CC y BCC
    cc_emails = ArrayField(
        models.EmailField(),
        size=10,
        default=list,
        blank=True,
        verbose_name=_('CC Emails')
    )
    bcc_emails = ArrayField(
        models.EmailField(),
        size=10,
        default=list,
        blank=True,
        verbose_name=_('BCC Emails')
    )
    
    # Attachments
    has_attachments = models.BooleanField(_('Has Attachments'), default=False)
    attachments = models.JSONField(
        _('Attachments'),
        default=list,
        blank=True,
        help_text=_('List of attachment file paths')
    )
    
    # Estado de envío
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('sending', _('Sending')),
            ('sent', _('Sent')),
            ('failed', _('Failed')),
            ('bounced', _('Bounced')),
        ],
        default='pending',
        db_index=True
    )
    
    # Tracking
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)
    opened_at = models.DateTimeField(_('Opened At'), null=True, blank=True)
    clicked_at = models.DateTimeField(_('Clicked At'), null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(_('Error Message'), blank=True)
    retry_count = models.PositiveIntegerField(_('Retry Count'), default=0)
    max_retries = models.PositiveIntegerField(_('Max Retries'), default=3)
    next_retry_at = models.DateTimeField(_('Next Retry At'), null=True, blank=True)
    
    # External references
    external_id = models.CharField(
        _('External ID'),
        max_length=255,
        blank=True,
        help_text=_('ID from email service provider')
    )
    
    # Template
    template_name = models.CharField(_('Template Name'), max_length=100, blank=True)
    template_context = models.JSONField(_('Template Context'), default=dict, blank=True)
    
    # Priority
    priority = models.CharField(
        _('Priority'),
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL
    )
    
    # Related objects
    # --- CORRECCIÓN: Cambiar related_name para evitar conflicto con apps.alerts.models.Alert ---
    # Original: related_name='email_notifications'
    # Conflictivo porque apps.alerts.models.Alert también tiene related_name='email_notifications'
    # Solución: Usar un nombre de related_name único para esta app.
    alert = models.ForeignKey(
        Alert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications_email', # Cambiado de 'email_notifications'
        help_text=_('The alert this email notification is about.')
    )
    
    class Meta:
        db_table = 'notifications_email'
        verbose_name = _('Email Notification')
        verbose_name_plural = _('Email Notifications')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['recipient_email', '-created']),
            models.Index(fields=['status', '-created']),
            models.Index(fields=['user', '-created']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['next_retry_at']),
        ]
    
    def __str__(self):
        return f"{self.subject} -> {self.recipient_email}"
    
    @property
    def can_retry(self):
        """Check if email can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries
    
    def mark_sent(self, external_id=None):
        """Mark email as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if external_id:
            self.external_id = external_id
        self.save(update_fields=['status', 'sent_at', 'external_id'])
    
    def mark_failed(self, error_message):
        """Mark email as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        
        if self.can_retry:
            # Calculate next retry time with exponential backoff
            delay_minutes = 5 * (2 ** self.retry_count)
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
        
        self.save(update_fields=['status', 'error_message', 'retry_count', 'next_retry_at'])
    
    def mark_delivered(self):
        """Mark email as delivered"""
        self.delivered_at = timezone.now()
        self.save(update_fields=['delivered_at'])
    
    def mark_opened(self):
        """Mark email as opened"""
        self.opened_at = timezone.now()
        self.save(update_fields=['opened_at'])
    
    def mark_clicked(self):
        """Mark link in email as clicked"""
        self.clicked_at = timezone.now()
        self.save(update_fields=['clicked_at'])


class WebhookNotification(BaseModel):
    """
    Modelo para notificaciones vía webhook
    """
    # Webhook configuration
    webhook_url = models.URLField(_('Webhook URL'))
    method = models.CharField(
        _('HTTP Method'),
        max_length=10,
        choices=[
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('PATCH', 'PATCH'),
        ],
        default='POST'
    )
    
    # Headers
    headers = models.JSONField(_('Headers'), default=dict, blank=True)
    
    # Payload
    payload = models.JSONField(_('Payload'))
    
    # Authentication
    auth_type = models.CharField(
        _('Auth Type'),
        max_length=20,
        choices=[
            ('none', _('None')),
            ('basic', _('Basic Auth')),
            ('bearer', _('Bearer Token')),
            ('api_key', _('API Key')),
        ],
        default='none'
    )
    auth_credentials = models.JSONField(_('Auth Credentials'), default=dict, blank=True)
    
    # Status
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('sent', _('Sent')),
            ('failed', _('Failed')),
        ],
        default='pending',
        db_index=True
    )
    
    # Response
    sent_at = models.DateTimeField(_('Sent At'), null=True, blank=True)
    response_status_code = models.PositiveIntegerField(_('Response Status Code'), null=True, blank=True)
    response_body = models.TextField(_('Response Body'), blank=True)
    response_time_ms = models.PositiveIntegerField(_('Response Time (ms)'), null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(_('Error Message'), blank=True)
    retry_count = models.PositiveIntegerField(_('Retry Count'), default=0)
    max_retries = models.PositiveIntegerField(_('Max Retries'), default=3)
    
    # Related objects
    # --- CORRECCIÓN: Cambiar related_name para evitar conflicto con apps.alerts.models.Alert ---
    # Original: related_name='webhook_notifications'
    # Conflictivo porque apps.alerts.models.Alert también tiene related_name='webhook_notifications'
    # Solución: Usar un nombre de related_name único para esta app.
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications_webhook', # Cambiado de 'webhook_notifications'
        help_text=_('The alert this webhook notification is about.')
    )
    
    class Meta:
        db_table = 'notifications_webhook'
        verbose_name = _('Webhook Notification')
        verbose_name_plural = _('Webhook Notifications')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['status', '-created']),
            models.Index(fields=['webhook_url']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"Webhook to {self.webhook_url}"
    
    def mark_sent(self, status_code, response_body, response_time_ms):
        """Mark webhook as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.response_status_code = status_code
        self.response_body = response_body
        self.response_time_ms = response_time_ms
        self.save(update_fields=[
            'status', 'sent_at', 'response_status_code',
            'response_body', 'response_time_ms'
        ])
    
    def mark_failed(self, error_message):
        """Mark webhook as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count'])


class NotificationPreference(BaseModel):
    """
    Preferencias de notificación por usuario
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Canales habilitados
    email_enabled = models.BooleanField(_('Email Enabled'), default=True)
    sms_enabled = models.BooleanField(_('SMS Enabled'), default=False)
    push_enabled = models.BooleanField(_('Push Enabled'), default=True)
    in_app_enabled = models.BooleanField(_('In-App Enabled'), default=True)
    
    # Tipos de notificaciones por canal
    email_alert_notifications = models.BooleanField(_('Email Alert Notifications'), default=True)
    email_report_notifications = models.BooleanField(_('Email Report Notifications'), default=True)
    email_system_notifications = models.BooleanField(_('Email System Notifications'), default=True)
    
    # Horarios
    quiet_hours_enabled = models.BooleanField(_('Quiet Hours Enabled'), default=False)
    quiet_hours_start = models.TimeField(_('Quiet Hours Start'), null=True, blank=True)
    quiet_hours_end = models.TimeField(_('Quiet Hours End'), null=True, blank=True)
    
    # Frecuencia
    digest_enabled = models.BooleanField(_('Digest Enabled'), default=False)
    digest_frequency = models.CharField(
        _('Digest Frequency'),
        max_length=10,
        choices=[
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
        ],
        default='daily',
        blank=True
    )
    
    # Severidad mínima
    min_alert_severity = models.CharField(
        _('Minimum Alert Severity'),
        max_length=10,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ],
        default='medium'
    )
    
    class Meta:
        db_table = 'notifications_preference'
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
    
    def should_notify(self, channel, notification_type):
        """Check if user should be notified"""
        # Check if channel is enabled
        if channel == NotificationChannel.EMAIL and not self.email_enabled:
            return False
        elif channel == NotificationChannel.SMS and not self.sms_enabled:
            return False
        elif channel == NotificationChannel.PUSH and not self.push_enabled:
            return False
        elif channel == NotificationChannel.IN_APP and not self.in_app_enabled:
            return False
        
        # Check quiet hours
        if self.quiet_hours_enabled and self.is_quiet_hours():
            return False
        
        return True
    
    def is_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        current_time = timezone.now().time()
        
        if self.quiet_hours_start < self.quiet_hours_end:
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end
        else:
            # Quiet hours span midnight
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end
