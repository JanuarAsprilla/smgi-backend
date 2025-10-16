"""
SMGI Backend - Alerts Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos para sistema de alertas y notificaciones
"""
import uuid
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel, SoftDeletableModel
from apps.common.models import BaseModel
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer


class AlertSeverity(models.TextChoices):
    """Alert severity levels"""
    LOW = 'low', _('Low')
    MEDIUM = 'medium', _('Medium')
    HIGH = 'high', _('High')
    CRITICAL = 'critical', _('Critical')


class AlertStatus(models.TextChoices):
    """Alert status choices"""
    ACTIVE = 'active', _('Active')
    ACKNOWLEDGED = 'acknowledged', _('Acknowledged')
    RESOLVED = 'resolved', _('Resolved')
    DISMISSED = 'dismissed', _('Dismissed')
    EXPIRED = 'expired', _('Expired')


class AlertCategory(models.TextChoices):
    """Alert category choices"""
    CHANGE_DETECTION = 'change_detection', _('Change Detection')
    SERVICE_AVAILABILITY = 'service_availability', _('Service Availability')
    DATA_QUALITY = 'data_quality', _('Data Quality')
    PERFORMANCE = 'performance', _('Performance')
    SECURITY = 'security', _('Security')
    SYSTEM_HEALTH = 'system_health', _('System Health')
    THRESHOLD_BREACH = 'threshold_breach', _('Threshold Breach')
    ANOMALY = 'anomaly', _('Anomaly Detection')


class Alert(BaseModel):
    """
    Main alert model for the SMGI system
    """
    # Alert identification
    title = models.CharField(_('Alert Title'), max_length=200)
    description = models.TextField(_('Description'))
    alert_id = models.CharField(
        _('Alert ID'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('Unique identifier for this alert')
    )

    # Classification
    category = models.CharField(
        _('Category'),
        max_length=30,
        choices=AlertCategory.choices,
        default=AlertCategory.CHANGE_DETECTION,
        db_index=True
    )
    severity = models.CharField(
        _('Severity'),
        max_length=10,
        choices=AlertSeverity.choices,
        default=AlertSeverity.MEDIUM,
        db_index=True
    )

    # Source information
    service = models.ForeignKey(
        ArcGISService,
        on_delete=models.CASCADE,
        related_name='alerts',
        blank=True,
        null=True
    )
    layer = models.ForeignKey(
        SpatialLayer,
        on_delete=models.CASCADE,
        related_name='alerts',
        blank=True,
        null=True
    )

    # Alert details
    affected_features_count = models.PositiveIntegerField(_('Affected Features Count'), default=0)
    change_percentage = models.FloatField(
        _('Change Percentage'),
        blank=True,
        null=True,
        validators=[MinValueValidator(-100.0), MaxValueValidator(1000.0)]
    )
    threshold_value = models.FloatField(_('Threshold Value'), blank=True, null=True)
    actual_value = models.FloatField(_('Actual Value'), blank=True, null=True)

    # Geographic extent of the alert
    alert_extent = models.PolygonField(
        _('Alert Extent'),
        blank=True,
        null=True,
        srid=4326,
        help_text=_('Geographic extent affected by this alert')
    )

    # Alert metadata
    metadata = models.JSONField(
        _('Alert Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional metadata about the alert')
    )
    tags = ArrayField(
        models.CharField(max_length=50),
        size=10,
        default=list,
        blank=True,
        verbose_name=_('Tags')
    )

    # Status and lifecycle
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.ACTIVE,
        db_index=True
    )

    # Time tracking
    first_detected = models.DateTimeField(_('First Detected'), auto_now_add=True)
    last_updated = models.DateTimeField(_('Last Updated'), auto_now=True)
    acknowledged_at = models.DateTimeField(_('Acknowledged At'), blank=True, null=True)
    resolved_at = models.DateTimeField(_('Resolved At'), blank=True, null=True)
    expires_at = models.DateTimeField(_('Expires At'), blank=True, null=True)

    # Assignment and tracking
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_alerts',
        verbose_name=_('Assigned To')
    )
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        verbose_name=_('Acknowledged By')
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        verbose_name=_('Resolved By')
    )

    # Alert configuration
    auto_resolve = models.BooleanField(_('Auto Resolve'), default=False)
    auto_resolve_duration = models.PositiveIntegerField(
        _('Auto Resolve Duration (hours)'),
        default=24,
        blank=True,
        null=True
    )
    suppress_similar = models.BooleanField(_('Suppress Similar Alerts'), default=True)
    suppression_duration = models.PositiveIntegerField(
        _('Suppression Duration (minutes)'),
        default=60
    )

    # Notification tracking
    notification_sent = models.BooleanField(_('Notification Sent'), default=False)
    notification_count = models.PositiveIntegerField(_('Notification Count'), default=0)
    last_notification_sent = models.DateTimeField(_('Last Notification Sent'), blank=True, null=True)

    # External references
    external_ticket_id = models.CharField(
        _('External Ticket ID'),
        max_length=100,
        blank=True,
        help_text=_('Reference to external ticketing system')
    )
    related_alerts = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='parent_alerts',
        verbose_name=_('Related Alerts')
    )

    class Meta:
        db_table = 'alerts_alert'
        verbose_name = _('Alert')
        verbose_name_plural = _('Alerts')
        ordering = ['-severity', '-created']
        indexes = [
            models.Index(fields=['alert_id']),
            models.Index(fields=['category', '-created']),
            models.Index(fields=['severity', '-created']),
            models.Index(fields=['status', '-created']),
            models.Index(fields=['service', '-created']),
            models.Index(fields=['layer', '-created']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['first_detected']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['notification_sent']),
        ]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"

    # -------------------
    # Helper Properties
    # -------------------
    @property
    def age_hours(self):
        """Calculate alert age in hours"""
        return (timezone.now() - self.first_detected).total_seconds() / 3600

    @property
    def is_expired(self):
        """Check if alert has expired"""
        return self.expires_at and timezone.now() > self.expires_at

    @property
    def should_auto_resolve(self):
        """Check if alert should be auto-resolved"""
        if not self.auto_resolve or not self.auto_resolve_duration:
            return False
        auto_resolve_time = self.first_detected + timezone.timedelta(hours=self.auto_resolve_duration)
        return timezone.now() > auto_resolve_time

    @property
    def time_to_acknowledge(self):
        """Calculate time taken to acknowledge alert"""
        if not self.acknowledged_at:
            return None
        return (self.acknowledged_at - self.first_detected).total_seconds()

    @property
    def time_to_resolve(self):
        """Calculate time taken to resolve alert"""
        if not self.resolved_at:
            return None
        return (self.resolved_at - self.first_detected).total_seconds()

    # -------------------
    # Business Logic
    # -------------------
    def acknowledge(self, user, notes=None):
        """Acknowledge this alert"""
        if self.status == AlertStatus.ACTIVE:
            self.status = AlertStatus.ACKNOWLEDGED
            self.acknowledged_by = user
            self.acknowledged_at = timezone.now()
            self.save(update_fields=['status', 'acknowledged_by', 'acknowledged_at'])
            AlertAction.objects.create(alert=self, action_type=AlertActionType.ACKNOWLEDGED, user=user, notes=notes or '')
            return True
        return False

    def resolve(self, user, notes=None):
        """Resolve this alert"""
        if self.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
            self.status = AlertStatus.RESOLVED
            self.resolved_by = user
            self.resolved_at = timezone.now()
            self.save(update_fields=['status', 'resolved_by', 'resolved_at'])
            AlertAction.objects.create(alert=self, action_type=AlertActionType.RESOLVED, user=user, notes=notes or '')
            return True
        return False

    def dismiss(self, user, notes=None):
        """Dismiss this alert"""
        if self.status != AlertStatus.DISMISSED:
            self.status = AlertStatus.DISMISSED
            self.save(update_fields=['status'])
            AlertAction.objects.create(alert=self, action_type=AlertActionType.DISMISSED, user=user, notes=notes or '')
            return True
        return False

    def assign_to(self, user, assigned_by):
        """Assign alert to a user"""
        self.assigned_to = user
        self.save(update_fields=['assigned_to'])
        AlertAction.objects.create(
            alert=self,
            action_type=AlertActionType.ASSIGNED,
            user=assigned_by,
            notes=f'Assigned to {user.get_full_name()}'
        )

    def add_comment(self, user, comment):
        """Add comment to alert"""
        AlertAction.objects.create(
            alert=self,
            action_type=AlertActionType.COMMENTED,
            user=user,
            notes=comment
        )

    def get_similar_active_alerts(self, minutes=60):
        """Get similar active alerts within specified time window"""
        similar_time = timezone.now() - timezone.timedelta(minutes=minutes)
        return Alert.objects.filter(
            category=self.category,
            severity=self.severity,
            service=self.service,
            layer=self.layer,
            status=AlertStatus.ACTIVE,
            first_detected__gte=similar_time
        ).exclude(id=self.id)

    def should_suppress_notifications(self):
        """Check if notifications should be suppressed due to similar alerts"""
        if not self.suppress_similar:
            return False
        similar_alerts = self.get_similar_active_alerts(self.suppression_duration)
        return similar_alerts.exists()

    def increment_notification_count(self):
        """Increment notification count and update last sent time"""
        self.notification_count += 1
        self.last_notification_sent = timezone.now()
        self.notification_sent = True
        self.save(update_fields=['notification_count', 'last_notification_sent', 'notification_sent'])


class AlertActionType(models.TextChoices):
    """Types of actions that can be performed on alerts"""
    CREATED = 'created', _('Created')
    ACKNOWLEDGED = 'acknowledged', _('Acknowledged')
    ASSIGNED = 'assigned', _('Assigned')
    RESOLVED = 'resolved', _('Resolved')
    DISMISSED = 'dismissed', _('Dismissed')
    COMMENTED = 'commented', _('Commented')
    ESCALATED = 'escalated', _('Escalated')


class AlertAction(BaseModel):
    """Records actions performed on alerts"""
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=20, choices=AlertActionType.choices)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'alerts_action'
        verbose_name = _('Alert Action')
        verbose_name_plural = _('Alert Actions')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_action_type_display()} - {self.alert.title}"
