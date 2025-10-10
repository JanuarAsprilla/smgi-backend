"""
SMGI Backend - GIS Services Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos para servicios geoespaciales y capas espaciales
"""
import uuid
import json
from django.contrib.gis.db import models
from django.contrib.gis.geos import Polygon
from django.core.validators import URLValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel, SoftDeletableModel
from apps.common.models import BaseModel
from apps.authentication.models import User


class ServiceStatus(models.TextChoices):
    """Service status choices"""
    ACTIVE = 'active', _('Active')
    INACTIVE = 'inactive', _('Inactive')
    ERROR = 'error', _('Error')
    MAINTENANCE = 'maintenance', _('Maintenance')
    UNKNOWN = 'unknown', _('Unknown')


class ServiceType(models.TextChoices):
    """Service type choices"""
    MAP_SERVER = 'mapserver', _('Map Server')
    FEATURE_SERVER = 'featureserver', _('Feature Server')
    IMAGE_SERVER = 'imageserver', _('Image Server')
    GEOCODE_SERVER = 'geocodeserver', _('Geocode Server')
    GEOMETRY_SERVER = 'geometryserver', _('Geometry Server')
    GEOPROCESSING_SERVER = 'gpserver', _('Geoprocessing Server')
    WMS = 'wms', _('Web Map Service (WMS)')
    WFS = 'wfs', _('Web Feature Service (WFS)')
    WCS = 'wcs', _('Web Coverage Service (WCS)')
    WMTS = 'wmts', _('Web Map Tile Service (WMTS)')


class ArcGISService(BaseModel):
    """
    Model to represent ArcGIS services and other GIS services
    """
    name = models.CharField(_('Service Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    
    # Service connection details
    base_url = models.URLField(
        _('Base URL'),
        validators=[URLValidator()],
        help_text=_('Base URL of the ArcGIS service')
    )
    service_type = models.CharField(
        _('Service Type'),
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.MAP_SERVER
    )
    
    # Authentication and access
    requires_authentication = models.BooleanField(_('Requires Authentication'), default=False)
    username = models.CharField(_('Username'), max_length=100, blank=True)
    password = models.CharField(_('Password'), max_length=255, blank=True)  # Should be encrypted
    token = models.TextField(_('Access Token'), blank=True)
    token_expires = models.DateTimeField(_('Token Expires'), blank=True, null=True)
    
    # Service configuration
    timeout_seconds = models.PositiveIntegerField(
        _('Timeout (seconds)'),
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(300)]
    )
    max_record_count = models.PositiveIntegerField(
        _('Max Record Count'),
        default=1000,
        help_text=_('Maximum number of records to fetch per request')
    )
    
    # Monitoring settings
    is_monitored = models.BooleanField(_('Is Monitored'), default=True)
    monitoring_interval = models.PositiveIntegerField(
        _('Monitoring Interval (minutes)'),
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(1440)]
    )
    
    # Service metadata
    version = models.CharField(_('Service Version'), max_length=20, blank=True)
    capabilities = models.JSONField(
        _('Service Capabilities'),
        default=dict,
        blank=True,
        help_text=_('JSON object containing service capabilities')
    )
    metadata = models.JSONField(
        _('Service Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional metadata about the service')
    )
    
    # Status tracking
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=ServiceStatus.choices,
        default=ServiceStatus.UNKNOWN
    )
    last_check = models.DateTimeField(_('Last Check'), blank=True, null=True)
    last_successful_check = models.DateTimeField(_('Last Successful Check'), blank=True, null=True)
    consecutive_failures = models.PositiveIntegerField(_('Consecutive Failures'), default=0)
    
    # Geographic bounds
    extent = models.PolygonField(_('Service Extent'), blank=True, null=True, srid=4326)
    
    # User management
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_services'
    )
    
    class Meta:
        db_table = 'gis_arcgis_service'
        verbose_name = _('ArcGIS Service')
        verbose_name_plural = _('ArcGIS Services')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['service_type']),
            models.Index(fields=['status']),
            models.Index(fields=['is_monitored']),
            models.Index(fields=['last_check']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.service_type})"
    
    @property
    def is_online(self):
        """Check if service is online"""
        return self.status == ServiceStatus.ACTIVE
    
    @property
    def needs_token_refresh(self):
        """Check if token needs refresh"""
        if not self.token_expires:
            return False
        return timezone.now() >= self.token_expires
    
    def update_status(self, status, error_message=None):
        """Update service status"""
        self.status = status
        self.last_check = timezone.now()
        
        if status == ServiceStatus.ACTIVE:
            self.last_successful_check = timezone.now()
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            
        if error_message:
            self.metadata['last_error'] = {
                'message': error_message,
                'timestamp': timezone.now().isoformat()
            }
        
        self.save(update_fields=['status', 'last_check', 'last_successful_check', 
                                'consecutive_failures', 'metadata'])
    
    def get_layers(self):
        """Get all layers for this service"""
        return self.spatial_layers.filter(is_removed=False)
    
    def get_monitored_layers(self):
        """Get only monitored layers"""
        return self.spatial_layers.filter(is_monitored=True, is_removed=False)


class LayerGeometryType(models.TextChoices):
    """Geometry type choices for layers"""
    POINT = 'point', _('Point')
    MULTIPOINT = 'multipoint', _('MultiPoint')
    POLYLINE = 'polyline', _('Polyline')
    POLYGON = 'polygon', _('Polygon')
    ENVELOPE = 'envelope', _('Envelope')
    RASTER = 'raster', _('Raster')
    UNKNOWN = 'unknown', _('Unknown')


class SpatialLayer(BaseModel):
    """
    Model to represent spatial layers within ArcGIS services
    """
    service = models.ForeignKey(
        ArcGISService,
        on_delete=models.CASCADE,
        related_name='spatial_layers'
    )
    
    # Layer identification
    layer_id = models.IntegerField(_('Layer ID'), help_text=_('Layer ID within the service'))
    name = models.CharField(_('Layer Name'), max_length=200)
    display_name = models.CharField(_('Display Name'), max_length=200, blank=True)
    description = models.TextField(_('Description'), blank=True)
    
    # Layer properties
    geometry_type = models.CharField(
        _('Geometry Type'),
        max_length=20,
        choices=LayerGeometryType.choices,
        default=LayerGeometryType.UNKNOWN
    )
    min_scale = models.FloatField(_('Min Scale'), blank=True, null=True)
    max_scale = models.FloatField(_('Max Scale'), blank=True, null=True)
    
    # Geographic properties
    extent = models.PolygonField(_('Layer Extent'), blank=True, null=True, srid=4326)
    spatial_reference = models.JSONField(
        _('Spatial Reference'),
        default=dict,
        blank=True,
        help_text=_('Spatial reference system information')
    )
    
    # Layer capabilities and metadata
    supports_query = models.BooleanField(_('Supports Query'), default=True)
    supports_statistics = models.BooleanField(_('Supports Statistics'), default=False)
    can_modify_layer = models.BooleanField(_('Can Modify Layer'), default=False)
    
    fields = models.JSONField(
        _('Layer Fields'),
        default=list,
        blank=True,
        help_text=_('List of field definitions for the layer')
    )
    
    # Monitoring configuration
    is_monitored = models.BooleanField(_('Is Monitored'), default=False)
    monitoring_enabled = models.BooleanField(_('Monitoring Enabled'), default=True)
    change_detection_enabled = models.BooleanField(_('Change Detection Enabled'), default=True)
    
    # Change detection settings
    change_detection_fields = models.JSONField(
        _('Change Detection Fields'),
        default=list,
        blank=True,
        help_text=_('Fields to monitor for changes')
    )
    change_threshold = models.FloatField(
        _('Change Threshold'),
        default=0.05,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Minimum change percentage to trigger alert')
    )
    
    # Layer statistics
    feature_count = models.PositiveIntegerField(_('Feature Count'), default=0)
    last_feature_count = models.PositiveIntegerField(_('Last Feature Count'), default=0)
    last_updated = models.DateTimeField(_('Last Updated'), blank=True, null=True)
    
    # Status tracking
    last_check = models.DateTimeField(_('Last Check'), blank=True, null=True)
    last_successful_check = models.DateTimeField(_('Last Successful Check'), blank=True, null=True)
    check_failures = models.PositiveIntegerField(_('Check Failures'), default=0)
    
    # Alert configuration
    alert_on_change = models.BooleanField(_('Alert on Change'), default=True)
    alert_on_error = models.BooleanField(_('Alert on Error'), default=True)
    alert_thresholds = models.JSONField(
        _('Alert Thresholds'),
        default=dict,
        blank=True,
        help_text=_('Custom alert thresholds for this layer')
    )
    
    # User management
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_layers'
    )
    
    class Meta:
        db_table = 'gis_spatial_layer'
        verbose_name = _('Spatial Layer')
        verbose_name_plural = _('Spatial Layers')
        ordering = ['service__name', 'layer_id']
        unique_together = ['service', 'layer_id']
        indexes = [
            models.Index(fields=['service', 'layer_id']),
            models.Index(fields=['name']),
            models.Index(fields=['geometry_type']),
            models.Index(fields=['is_monitored']),
            models.Index(fields=['monitoring_enabled']),
            models.Index(fields=['last_check']),
            models.Index(fields=['feature_count']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.name} (ID: {self.layer_id})"
    
    @property
    def full_name(self):
        """Get full layer name including service"""
        return f"{self.service.name}/{self.name}"
    
    @property
    def should_be_monitored(self):
        """Check if layer should be monitored"""
        return (self.is_monitored and 
                self.monitoring_enabled and 
                self.service.is_monitored and
                self.service.status == ServiceStatus.ACTIVE)
    
    @property
    def change_percentage(self):
        """Calculate change percentage from last count"""
        if self.last_feature_count == 0:
            return 0.0 if self.feature_count == 0 else 100.0
        
        return abs(self.feature_count - self.last_feature_count) / self.last_feature_count * 100
    
    @property
    def has_significant_change(self):
        """Check if layer has significant change"""
        return self.change_percentage >= (self.change_threshold * 100)
    
    def update_feature_count(self, new_count):
        """Update feature count and check for changes"""
        old_count = self.feature_count
        self.last_feature_count = old_count
        self.feature_count = new_count
        self.last_check = timezone.now()
        self.last_successful_check = timezone.now()
        self.check_failures = 0
        
        # Check for significant changes
        if self.has_significant_change and self.alert_on_change:
            # Trigger change detection alert
            from apps.alerts.tasks import create_change_detection_alert
            create_change_detection_alert.delay(
                layer_id=self.id,
                old_count=old_count,
                new_count=new_count,
                change_percentage=self.change_percentage
            )
        
        self.save(update_fields=[
            'feature_count', 'last_feature_count', 'last_check', 
            'last_successful_check', 'check_failures'
        ])
    
    def record_check_failure(self, error_message=None):
        """Record a failed check"""
        self.check_failures += 1
        self.last_check = timezone.now()
        
        # Store error in metadata if provided
        if error_message and hasattr(self, 'metadata'):
            if not isinstance(self.metadata, dict):
                self.metadata = {}
            self.metadata['last_error'] = {
                'message': error_message,
                'timestamp': timezone.now().isoformat()
            }
        
        # Trigger error alert if enabled
        if self.alert_on_error and self.check_failures >= 3:
            from apps.alerts.tasks import create_layer_error_alert
            create_layer_error_alert.delay(
                layer_id=self.id,
                error_message=error_message,
                consecutive_failures=self.check_failures
            )
        
        self.save(update_fields=['check_failures', 'last_check'])
    
    def get_latest_snapshot(self):
        """Get the most recent snapshot for this layer"""
        return self.snapshots.order_by('-created').first()
    
    def get_snapshots_in_range(self, start_date, end_date):
        """Get snapshots within date range"""
        return self.snapshots.filter(
            created__range=[start_date, end_date]
        ).order_by('-created')


class LayerField(models.Model):
    """
    Model to represent fields in a spatial layer
    """
    layer = models.ForeignKey(
        SpatialLayer,
        on_delete=models.CASCADE,
        related_name='layer_fields'
    )
    
    name = models.CharField(_('Field Name'), max_length=100)
    alias = models.CharField(_('Field Alias'), max_length=200, blank=True)
    field_type = models.CharField(_('Field Type'), max_length=50)
    length = models.PositiveIntegerField(_('Field Length'), blank=True, null=True)
    is_nullable = models.BooleanField(_('Is Nullable'), default=True)
    default_value = models.TextField(_('Default Value'), blank=True)
    
    # Monitoring configuration for this field
    monitor_for_changes = models.BooleanField(_('Monitor for Changes'), default=False)
    change_threshold = models.FloatField(
        _('Change Threshold'),
        blank=True,
        null=True,
        validators=[MinValueValidator(0.0)]
    )
    
    class Meta:
        db_table = 'gis_layer_field'
        verbose_name = _('Layer Field')
        verbose_name_plural = _('Layer Fields')
        unique_together = ['layer', 'name']
        indexes = [
            models.Index(fields=['layer', 'name']),
            models.Index(fields=['field_type']),
            models.Index(fields=['monitor_for_changes']),
        ]
    
    def __str__(self):
        return f"{self.layer.name}.{self.name} ({self.field_type})"


class ServiceEndpoint(BaseModel):
    """
    Model to represent different endpoints of a service
    """
    service = models.ForeignKey(
        ArcGISService,
        on_delete=models.CASCADE,
        related_name='endpoints'
    )
    
    name = models.CharField(_('Endpoint Name'), max_length=100)
    path = models.CharField(_('Endpoint Path'), max_length=500)
    method = models.CharField(
        _('HTTP Method'),
        max_length=10,
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('DELETE', 'DELETE'),
        ],
        default='GET'
    )
    
    # Endpoint configuration
    parameters = models.JSONField(
        _('Default Parameters'),
        default=dict,
        blank=True,
        help_text=_('Default parameters for this endpoint')
    )
    
    # Monitoring
    is_monitored = models.BooleanField(_('Is Monitored'), default=False)
    timeout_seconds = models.PositiveIntegerField(_('Timeout (seconds)'), default=30)
    
    # Status tracking
    last_response_time = models.FloatField(_('Last Response Time (ms)'), blank=True, null=True)
    last_status_code = models.PositiveIntegerField(_('Last Status Code'), blank=True, null=True)
    last_check = models.DateTimeField(_('Last Check'), blank=True, null=True)
    
    class Meta:
        db_table = 'gis_service_endpoint'
        verbose_name = _('Service Endpoint')
        verbose_name_plural = _('Service Endpoints')
        unique_together = ['service', 'name']
        indexes = [
            models.Index(fields=['service', 'name']),
            models.Index(fields=['method']),
            models.Index(fields=['is_monitored']),
            models.Index(fields=['last_check']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.name}"
    
    @property
    def full_url(self):
        """Get the full URL for this endpoint"""
        base_url = self.service.base_url.rstrip('/')
        path = self.path.lstrip('/')
        return f"{base_url}/{path}"
    
    def update_response_metrics(self, response_time_ms, status_code):
        """Update response metrics"""
        self.last_response_time = response_time_ms
        self.last_status_code = status_code
        self.last_check = timezone.now()
        self.save(update_fields=['last_response_time', 'last_status_code', 'last_check'])


class ServiceCredential(TimeStampedModel):
    """
    Model to securely store service credentials
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.OneToOneField(
        ArcGISService,
        on_delete=models.CASCADE,
        related_name='credentials'
    )
    
    # Authentication details (should be encrypted in production)
    username = models.CharField(_('Username'), max_length=255, blank=True)
    password = models.TextField(_('Encrypted Password'), blank=True)
    api_key = models.TextField(_('API Key'), blank=True)
    client_id = models.CharField(_('Client ID'), max_length=255, blank=True)
    client_secret = models.TextField(_('Client Secret'), blank=True)
    
    # OAuth details
    access_token = models.TextField(_('Access Token'), blank=True)
    refresh_token = models.TextField(_('Refresh Token'), blank=True)
    token_type = models.CharField(_('Token Type'), max_length=50, default='Bearer')
    expires_in = models.PositiveIntegerField(_('Expires In (seconds)'), blank=True, null=True)
    token_created_at = models.DateTimeField(_('Token Created At'), blank=True, null=True)
    
    # Additional configuration
    auth_url = models.URLField(_('Authentication URL'), blank=True)
    token_url = models.URLField(_('Token URL'), blank=True)
    
    class Meta:
        db_table = 'gis_service_credential'
        verbose_name = _('Service Credential')
        verbose_name_plural = _('Service Credentials')
    
    def __str__(self):
        return f"Credentials for {self.service.name}"
    
    @property
    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_created_at or not self.expires_in:
            return True
        
        expiry_time = self.token_created_at + timezone.timedelta(seconds=self.expires_in)
        return timezone.now() >= expiry_time
    
    def needs_refresh(self):
        """Check if token needs refresh (5 minutes before expiry)"""
        if not self.token_created_at or not self.expires_in:
            return True
        
        buffer_time = timezone.timedelta(minutes=5)
        expiry_time = self.token_created_at + timezone.timedelta(seconds=self.expires_in)
        return timezone.now() >= (expiry_time - buffer_time)


class ServiceConfiguration(BaseModel):
    """
    Model to store additional service configurations
    """
    service = models.OneToOneField(
        ArcGISService,
        on_delete=models.CASCADE,
        related_name='configuration'
    )
    
    # Request configuration
    headers = models.JSONField(
        _('Custom Headers'),
        default=dict,
        blank=True,
        help_text=_('Custom headers to include in requests')
    )
    query_parameters = models.JSONField(
        _('Default Query Parameters'),
        default=dict,
        blank=True,
        help_text=_('Default query parameters for requests')
    )
    
    # Retry configuration
    max_retries = models.PositiveIntegerField(_('Max Retries'), default=3)
    retry_delay = models.PositiveIntegerField(_('Retry Delay (seconds)'), default=1)
    backoff_factor = models.FloatField(_('Backoff Factor'), default=2.0)
    
    # Cache configuration
    cache_responses = models.BooleanField(_('Cache Responses'), default=True)
    cache_duration = models.PositiveIntegerField(
        _('Cache Duration (seconds)'),
        default=300  # 5 minutes
    )
    
    # Rate limiting
    requests_per_minute = models.PositiveIntegerField(
        _('Requests per Minute'),
        default=60,
        help_text=_('Maximum requests per minute to this service')
    )
    
    # Data processing options
    data_format = models.CharField(
        _('Preferred Data Format'),
        max_length=20,
        choices=[
            ('json', 'JSON'),
            ('geojson', 'GeoJSON'),
            ('xml', 'XML'),
            ('csv', 'CSV'),
        ],
        default='json'
    )
    
    # Monitoring configuration
    health_check_interval = models.PositiveIntegerField(
        _('Health Check Interval (minutes)'),
        default=5
    )
    performance_monitoring = models.BooleanField(
        _('Performance Monitoring'),
        default=True
    )
    
    # Notification settings
    notification_settings = models.JSONField(
        _('Notification Settings'),
        default=dict,
        blank=True,
        help_text=_('Service-specific notification preferences')
    )
    
    class Meta:
        db_table = 'gis_service_configuration'
        verbose_name = _('Service Configuration')
        verbose_name_plural = _('Service Configurations')
    
    def __str__(self):
        return f"Configuration for {self.service.name}"
    
    def get_notification_setting(self, setting_name, default=None):
        """Get a specific notification setting"""
        return self.notification_settings.get(setting_name, default)
    
    def should_send_notification(self, notification_type):
        """Check if notification should be sent for given type"""
        return self.notification_settings.get(f'send_{notification_type}', True)


class ServiceTag(BaseModel):
    """
    Model for tagging services for better organization
    """
    name = models.CharField(_('Tag Name'), max_length=50, unique=True)
    color = models.CharField(
        _('Tag Color'),
        max_length=7,
        default='#007bff',
        help_text=_('Hex color code for the tag')
    )
    description = models.TextField(_('Description'), blank=True)
    
    class Meta:
        db_table = 'gis_service_tag'
        verbose_name = _('Service Tag')
        verbose_name_plural = _('Service Tags')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ServiceTagRelation(models.Model):
    """
    Through model for many-to-many relationship between services and tags
    """
    service = models.ForeignKey(ArcGISService, on_delete=models.CASCADE)
    tag = models.ForeignKey(ServiceTag, on_delete=models.CASCADE)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gis_service_tag_relation'
        unique_together = ['service', 'tag']
        verbose_name = _('Service Tag Relation')
        verbose_name_plural = _('Service Tag Relations')
    
    def __str__(self):
        return f"{self.service.name} - {self.tag.name}"


# Add many-to-many relationship to ArcGISService
ArcGISService.add_to_class(
    'tags',
    models.ManyToManyField(
        ServiceTag,
        through=ServiceTagRelation,
        related_name='services',
        blank=True
    )
)


class ServiceMetrics(TimeStampedModel):
    """
    Model to store service performance metrics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        ArcGISService,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    
    # Performance metrics
    response_time_ms = models.FloatField(_('Response Time (ms)'))
    status_code = models.PositiveIntegerField(_('HTTP Status Code'))
    success = models.BooleanField(_('Request Success'))
    
    # Request details
    endpoint = models.CharField(_('Endpoint'), max_length=500, blank=True)
    method = models.CharField(_('HTTP Method'), max_length=10, default='GET')
    request_size_bytes = models.PositiveIntegerField(_('Request Size (bytes)'), blank=True, null=True)
    response_size_bytes = models.PositiveIntegerField(_('Response Size (bytes)'), blank=True, null=True)
    
    # Error information
    error_message = models.TextField(_('Error Message'), blank=True)
    error_type = models.CharField(_('Error Type'), max_length=100, blank=True)
    
    # Additional context
    user_agent = models.CharField(_('User Agent'), max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True)
    
    class Meta:
        db_table = 'gis_service_metrics'
        verbose_name = _('Service Metrics')
        verbose_name_plural = _('Service Metrics')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['service', '-created']),
            models.Index(fields=['success']),
            models.Index(fields=['status_code']),
            models.Index(fields=['response_time_ms']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else f"Failed ({self.status_code})"
        return f"{self.service.name} - {status} - {self.response_time_ms}ms"
    
    @classmethod
    def record_request(cls, service, endpoint=None, method='GET', 
                      response_time_ms=None, status_code=None, 
                      success=True, error_message=None, **kwargs):
        """
        Convenience method to record a service request
        """
        return cls.objects.create(
            service=service,
            endpoint=endpoint or '',
            method=method,
            response_time_ms=response_time_ms or 0,
            status_code=status_code or 200,
            success=success,
            error_message=error_message or '',
            **kwargs
        )
    
    @classmethod
    def get_average_response_time(cls, service, hours=24):
        """
        Get average response time for a service in the last N hours
        """
        from django.db.models import Avg
        from django.utils import timezone
        
        since = timezone.now() - timezone.timedelta(hours=hours)
        result = cls.objects.filter(
            service=service,
            success=True,
            created__gte=since
        ).aggregate(avg_response_time=Avg('response_time_ms'))
        
        return result['avg_response_time'] or 0
    
    @classmethod
    def get_success_rate(cls, service, hours=24):
        """
        Get success rate for a service in the last N hours
        """
        from django.db.models import Count, Case, When, FloatField
        from django.utils import timezone
        
        since = timezone.now() - timezone.timedelta(hours=hours)
        result = cls.objects.filter(
            service=service,
            created__gte=since
        ).aggregate(
            total=Count('id'),
            successful=Count(Case(When(success=True, then=1), output_field=FloatField()))
        )
        
        if result['total'] == 0:
            return 0.0
        
        return (result['successful'] / result['total']) * 100