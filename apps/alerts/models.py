"""
Models for Alerts app.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import User
from apps.monitoring.models import Detection, Monitor, MonitoringProject


class BaseModel(models.Model):
    """
    Abstract base model with common fields.
    """
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_created',
        verbose_name=_('creado por')
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_updated',
        verbose_name=_('actualizado por')
    )
    created_at = models.DateTimeField(
        _('fecha de creación'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('fecha de actualización'),
        auto_now=True
    )
    is_active = models.BooleanField(
        _('activo'),
        default=True
    )
    
    class Meta:
        abstract = True


class AlertChannel(BaseModel):
    """
    Model for alert channels (email, SMS, webhook, etc.)
    """
    
    class ChannelType(models.TextChoices):
        EMAIL = 'email', _('Email')
        SMS = 'sms', _('SMS')
        WEBHOOK = 'webhook', _('Webhook')
        SLACK = 'slack', _('Slack')
        TELEGRAM = 'telegram', _('Telegram')
        PUSH = 'push', _('Push Notification')
        IN_APP = 'in_app', _('In-App')
    
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    channel_type = models.CharField(
        _('tipo de canal'),
        max_length=20,
        choices=ChannelType.choices
    )
    
    # Configuration
    configuration = models.JSONField(
        _('configuración'),
        default=dict,
        blank=True,
        help_text=_('Configuración específica del canal (URL, credenciales, etc.)')
    )
    
    # Status
    is_enabled = models.BooleanField(
        _('habilitado'),
        default=True
    )
    last_used = models.DateTimeField(
        _('último uso'),
        null=True,
        blank=True
    )
    
    # Statistics
    total_sent = models.IntegerField(
        _('total enviados'),
        default=0
    )
    total_failed = models.IntegerField(
        _('total fallidos'),
        default=0
    )
    
    class Meta:
        verbose_name = _('canal de alerta')
        verbose_name_plural = _('canales de alerta')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class AlertRule(BaseModel):
    """
    Model for alert rules.
    Defines when and how alerts should be triggered.
    """
    
    class Severity(models.TextChoices):
        LOW = 'low', _('Baja')
        MEDIUM = 'medium', _('Media')
        HIGH = 'high', _('Alta')
        CRITICAL = 'critical', _('Crítica')
    
    class TriggerType(models.TextChoices):
        DETECTION = 'detection', _('Detección')
        THRESHOLD = 'threshold', _('Umbral')
        SCHEDULE = 'schedule', _('Programado')
        CUSTOM = 'custom', _('Personalizado')
    
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    severity = models.CharField(
        _('severidad mínima'),
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        help_text=_('Severidad mínima para activar la alerta')
    )
    trigger_type = models.CharField(
        _('tipo de activación'),
        max_length=20,
        choices=TriggerType.choices,
        default=TriggerType.DETECTION
    )
    
    # Conditions
    conditions = models.JSONField(
        _('condiciones'),
        default=dict,
        blank=True,
        help_text=_('Condiciones para activar la alerta')
    )
    
    # Targets
    monitors = models.ManyToManyField(
        Monitor,
        related_name='alert_rules',
        verbose_name=_('monitores'),
        blank=True
    )
    projects = models.ManyToManyField(
        MonitoringProject,
        related_name='alert_rules',
        verbose_name=_('proyectos'),
        blank=True
    )
    
    # Recipients
    recipients = models.ManyToManyField(
        User,
        related_name='alert_rules',
        verbose_name=_('destinatarios'),
        blank=True
    )
    channels = models.ManyToManyField(
        AlertChannel,
        related_name='alert_rules',
        verbose_name=_('canales')
    )
    
    # Message template
    message_template = models.TextField(
        _('plantilla de mensaje'),
        blank=True,
        help_text=_('Plantilla del mensaje de alerta (soporta variables)')
    )
    
    # Throttling
    throttle_minutes = models.IntegerField(
        _('minutos de espera'),
        default=0,
        help_text=_('Minutos a esperar antes de enviar otra alerta similar (0 = sin límite)')
    )
    
    # Status
    is_enabled = models.BooleanField(
        _('habilitado'),
        default=True
    )
    
    # Statistics
    trigger_count = models.IntegerField(
        _('número de activaciones'),
        default=0
    )
    last_triggered = models.DateTimeField(
        _('última activación'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('regla de alerta')
        verbose_name_plural = _('reglas de alerta')
        ordering = ['-severity', 'name']
        indexes = [
            models.Index(fields=['trigger_type', 'is_enabled']),
            models.Index(fields=['severity', 'is_enabled']),
        ]
    
    def __str__(self):
        return self.name


class Alert(BaseModel):
    """
    Model for alerts.
    Records when an alert rule is triggered.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pendiente')
        SENT = 'sent', _('Enviado')
        FAILED = 'failed', _('Fallido')
        ACKNOWLEDGED = 'acknowledged', _('Reconocido')
        RESOLVED = 'resolved', _('Resuelto')
    
    rule = models.ForeignKey(
        AlertRule,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name=_('regla')
    )
    title = models.CharField(
        _('título'),
        max_length=255
    )
    message = models.TextField(
        _('mensaje')
    )
    severity = models.CharField(
        _('severidad'),
        max_length=20,
        choices=AlertRule.Severity.choices
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Related objects
    detection = models.ForeignKey(
        Detection,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name=_('detección')
    )
    monitor = models.ForeignKey(
        Monitor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name=_('monitor')
    )
    
    # Alert data
    alert_data = models.JSONField(
        _('datos de alerta'),
        default=dict,
        blank=True,
        help_text=_('Datos adicionales de contexto')
    )
    
    # Delivery
    sent_at = models.DateTimeField(
        _('enviado en'),
        null=True,
        blank=True
    )
    delivery_details = models.JSONField(
        _('detalles de entrega'),
        default=dict,
        blank=True,
        help_text=_('Información sobre el envío por cada canal')
    )
    
    # Acknowledgment
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        verbose_name=_('reconocido por')
    )
    acknowledged_at = models.DateTimeField(
        _('reconocido en'),
        null=True,
        blank=True
    )
    
    # Resolution
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        verbose_name=_('resuelto por')
    )
    resolved_at = models.DateTimeField(
        _('resuelto en'),
        null=True,
        blank=True
    )
    resolution_notes = models.TextField(
        _('notas de resolución'),
        blank=True
    )
    
    class Meta:
        verbose_name = _('alerta')
        verbose_name_plural = _('alertas')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rule', 'status']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'severity']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_severity_display()}"


class AlertLog(models.Model):
    """
    Model for alert delivery logs.
    Tracks delivery attempts and results.
    """
    
    class Status(models.TextChoices):
        SUCCESS = 'success', _('Exitoso')
        FAILED = 'failed', _('Fallido')
        PENDING = 'pending', _('Pendiente')
        RETRY = 'retry', _('Reintentando')
    
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name=_('alerta')
    )
    channel = models.ForeignKey(
        AlertChannel,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name=_('canal')
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='alert_logs',
        verbose_name=_('destinatario')
    )
    
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices
    )
    
    # Delivery details
    sent_at = models.DateTimeField(
        _('enviado en'),
        auto_now_add=True
    )
    response = models.TextField(
        _('respuesta'),
        blank=True,
        help_text=_('Respuesta del servicio de entrega')
    )
    error_message = models.TextField(
        _('mensaje de error'),
        blank=True
    )
    retry_count = models.IntegerField(
        _('intentos'),
        default=0
    )
    
    # Metadata
    metadata = models.JSONField(
        _('metadatos'),
        default=dict,
        blank=True
    )
    
    class Meta:
        verbose_name = _('log de alerta')
        verbose_name_plural = _('logs de alertas')
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['alert', 'status']),
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"{self.alert.title} - {self.channel.name} ({self.status})"


class AlertSubscription(BaseModel):
    """
    Model for user alert subscriptions.
    Users can subscribe to specific types of alerts.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='alert_subscriptions',
        verbose_name=_('usuario')
    )
    
    # Subscription targets
    projects = models.ManyToManyField(
        MonitoringProject,
        related_name='subscriptions',
        verbose_name=_('proyectos'),
        blank=True
    )
    monitors = models.ManyToManyField(
        Monitor,
        related_name='subscriptions',
        verbose_name=_('monitores'),
        blank=True
    )
    
    # Preferences
    min_severity = models.CharField(
        _('severidad mínima'),
        max_length=20,
        choices=AlertRule.Severity.choices,
        default=AlertRule.Severity.MEDIUM
    )
    channels = models.ManyToManyField(
        AlertChannel,
        related_name='subscriptions',
        verbose_name=_('canales preferidos')
    )
    
    # Schedule
    quiet_hours_start = models.TimeField(
        _('inicio de horas silenciosas'),
        null=True,
        blank=True,
        help_text=_('No enviar alertas durante este período')
    )
    quiet_hours_end = models.TimeField(
        _('fin de horas silenciosas'),
        null=True,
        blank=True
    )
    
    # Status
    is_enabled = models.BooleanField(
        _('habilitado'),
        default=True
    )
    
    class Meta:
        verbose_name = _('suscripción de alerta')
        verbose_name_plural = _('suscripciones de alertas')
        ordering = ['user', '-created_at']
        unique_together = ['user']
    
    def __str__(self):
        return f"Suscripción de {self.user.username}"


class AlertTemplate(BaseModel):
    """
    Model for alert message templates.
    """
    name = models.CharField(
        _('nombre'),
        max_length=255,
        unique=True
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    
    # Template content
    subject_template = models.CharField(
        _('plantilla de asunto'),
        max_length=500,
        blank=True
    )
    body_template = models.TextField(
        _('plantilla de cuerpo')
    )
    
    # Metadata
    variables = models.JSONField(
        _('variables disponibles'),
        default=list,
        blank=True,
        help_text=_('Lista de variables que se pueden usar en la plantilla')
    )
    
    # Usage
    is_default = models.BooleanField(
        _('es por defecto'),
        default=False
    )
    
    class Meta:
        verbose_name = _('plantilla de alerta')
        verbose_name_plural = _('plantillas de alertas')
        ordering = ['name']
    
    def __str__(self):
        return self.name
