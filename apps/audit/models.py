"""
SMGI Backend - Audit Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos para auditoría y trazabilidad del sistema
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


class AuditEventType(models.TextChoices):
    """Tipos de eventos de auditoría"""
    USER_ACTION = 'user_action', _('User Action')
    DATA_CHANGE = 'data_change', _('Data Change')
    SECURITY_EVENT = 'security_event', _('Security Event')
    SYSTEM_EVENT = 'system_event', _('System Event')
    API_CALL = 'api_call', _('API Call')
    EXTERNAL_API_CALL = 'external_api_call', _('External API Call')
    INTERNAL_API_CALL = 'internal_api_call', _('Internal API Call')
    DATABASE_QUERY = 'database_query', _('Database Query')
    CACHE_OPERATION = 'cache_operation', _('Cache Operation')
    FILE_OPERATION = 'file_operation', _('File Operation')
    EMAIL_SENDING = 'email_sending', _('Email Sending')
    SMS_SENDING = 'sms_sending', _('SMS Sending')
    WEBHOOK_SENDING = 'webhook_sending', _('Webhook Sending')
    PUSH_NOTIFICATION_SENDING = 'push_notification_sending', _('Push Notification Sending')
    REPORT_GENERATION = 'report_generation', _('Report Generation')
    ALERT_TRIGGERING = 'alert_triggering', _('Alert Triggering')
    MONITORING_JOB_SCHEDULING = 'monitoring_job_scheduling', _('Monitoring Job Scheduling')
    SYSTEM_HEALTH_CHECK = 'system_health_check', _('System Health Check')
    DATA_VALIDATION = 'data_validation', _('Data Validation')
    GIS_SERVICE_INTERACTION = 'gis_service_interaction', _('GIS Service Interaction')
    AUTHENTICATION = 'authentication', _('Authentication')
    AUTHORIZATION = 'authorization', _('Authorization')
    ERROR_HANDLING = 'error_handling', _('Error Handling')
    PERFORMANCE_MONITORING = 'performance_monitoring', _('Performance Monitoring')


class AuditEventSeverity(models.TextChoices):
    """Niveles de severidad de eventos de auditoría"""
    LOW = 'low', _('Low')
    MEDIUM = 'medium', _('Medium')
    HIGH = 'high', _('High')
    CRITICAL = 'critical', _('Critical')


class AuditEventStatus(models.TextChoices):
    """Estados de eventos de auditoría"""
    PENDING = 'pending', _('Pending')
    PROCESSING = 'processing', _('Processing')
    COMPLETED = 'completed', _('Completed')
    FAILED = 'failed', _('Failed')
    CANCELLED = 'cancelled', _('Cancelled')


class DataClassification(models.TextChoices):
    """Clasificación de datos"""
    PUBLIC = 'public', _('Public')
    INTERNAL = 'internal', _('Internal')
    CONFIDENTIAL = 'confidential', _('Confidential')
    SECRET = 'secret', _('Secret')


class AuditLog(BaseModel):
    """
    Modelo principal para registrar eventos de auditoría
    """
    # Event identification
    event_id = models.CharField(
        _('Event ID'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('Unique identifier for this audit event')
    )
    
    # Event classification
    event_type = models.CharField(
        _('Event Type'),
        max_length=30,
        choices=AuditEventType.choices,
        default=AuditEventType.USER_ACTION,
        db_index=True
    )
    severity = models.CharField(
        _('Severity'),
        max_length=10,
        choices=AuditEventSeverity.choices,
        default=AuditEventSeverity.MEDIUM,
        db_index=True
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=AuditEventStatus.choices,
        default=AuditEventStatus.COMPLETED,
        db_index=True
    )
    
    # Actor information
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        db_index=True
    )
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True, db_index=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    # Resource information
    resource_type = models.CharField(_('Resource Type'), max_length=100, blank=True, db_index=True)
    resource_id = models.CharField(_('Resource ID'), max_length=255, blank=True, db_index=True)
    
    # Action details
    action = models.CharField(_('Action'), max_length=50, db_index=True)
    description = models.TextField(_('Description'), blank=True)
    details = models.JSONField(
        _('Details'),
        default=dict,
        blank=True,
        help_text=_('Additional details about the event')
    )
    
    # Timing
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True, db_index=True)
    duration_ms = models.PositiveIntegerField(_('Duration (ms)'), default=0)
    
    # Outcome
    success = models.BooleanField(_('Success'), default=True, db_index=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    
    # Metadata
    metadata = models.JSONField(
        _('Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional metadata about the event')
    )
    tags = ArrayField(
        models.CharField(max_length=50),
        size=10,
        default=list,
        blank=True,
        verbose_name=_('Tags')
    )
    
    # Relationships
    related_events = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='parent_events',
        verbose_name=_('Related Events')
    )
    parent_event = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_events',
        verbose_name=_('Parent Event')
    )
    
    # External references
    external_reference_id = models.CharField(
        _('External Reference ID'),
        max_length=255,
        blank=True,
        help_text=_('Reference ID from external system')
    )
    external_system = models.CharField(
        _('External System'),
        max_length=100,
        blank=True,
        help_text=_('Name of the external system that generated the event')
    )
    
    # Archiving
    is_archived = models.BooleanField(_('Is Archived'), default=False, db_index=True)
    archived_at = models.DateTimeField(_('Archived At'), blank=True, null=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_audit_logs',
        verbose_name=_('Archived By')
    )
    
    # Retention and classification
    retention_policy = models.CharField(
        _('Retention Policy'),
        max_length=100,
        blank=True,
        help_text=_('Policy governing how long this log is retained')
    )
    data_classification = models.CharField(
        _('Data Classification'),
        max_length=20,
        choices=DataClassification.choices,
        default=DataClassification.INTERNAL,
        db_index=True
    )
    
    class Meta:
        db_table = 'audit_log'
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_id']),
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
            models.Index(fields=['status', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
            models.Index(fields=['is_archived', '-timestamp']),
            models.Index(fields=['archived_at']),
            models.Index(fields=['retention_policy']),
            models.Index(fields=['data_classification']),
            models.Index(fields=['created']),
            models.Index(fields=['modified']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else 'System'
        return f"[{self.get_event_type_display()}] {self.action} by {user_email} on {self.resource_type} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def actor_name(self):
        """Get the name of the actor (user or system)"""
        if self.user:
            return self.user.get_full_name() or self.user.username
        return 'System'
    
    @property
    def resource_name(self):
        """Get a human-readable name for the resource"""
        # This would ideally be dynamic based on resource_type
        # For now, we'll just return the resource_id
        return self.resource_id
    
    @property
    def event_summary(self):
        """Get a concise summary of the event"""
        return f"{self.get_event_type_display()} - {self.action} - {self.resource_type}:{self.resource_id}"
    
    def archive(self, user=None):
        """Archive this audit log"""
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            self.archived_by = user
            self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
    
    def unarchive(self):
        """Unarchive this audit log"""
        if self.is_archived:
            self.is_archived = False
            self.archived_at = None
            self.archived_by = None
            self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
    
    def add_tag(self, tag):
        """Add a tag to this audit log"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.save(update_fields=['tags'])
    
    def remove_tag(self, tag):
        """Remove a tag from this audit log"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.save(update_fields=['tags'])
    
    def get_related_events(self):
        """Get related events for this audit log"""
        return self.related_events.all()
    
    def add_related_event(self, event):
        """Add a related event to this audit log"""
        self.related_events.add(event)
    
    def remove_related_event(self, event):
        """Remove a related event from this audit log"""
        self.related_events.remove(event)
    
    def get_child_events(self):
        """Get child events for this audit log"""
        return self.child_events.all()
    
    def add_child_event(self, event):
        """Add a child event to this audit log"""
        event.parent_event = self
        event.save(update_fields=['parent_event'])
    
    def remove_child_event(self, event):
        """Remove a child event from this audit log"""
        event.parent_event = None
        event.save(update_fields=['parent_event'])


class AuditTrail(BaseModel):
    """
    Modelo para rastrear cambios en modelos específicos
    """
    # Model information
    model_name = models.CharField(_('Model Name'), max_length=100, db_index=True)
    object_id = models.CharField(_('Object ID'), max_length=255, db_index=True)
    
    # Field information
    field_name = models.CharField(_('Field Name'), max_length=100, db_index=True)
    old_value = models.TextField(_('Old Value'), blank=True)
    new_value = models.TextField(_('New Value'), blank=True)
    
    # Change type
    change_type = models.CharField(
        _('Change Type'),
        max_length=20,
        choices=[
            ('CREATED', _('Created')),
            ('UPDATED', _('Updated')),
            ('DELETED', _('Deleted')),
            ('VIEWED', _('Viewed')),
        ],
        default='UPDATED',
        db_index=True
    )
    
    # Actor information
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_trails',
        db_index=True
    )
    timestamp = models.DateTimeField(_('Timestamp'), auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True, db_index=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    # Session and request information
    session_key = models.CharField(_('Session Key'), max_length=255, blank=True, db_index=True)
    request_id = models.CharField(_('Request ID'), max_length=255, blank=True, db_index=True)
    correlation_id = models.CharField(_('Correlation ID'), max_length=255, blank=True, db_index=True)
    
    # Archiving
    is_archived = models.BooleanField(_('Is Archived'), default=False, db_index=True)
    archived_at = models.DateTimeField(_('Archived At'), blank=True, null=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_audit_trails',
        verbose_name=_('Archived By')
    )
    
    # Retention and classification
    retention_policy = models.CharField(
        _('Retention Policy'),
        max_length=100,
        blank=True,
        help_text=_('Policy governing how long this trail is retained')
    )
    data_classification = models.CharField(
        _('Data Classification'),
        max_length=20,
        choices=DataClassification.choices,
        default=DataClassification.INTERNAL,
        db_index=True
    )
    
    class Meta:
        db_table = 'audit_trail'
        verbose_name = _('Audit Trail')
        verbose_name_plural = _('Audit Trails')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['field_name']),
            models.Index(fields=['change_type', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['session_key']),
            models.Index(fields=['request_id']),
            models.Index(fields=['correlation_id']),
            models.Index(fields=['is_archived', '-timestamp']),
            models.Index(fields=['archived_at']),
            models.Index(fields=['retention_policy']),
            models.Index(fields=['data_classification']),
            models.Index(fields=['created']),
            models.Index(fields=['modified']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else 'System'
        return f"{self.model_name} #{self.object_id} - {self.field_name} - {self.get_change_type_display()} by {user_email} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def actor_name(self):
        """Get the name of the actor (user or system)"""
        if self.user:
            return self.user.get_full_name() or self.user.username
        return 'System'
    
    @property
    def change_summary(self):
        """Get a concise summary of the change"""
        return f"{self.model_name} #{self.object_id} - {self.field_name} - {self.get_change_type_display()}"
    
    def archive(self, user=None):
        """Archive this audit trail"""
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            self.archived_by = user
            self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
    
    def unarchive(self):
        """Unarchive this audit trail"""
        if self.is_archived:
            self.is_archived = False
            self.archived_at = None
            self.archived_by = None
            self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])


class AuditPolicy(BaseModel):
    """
    Modelo para definir políticas de auditoría
    """
    # Policy identification
    name = models.CharField(_('Policy Name'), max_length=200, unique=True)
    description = models.TextField(_('Description'), blank=True)
    
    # Activation
    is_active = models.BooleanField(_('Is Active'), default=True, db_index=True)
    
    # Scope
    resource_types = ArrayField(
        models.CharField(max_length=100),
        size=20,
        default=list,
        blank=True,
        verbose_name=_('Resource Types')
    )
    event_types = ArrayField(
        models.CharField(max_length=30, choices=AuditEventType.choices),
        size=20,
        default=list,
        blank=True,
        verbose_name=_('Event Types')
    )
    severity_levels = ArrayField(
        models.CharField(max_length=10, choices=AuditEventSeverity.choices),
        size=10,
        default=list,
        blank=True,
        verbose_name=_('Severity Levels')
    )
    actions = ArrayField(
        models.CharField(max_length=50),
        size=20,
        default=list,
        blank=True,
        verbose_name=_('Actions')
    )
    users = models.ManyToManyField(
        User,
        related_name='audit_policies',
        blank=True,
        verbose_name=_('Users')
    )
    ip_addresses = ArrayField(
        models.GenericIPAddressField(),
        size=20,
        default=list,
        blank=True,
        verbose_name=_('IP Addresses')
    )
    user_agents = ArrayField(
        models.CharField(max_length=255),
        size=20,
        default=list,
        blank=True,
        verbose_name=_('User Agents')
    )
    
    # Retention
    retention_days = models.PositiveIntegerField(
        _('Retention Days'),
        default=90,
        validators=[MinValueValidator(1), MaxValueValidator(3650)], # 1 day to 10 years
        help_text=_('Number of days to retain audit logs')
    )
    archive_after_days = models.PositiveIntegerField(
        _('Archive After Days'),
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(3650)],
        help_text=_('Number of days after which to archive audit logs')
    )
    
    # Notification
    notify_on_events = models.BooleanField(_('Notify on Events'), default=False)
    notification_channels = ArrayField(
        models.CharField(max_length=20, choices=[
            ('email', _('Email')),
            ('sms', _('SMS')),
            ('push', _('Push Notification')),
            ('webhook', _('Webhook')),
            ('in_app', _('In-App Notification')),
        ]),
        size=10,
        default=list,
        blank=True,
        verbose_name=_('Notification Channels')
    )
    notification_recipients = models.ManyToManyField(
        User,
        related_name='audit_policy_notifications',
        blank=True,
        verbose_name=_('Notification Recipients')
    )
    
    # User management
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_audit_policies'
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_audit_policies'
    )
    
    class Meta:
        db_table = 'audit_policy'
        verbose_name = _('Audit Policy')
        verbose_name_plural = _('Audit Policies')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['retention_days']),
            models.Index(fields=['archive_after_days']),
            models.Index(fields=['notify_on_events']),
            models.Index(fields=['created_by']),
            models.Index(fields=['modified_by']),
            models.Index(fields=['created']),
            models.Index(fields=['modified']),
        ]
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    
    @property
    def resource_count(self):
        """Get total number of resources covered by this policy"""
        return len(self.resource_types)
    
    @property
    def user_count(self):
        """Get total number of users covered by this policy"""
        return self.users.count()
    
    @property
    def ip_address_count(self):
        """Get total number of IP addresses covered by this policy"""
        return len(self.ip_addresses)
    
    @property
    def user_agent_count(self):
        """Get total number of user agents covered by this policy"""
        return len(self.user_agents)
    
    def should_audit(self, event_type, severity, action, user=None, ip_address=None, user_agent=None):
        """
        Check if an event should be audited based on this policy
        
        Args:
            event_type (str): Type of the event (AuditEventType)
            severity (str): Severity of the event (AuditEventSeverity)
            action (str): Action performed
            user (User): User who performed the action
            ip_address (str): IP address of the user
            user_agent (str): User agent of the client
            
        Returns:
            bool: True if the event should be audited, False otherwise
        """
        # Check if policy is active
        if not self.is_active:
            return False
        
        # Check event type
        if self.event_types and event_type not in self.event_types:
            return False
        
        # Check severity
        if self.severity_levels and severity not in self.severity_levels:
            return False
        
        # Check action
        if self.actions and action not in self.actions:
            return False
        
        # Check user
        if self.users.exists() and user and not self.users.filter(id=user.id).exists():
            return False
        
        # Check IP address
        if self.ip_addresses and ip_address and ip_address not in self.ip_addresses:
            return False
        
        # Check user agent
        if self.user_agents and user_agent and user_agent not in self.user_agents:
            return False
        
        # All checks passed
        return True
    
    def get_notification_recipients(self):
        """Get notification recipients for this policy"""
        return self.notification_recipients.all()
    
    def add_notification_recipient(self, user):
        """Add a notification recipient to this policy"""
        self.notification_recipients.add(user)
    
    def remove_notification_recipient(self, user):
        """Remove a notification recipient from this policy"""
        self.notification_recipients.remove(user)
    
    def get_users(self):
        """Get users covered by this policy"""
        return self.users.all()
    
    def add_user(self, user):
        """Add a user to this policy"""
        self.users.add(user)
    
    def remove_user(self, user):
        """Remove a user from this policy"""
        self.users.remove(user)


class AuditConfiguration(BaseModel):
    """
    Modelo para configurar el sistema de auditoría
    """
    # Configuration identification
    name = models.CharField(_('Configuration Name'), max_length=200, unique=True)
    description = models.TextField(_('Description'), blank=True)
    
    # Activation
    is_active = models.BooleanField(_('Is Active'), default=True, db_index=True)
    
    # Retention
    default_retention_days = models.PositiveIntegerField(
        _('Default Retention Days'),
        default=90,
        validators=[MinValueValidator(1), MaxValueValidator(3650)], # 1 day to 10 years
        help_text=_('Default number of days to retain audit logs')
    )
    default_archive_after_days = models.PositiveIntegerField(
        _('Default Archive After Days'),
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(3650)],
        help_text=_('Default number of days after which to archive audit logs')
    )
    default_data_classification = models.CharField(
        _('Default Data Classification'),
        max_length=20,
        choices=DataClassification.choices,
        default=DataClassification.INTERNAL,
        db_index=True
    )
    
    # Logging
    enable_real_time_logging = models.BooleanField(_('Enable Real-Time Logging'), default=True)
    enable_batch_logging = models.BooleanField(_('Enable Batch Logging'), default=False)
    batch_size = models.PositiveIntegerField(
        _('Batch Size'),
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        help_text=_('Number of logs to batch before writing to database')
    )
    
    # Log level
    log_level = models.CharField(
        _('Log Level'),
        max_length=10,
        choices=[
            ('DEBUG', _('Debug')),
            ('INFO', _('Info')),
            ('WARNING', _('Warning')),
            ('ERROR', _('Error')),
            ('CRITICAL', _('Critical')),
        ],
        default='INFO',
        db_index=True
    )
    
    # Sensitive data handling
    exclude_sensitive_fields = ArrayField(
        models.CharField(max_length=100),
        size=50,
        default=list,
        blank=True,
        verbose_name=_('Exclude Sensitive Fields')
    )
    mask_sensitive_data = models.BooleanField(_('Mask Sensitive Data'), default=True)
    encrypt_audit_logs = models.BooleanField(_('Encrypt Audit Logs'), default=False)
    
    # Storage options
    store_audit_trails = models.BooleanField(_('Store Audit Trails'), default=True)
    store_user_sessions = models.BooleanField(_('Store User Sessions'), default=True)
    store_api_calls = models.BooleanField(_('Store API Calls'), default=True)
    store_external_api_calls = models.BooleanField(_('Store External API Calls'), default=True)
    store_internal_api_calls = models.BooleanField(_('Store Internal API Calls'), default=True)
    store_database_queries = models.BooleanField(_('Store Database Queries'), default=True)
    store_cache_operations = models.BooleanField(_('Store Cache Operations'), default=True)
    store_file_operations = models.BooleanField(_('Store File Operations'), default=True)
    store_email_sending = models.BooleanField(_('Store Email Sending'), default=True)
    store_sms_sending = models.BooleanField(_('Store SMS Sending'), default=True)
    store_webhook_sending = models.BooleanField(_('Store Webhook Sending'), default=True)
    store_push_notification_sending = models.BooleanField(_('Store Push Notification Sending'), default=True)
    store_report_generation = models.BooleanField(_('Store Report Generation'), default=True)
    store_alert_triggering = models.BooleanField(_('Store Alert Triggering'), default=True)
    store_monitoring_job_scheduling = models.BooleanField(_('Store Monitoring Job Scheduling'), default=True)
    store_system_health_checks = models.BooleanField(_('Store System Health Checks'), default=True)
    store_data_validation = models.BooleanField(_('Store Data Validation'), default=True)
    store_gis_service_interaction = models.BooleanField(_('Store GIS Service Interaction'), default=True)
    store_authentication = models.BooleanField(_('Store Authentication'), default=True)
    store_authorization = models.BooleanField(_('Store Authorization'), default=True)
    store_error_handling = models.BooleanField(_('Store Error Handling'), default=True)
    store_performance_monitoring = models.BooleanField(_('Store Performance Monitoring'), default=True)
    
    # User management
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_audit_configurations'
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_audit_configurations'
    )
    
    class Meta:
        db_table = 'audit_configuration'
        verbose_name = _('Audit Configuration')
        verbose_name_plural = _('Audit Configurations')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['default_retention_days']),
            models.Index(fields=['default_archive_after_days']),
            models.Index(fields=['default_data_classification']),
            models.Index(fields=['enable_real_time_logging']),
            models.Index(fields=['enable_batch_logging']),
            models.Index(fields=['log_level']),
            models.Index(fields=['encrypt_audit_logs']),
            models.Index(fields=['created_by']),
            models.Index(fields=['modified_by']),
            models.Index(fields=['created']),
            models.Index(fields=['modified']),
        ]
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    
    @property
    def total_storage_options_enabled(self):
        """Get total number of storage options enabled"""
        storage_options = [
            self.store_audit_trails, self.store_user_sessions, self.store_api_calls,
            self.store_external_api_calls, self.store_internal_api_calls,
            self.store_database_queries, self.store_cache_operations,
            self.store_file_operations, self.store_email_sending,
            self.store_sms_sending, self.store_webhook_sending,
            self.store_push_notification_sending, self.store_report_generation,
            self.store_alert_triggering, self.store_monitoring_job_scheduling,
            self.store_system_health_checks, self.store_data_validation,
            self.store_gis_service_interaction, self.store_authentication,
            self.store_authorization, self.store_error_handling,
            self.store_performance_monitoring
        ]
        return sum(storage_options)
    
    @property
    def total_sensitive_fields_excluded(self):
        """Get total number of sensitive fields excluded"""
        return len(self.exclude_sensitive_fields)
    
    def should_store_event(self, event_type):
        """
        Check if an event type should be stored based on configuration
        
        Args:
            event_type (str): Type of the event (AuditEventType)
            
        Returns:
            bool: True if the event should be stored, False otherwise
        """
        # Map event types to storage options
        storage_map = {
            AuditEventType.USER_ACTION: self.store_audit_trails,
            AuditEventType.DATA_CHANGE: self.store_audit_trails,
            AuditEventType.SECURITY_EVENT: self.store_authentication or self.store_authorization,
            AuditEventType.SYSTEM_EVENT: self.store_system_health_checks,
            AuditEventType.API_CALL: self.store_api_calls,
            AuditEventType.EXTERNAL_API_CALL: self.store_external_api_calls,
            AuditEventType.INTERNAL_API_CALL: self.store_internal_api_calls,
            AuditEventType.DATABASE_QUERY: self.store_database_queries,
            AuditEventType.CACHE_OPERATION: self.store_cache_operations,
            AuditEventType.FILE_OPERATION: self.store_file_operations,
            AuditEventType.EMAIL_SENDING: self.store_email_sending,
            AuditEventType.SMS_SENDING: self.store_sms_sending,
            AuditEventType.WEBHOOK_SENDING: self.store_webhook_sending,
            AuditEventType.PUSH_NOTIFICATION_SENDING: self.store_push_notification_sending,
            AuditEventType.REPORT_GENERATION: self.store_report_generation,
            AuditEventType.ALERT_TRIGGERING: self.store_alert_triggering,
            AuditEventType.MONITORING_JOB_SCHEDULING: self.store_monitoring_job_scheduling,
            AuditEventType.SYSTEM_HEALTH_CHECK: self.store_system_health_checks,
            AuditEventType.DATA_VALIDATION: self.store_data_validation,
            AuditEventType.GIS_SERVICE_INTERACTION: self.store_gis_service_interaction,
            AuditEventType.AUTHENTICATION: self.store_authentication,
            AuditEventType.AUTHORIZATION: self.store_authorization,
            AuditEventType.ERROR_HANDLING: self.store_error_handling,
            AuditEventType.PERFORMANCE_MONITORING: self.store_performance_monitoring,
        }
        
        return storage_map.get(event_type, False)
    
    def should_exclude_field(self, field_name):
        """
        Check if a field should be excluded from logging
        
        Args:
            field_name (str): Name of the field
            
        Returns:
            bool: True if the field should be excluded, False otherwise
        """
        return field_name in self.exclude_sensitive_fields
    
    def should_mask_data(self):
        """
        Check if sensitive data should be masked
        
        Returns:
            bool: True if data should be masked, False otherwise
        """
        return self.mask_sensitive_data
    
    def should_encrypt_logs(self):
        """
        Check if audit logs should be encrypted
        
        Returns:
            bool: True if logs should be encrypted, False otherwise
        """
        return self.encrypt_audit_logs
