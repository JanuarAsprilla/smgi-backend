"""
SMGI Backend - Monitoring Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos para monitoreo de capas y detección de cambios
"""
import uuid
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel, SoftDeletableModel
from apps.common.models import BaseModel
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer


class MonitoringStatus(models.TextChoices):
    """Monitoring status choices"""
    ACTIVE = 'active', _('Active')
    PAUSED = 'paused', _('Paused')
    STOPPED = 'stopped', _('Stopped')
    ERROR = 'error', _('Error')
    MAINTENANCE = 'maintenance', _('Maintenance')


class ChangeType(models.TextChoices):
    """Types of changes detected"""
    FEATURE_COUNT = 'feature_count', _('Feature Count Change')
    ATTRIBUTE = 'attribute', _('Attribute Change')
    GEOMETRY = 'geometry', _('Geometry Change')
    SCHEMA = 'schema', _('Schema Change')
    PERFORMANCE = 'performance', _('Performance Change')
    AVAILABILITY = 'availability', _('Availability Change')
    DATA_QUALITY = 'data_quality', _('Data Quality Change')


class ChangeDetectionAlgorithm(models.TextChoices):
    """Change detection algorithms"""
    SIMPLE_COUNT = 'simple_count', _('Simple Feature Count')
    HASH_COMPARISON = 'hash_comparison', _('Hash Comparison')
    FIELD_COMPARISON = 'field_comparison', _('Field-by-Field Comparison')
    GEOMETRIC_ANALYSIS = 'geometric_analysis', _('Geometric Analysis')
    STATISTICAL_ANALYSIS = 'statistical_analysis', _('Statistical Analysis')
    ML_ANOMALY_DETECTION = 'ml_anomaly', _('Machine Learning Anomaly Detection')


class LayerSnapshot(BaseModel):
    """
    Model to store snapshots of spatial layers for change detection
    """
    layer = models.ForeignKey(
        SpatialLayer,
        on_delete=models.CASCADE,
        related_name='snapshots'
    )
    
    # Snapshot identification
    snapshot_hash = models.CharField(
        _('Snapshot Hash'),
        max_length=64,
        db_index=True,
        help_text=_('SHA-256 hash of the snapshot data')
    )
    
    # Basic layer metrics
    feature_count = models.PositiveIntegerField(_('Feature Count'))
    total_area = models.FloatField(_('Total Area'), blank=True, null=True)
    total_length = models.FloatField(_('Total Length'), blank=True, null=True)
    
    # Geometric statistics
    extent_bounds = models.JSONField( # Considerar PolygonField si se hacen muchas queries espaciales
        _('Extent Bounds'),
        default=dict,
        blank=True,
        help_text=_('Bounding box of all features [minX, minY, maxX, maxY]')
    )
    centroid = models.PointField(_('Centroid'), blank=True, null=True, srid=4326)
    
    # Attribute statistics
    attribute_stats = models.JSONField(
        _('Attribute Statistics'),
        default=dict,
        blank=True,
        help_text=_('Statistical summary of numeric attributes')
    )
    unique_values = models.JSONField(
        _('Unique Values'),
        default=dict,
        blank=True,
        help_text=_('Count of unique values for categorical fields')
    )
    
    # Data quality metrics
    null_count = models.JSONField(
        _('Null Value Counts'),
        default=dict,
        blank=True,
        help_text=_('Count of null values per field')
    )
    invalid_geometries = models.PositiveIntegerField(_('Invalid Geometries'), default=0)
    duplicate_records = models.PositiveIntegerField(_('Duplicate Records'), default=0)
    
    # Snapshot metadata
    data_checksum = models.CharField(
        _('Data Checksum'),
        max_length=64,
        blank=True,
        help_text=_('Checksum of actual data content')
    )
    schema_version = models.CharField(_('Schema Version'), max_length=50, blank=True)
    collection_duration_ms = models.PositiveIntegerField(
        _('Collection Duration (ms)'),
        default=0
    )
    
    # Storage information
    data_size_bytes = models.PositiveIntegerField(_('Data Size (bytes)'), default=0)
    compressed_size_bytes = models.PositiveIntegerField(
        _('Compressed Size (bytes)'),
        default=0
    )
    
    # Status and validation
    is_valid = models.BooleanField(_('Is Valid'), default=True)
    validation_errors = models.JSONField(
        _('Validation Errors'),
        default=list,
        blank=True
    )
    
    class Meta:
        db_table = 'monitoring_layer_snapshot'
        verbose_name = _('Layer Snapshot')
        verbose_name_plural = _('Layer Snapshots')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['layer', '-created']),
            models.Index(fields=['snapshot_hash']),
            models.Index(fields=['feature_count']),
            models.Index(fields=['is_valid']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        return f"Snapshot of {self.layer.name} - {self.created.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def compression_ratio(self):
        """Calculate compression ratio"""
        if self.data_size_bytes == 0:
            return 0
        return (1 - self.compressed_size_bytes / self.data_size_bytes) * 100
    
    def get_previous_snapshot(self):
        """Get the previous snapshot for comparison"""
        return LayerSnapshot.objects.filter(
            layer=self.layer,
            created__lt=self.created,
            is_valid=True
        ).order_by('-created').first()
    
    def compare_with_previous(self):
        """Compare this snapshot with the previous one"""
        previous = self.get_previous_snapshot()
        if not previous:
            return None
        
        return {
            'feature_count_change': self.feature_count - previous.feature_count,
            'feature_count_change_percent': (
                (self.feature_count - previous.feature_count) / previous.feature_count * 100
                if previous.feature_count > 0 else 0
            ),
            'area_change': (self.total_area or 0) - (previous.total_area or 0),
            'invalid_geometries_change': self.invalid_geometries - previous.invalid_geometries,
            'duplicate_records_change': self.duplicate_records - previous.duplicate_records,
            'data_size_change': self.data_size_bytes - previous.data_size_bytes,
        }


class ChangeDetectionResult(BaseModel):
    """
    Model to store results of change detection analysis
    """
    # Snapshots being compared
    current_snapshot = models.ForeignKey(
        LayerSnapshot,
        on_delete=models.CASCADE,
        related_name='change_results_as_current'
    )
    previous_snapshot = models.ForeignKey(
        LayerSnapshot,
        on_delete=models.CASCADE,
        related_name='change_results_as_previous',
        null=True,
        blank=True
    )
    
    # Change detection metadata
    algorithm_used = models.CharField(
        _('Algorithm Used'),
        max_length=50,
        choices=ChangeDetectionAlgorithm.choices,
        default=ChangeDetectionAlgorithm.SIMPLE_COUNT
    )
    detection_duration_ms = models.PositiveIntegerField(
        _('Detection Duration (ms)'),
        default=0
    )
    confidence_score = models.FloatField(
        _('Confidence Score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Confidence level of the detection (0.0 to 1.0)')
    )
    
    # Change summary
    has_changes = models.BooleanField(_('Has Changes'), default=False)
    change_types = ArrayField(
        models.CharField(max_length=20, choices=ChangeType.choices),
        size=10,
        default=list,
        blank=True,
        verbose_name=_('Change Types')
    )
    
    # Quantitative changes
    feature_count_change = models.IntegerField(_('Feature Count Change'), default=0)
    feature_count_change_percent = models.FloatField(
        _('Feature Count Change (%)'),
        default=0.0
    )
    
    # Geometric changes
    area_change = models.FloatField(_('Area Change'), default=0.0)
    area_change_percent = models.FloatField(_('Area Change (%)'), default=0.0)
    centroid_displacement = models.FloatField(
        _('Centroid Displacement'),
        default=0.0,
        help_text=_('Distance centroid moved (in layer units)')
    )
    
    # Attribute changes
    modified_features = models.PositiveIntegerField(_('Modified Features'), default=0)
    new_features = models.PositiveIntegerField(_('New Features'), default=0)
    deleted_features = models.PositiveIntegerField(_('Deleted Features'), default=0)
    
    # Data quality changes
    data_quality_score = models.FloatField(
        _('Data Quality Score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        blank=True,
        null=True
    )
    data_quality_change = models.FloatField(_('Data Quality Change'), default=0.0)
    
    # Detailed analysis
    change_details = models.JSONField(
        _('Change Details'),
        default=dict,
        blank=True,
        help_text=_('Detailed breakdown of detected changes')
    )
    # --- Decisión importante: Cambiar affected_features a una tabla intermedia ---
    # Si la lista de IDs es muy larga, un JSONField puede ser ineficiente.
    # Se podría crear una tabla intermedia para IDs de features afectadas.
    # affected_features = models.JSONField( # Campo original
    #     _('Affected Features'),
    #     default=list,
    #     blank=True,
    #     help_text=_('List of feature IDs affected by changes')
    # )
    
    # Statistical analysis
    statistical_significance = models.FloatField(
        _('Statistical Significance'),
        blank=True,
        null=True,
        help_text=_('P-value or other statistical measure')
    )
    anomaly_score = models.FloatField(
        _('Anomaly Score'),
        blank=True,
        null=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Alert thresholds
    exceeds_threshold = models.BooleanField(_('Exceeds Threshold'), default=False)
    threshold_values = models.JSONField(
        _('Threshold Values'),
        default=dict,
        blank=True,
        help_text=_('Threshold values that were compared against')
    )
    
    # Processing status
    processing_status = models.CharField(
        _('Processing Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('processing', _('Processing')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
        ],
        default='completed'
    )
    error_message = models.TextField(_('Error Message'), blank=True)
    
    class Meta:
        db_table = 'monitoring_change_detection_result'
        verbose_name = _('Change Detection Result')
        verbose_name_plural = _('Change Detection Results')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['current_snapshot', '-created']),
            models.Index(fields=['has_changes']),
            models.Index(fields=['exceeds_threshold']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        layer_name = self.current_snapshot.layer.name
        status = "Changes detected" if self.has_changes else "No changes"
        return f"{layer_name} - {status} - {self.created.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def layer(self):
        """Get the layer being monitored"""
        return self.current_snapshot.layer
    
    @property
    def total_features_affected(self):
        """Total number of features affected by changes"""
        return self.new_features + self.deleted_features + self.modified_features
    
    @property
    def change_severity(self):
        """Calculate change severity level"""
        if not self.has_changes:
            return 'none'
        
        # Base severity on percentage change and confidence
        severity_score = abs(self.feature_count_change_percent) * self.confidence_score
        
        if severity_score >= 50:
            return 'critical'
        elif severity_score >= 25:
            return 'high'
        elif severity_score >= 10:
            return 'medium'
        else:
            return 'low'
    
    def get_change_summary(self):
        """Get a human-readable summary of changes"""
        if not self.has_changes:
            return "No significant changes detected."
        
        summary_parts = []
        
        if self.feature_count_change != 0:
            change_direction = "increased" if self.feature_count_change > 0 else "decreased"
            summary_parts.append(
                f"Feature count {change_direction} by {abs(self.feature_count_change)} "
                f"({abs(self.feature_count_change_percent):.1f}%)"
            )
        
        if self.new_features > 0:
            summary_parts.append(f"{self.new_features} new features added")
        
        if self.deleted_features > 0:
            summary_parts.append(f"{self.deleted_features} features removed")
        
        if self.modified_features > 0:
            summary_parts.append(f"{self.modified_features} features modified")
        
        return "; ".join(summary_parts) or "Changes detected in layer properties."


class AffectedFeature(models.Model):
    """
    Model to store IDs of features affected by a change detection result.
    This replaces the JSONField 'affected_features' in ChangeDetectionResult
    for better performance and scalability with large lists of IDs.
    """
    change_result = models.ForeignKey(
        ChangeDetectionResult,
        on_delete=models.CASCADE,
        related_name='affected_feature_ids' # Nuevo related_name
    )
    feature_id = models.CharField(max_length=255) # ID de la feature, puede ser string si no es int
    
    class Meta:
        db_table = 'monitoring_affected_feature'
        verbose_name = _('Affected Feature ID')
        verbose_name_plural = _('Affected Feature IDs')
        # Índice compuesto para consultas rápidas
        indexes = [
            models.Index(fields=['change_result', 'feature_id']),
        ]
        # Opcional: unique_together si un ID no puede estar duplicado por resultado
        # unique_together = ['change_result', 'feature_id']


class MonitoringJob(BaseModel):
    """
    Model to track monitoring jobs and their execution
    """
    # Job identification
    name = models.CharField(_('Job Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    
    # Target configuration
    layers = models.ManyToManyField(
        SpatialLayer,
        related_name='monitoring_jobs',
        verbose_name=_('Monitored Layers')
    )
    services = models.ManyToManyField(
        ArcGISService,
        related_name='monitoring_jobs',
        blank=True,
        verbose_name=_('Monitored Services')
    )
    
    # Execution configuration
    schedule_expression = models.CharField(
        _('Schedule Expression'),
        max_length=100,
        help_text=_('Cron expression for job scheduling')
    )
    is_active = models.BooleanField(_('Is Active'), default=True)
    max_runtime_minutes = models.PositiveIntegerField(
        _('Max Runtime (minutes)'),
        default=60
    )
    
    # Change detection settings
    detection_algorithm = models.CharField(
        _('Detection Algorithm'),
        max_length=50,
        choices=ChangeDetectionAlgorithm.choices,
        default=ChangeDetectionAlgorithm.SIMPLE_COUNT
    )
    change_threshold = models.FloatField(
        _('Change Threshold (%)'),
        default=5.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    
    # Alert configuration
    alert_on_changes = models.BooleanField(_('Alert on Changes'), default=True)
    alert_on_errors = models.BooleanField(_('Alert on Errors'), default=True)
    alert_threshold = models.CharField(
        _('Alert Threshold'),
        max_length=20,
        choices=[
            ('any', _('Any Change')),
            ('low', _('Low Severity')),
            ('medium', _('Medium Severity')),
            ('high', _('High Severity')),
            ('critical', _('Critical Only')),
        ],
        default='medium'
    )
    
    # Execution tracking
    last_run = models.DateTimeField(_('Last Run'), blank=True, null=True)
    last_successful_run = models.DateTimeField(_('Last Successful Run'), blank=True, null=True)
    next_run = models.DateTimeField(_('Next Scheduled Run'), blank=True, null=True)
    consecutive_failures = models.PositiveIntegerField(_('Consecutive Failures'), default=0)
    
    # Status
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=MonitoringStatus.choices,
        default=MonitoringStatus.ACTIVE
    )
    
    # User management
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_monitoring_jobs'
    )
    
    class Meta:
        db_table = 'monitoring_job'
        verbose_name = _('Monitoring Job')
        verbose_name_plural = _('Monitoring Jobs')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['status']),
            models.Index(fields=['last_run']),
            models.Index(fields=['next_run']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def is_overdue(self):
        """Check if job is overdue for execution"""
        if not self.next_run or not self.is_active:
            return False
        return timezone.now() > self.next_run
    
    @property
    def total_layers(self):
        """Get total number of layers being monitored"""
        return self.layers.count()
    
    @property
    def total_services(self):
        """Get total number of services being monitored"""
        return self.services.count()
    
    def calculate_next_run(self):
        """
        Calculate next run time based on schedule expression.
        Uses croniter library for robust cron parsing.
        """
        from django.utils import timezone
        try:
            from croniter import croniter
            # Asegurar que el schedule_expression es un cron válido
            # Si no lo es, croniter lanzará una excepción
            if croniter.is_valid(self.schedule_expression):
                # Obtener el timestamp del próximo run basado en la hora actual
                next_run_timestamp = croniter(self.schedule_expression, timezone.now()).get_next()
                return timezone.datetime.fromtimestamp(next_run_timestamp, tz=timezone.now().tzinfo)
            else:
                # Si no es válido, usar la lógica anterior como fallback o lanzar error
                # Lanzamos una excepción para que sea manejada por el caller
                raise ValueError(f"Invalid cron expression: {self.schedule_expression}")
        except ImportError:
            # Si croniter no está instalado, usar la lógica simple como fallback
            import re
            if re.match(r'^\d+m, self.schedule_expression):  # e.g., "15m"
                minutes = int(self.schedule_expression[:-1])
                return timezone.now() + timezone.timedelta(minutes=minutes)
            elif re.match(r'^\d+h, self.schedule_expression):  # e.g., "2h"
                hours = int(self.schedule_expression[:-1])
                return timezone.now() + timezone.timedelta(hours=hours)
            elif re.match(r'^\d+d, self.schedule_expression):  # e.g., "1d"
                days = int(self.schedule_expression[:-1])
                return timezone.now() + timezone.timedelta(days=days)
            else:
                # Default to 1 hour if schedule can't be parsed
                return timezone.now() + timezone.timedelta(hours=1)
        except ValueError:
            # Capturar el error de croniter.is_valid o de la expresión inválida
            # y usar fallback
            import re
            if re.match(r'^\d+m, self.schedule_expression):  # e.g., "15m"
                minutes = int(self.schedule_expression[:-1])
                return timezone.now() + timezone.timedelta(minutes=minutes)
            elif re.match(r'^\d+h, self.schedule_expression):  # e.g., "2h"
                hours = int(self.schedule_expression[:-1])
                return timezone.now() + timezone.timedelta(hours=hours)
            elif re.match(r'^\d+d, self.schedule_expression):  # e.g., "1d"
                days = int(self.schedule_expression[:-1])
                return timezone.now() + timezone.timedelta(days=days)
            else:
                # Default to 1 hour if schedule can't be parsed
                return timezone.now() + timezone.timedelta(hours=1)
    
    def update_next_run(self):
        """Update the next run time"""
        self.next_run = self.calculate_next_run()
        self.save(update_fields=['next_run'])
    
    @transaction.atomic # Asegura que la actualización del job y la creación de la ejecución sean atómicas
    def record_execution(self, success=True, error_message=None):
        """
        Record job execution result.
        Now uses signals or a separate Celery task for creating MonitoringJobExecution
        is preferred for decoupling, but this is the direct method.
        """
        self.last_run = timezone.now()
        
        if success:
            self.last_successful_run = timezone.now()
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
        
        # Update next run time
        self.update_next_run()
        
        # Create execution record (dentro de la transacción)
        MonitoringJobExecution.objects.create(
            job=self,
            success=success,
            error_message=error_message or ''
        )
        
        # Disable job after too many consecutive failures
        if self.consecutive_failures >= 5:
            self.status = MonitoringStatus.ERROR
        
        # Guardar solo los campos actualizados
        update_fields = [
            'last_run', 'last_successful_run', 'consecutive_failures', 'status', 'next_run'
        ]
        self.save(update_fields=update_fields)


class MonitoringJobExecution(TimeStampedModel):
    """
    Model to track individual executions of monitoring jobs
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        MonitoringJob,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    
    # Execution details
    started_at = models.DateTimeField(_('Started At'), auto_now_add=True)
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(_('Duration (seconds)'), blank=True, null=True)
    
    # Execution results
    success = models.BooleanField(_('Success'), default=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    layers_processed = models.PositiveIntegerField(_('Layers Processed'), default=0)
    snapshots_created = models.PositiveIntegerField(_('Snapshots Created'), default=0)
    changes_detected = models.PositiveIntegerField(_('Changes Detected'), default=0)
    alerts_created = models.PositiveIntegerField(_('Alerts Created'), default=0)
    
    # Performance metrics
    memory_usage_mb = models.PositiveIntegerField(_('Memory Usage (MB)'), blank=True, null=True)
    cpu_usage_percent = models.FloatField(_('CPU Usage (%)'), blank=True, null=True)
    
    # Detailed results
    execution_log = models.JSONField(
        _('Execution Log'),
        default=list,
        blank=True,
        help_text=_('Detailed log of execution steps')
    )
    performance_metrics = models.JSONField(
        _('Performance Metrics'),
        default=dict,
        blank=True
    )
    
    class Meta:
        db_table = 'monitoring_job_execution'
        verbose_name = _('Monitoring Job Execution')
        verbose_name_plural = _('Monitoring Job Executions')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['job', '-started_at']),
            models.Index(fields=['success']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.job.name} - {status} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
    
    @transaction.atomic
    def mark_completed(self, success=True, error_message=None):
        """Mark execution as completed"""
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        self.success = success
        if error_message:
            self.error_message = error_message
        self.save(update_fields=[
            'completed_at', 'duration_seconds', 'success', 'error_message'
        ])
    
    @transaction.atomic
    def add_log_entry(self, level, message, **kwargs):
        """Add entry to execution log"""
        if not isinstance(self.execution_log, list):
            self.execution_log = []
        
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        }
        
        self.execution_log.append(log_entry)
        self.save(update_fields=['execution_log'])


class DataQualityRule(BaseModel):
    """
    Model to define data quality rules for monitoring
    """
    name = models.CharField(_('Rule Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    
    # Target specification
    layer = models.ForeignKey(
        SpatialLayer,
        on_delete=models.CASCADE,
        related_name='quality_rules',
        blank=True,
        null=True
    )
    service = models.ForeignKey(
        ArcGISService,
        on_delete=models.CASCADE,
        related_name='quality_rules',
        blank=True,
        null=True
    )
    
    # Rule definition
    rule_type = models.CharField(
        _('Rule Type'),
        max_length=50,
        choices=[
            ('completeness', _('Completeness')),
            ('accuracy', _('Accuracy')),
            ('consistency', _('Consistency')),
            ('validity', _('Validity')),
            ('uniqueness', _('Uniqueness')),
            ('timeliness', _('Timeliness')),
        ]
    )
    
    rule_expression = models.TextField(
        _('Rule Expression'),
        help_text=_('SQL-like expression or JSON configuration for the rule')
    )
    
    # Thresholds
    warning_threshold = models.FloatField(
        _('Warning Threshold'),
        default=0.95,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    error_threshold = models.FloatField(
        _('Error Threshold'),
        default=0.90,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Configuration
    is_active = models.BooleanField(_('Is Active'), default=True)
    check_frequency_hours = models.PositiveIntegerField(
        _('Check Frequency (hours)'),
        default=24
    )
    
    # Tracking
    last_check = models.DateTimeField(_('Last Check'), blank=True, null=True)
    last_score = models.FloatField(_('Last Quality Score'), blank=True, null=True)
    
    class Meta:
        db_table = 'monitoring_data_quality_rule'
        verbose_name = _('Data Quality Rule')
        verbose_name_plural = _('Data Quality Rules')
        ordering = ['name']
        indexes = [
            models.Index(fields=['layer']),
            models.Index(fields=['service']),
            models.Index(fields=['rule_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_check']),
        ]
    
    def __str__(self):
        target = self.layer.name if self.layer else (
            self.service.name if self.service else "Global"
        )
        return f"{self.name} ({target})"
    
    @property
    def needs_check(self):
        """Check if rule needs to be evaluated"""
        if not self.is_active or not self.last_check:
            return True
        
        next_check = self.last_check + timezone.timedelta(hours=self.check_frequency_hours)
        return timezone.now() >= next_check
    
    @property
    def current_status(self):
        """Get current quality status based on last score"""
        if self.last_score is None:
            return 'unknown'
        elif self.last_score >= self.warning_threshold:
            return 'good'
        elif self.last_score >= self.error_threshold:
            return 'warning'
        else:
            return 'error'


class DataQualityResult(TimeStampedModel):
    """
    Model to store results of data quality assessments
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(
        DataQualityRule,
        on_delete=models.CASCADE,
        related_name='results'
    )
    
    # Assessment results
    quality_score = models.FloatField(
        _('Quality Score'),
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    passed = models.BooleanField(_('Passed'))
    
    # Detailed metrics
    total_records = models.PositiveIntegerField(_('Total Records'), default=0)
    valid_records = models.PositiveIntegerField(_('Valid Records'), default=0)
    invalid_records = models.PositiveIntegerField(_('Invalid Records'), default=0)
    
    # Quality dimensions
    completeness_score = models.FloatField(_('Completeness Score'), blank=True, null=True)
    accuracy_score = models.FloatField(_('Accuracy Score'), blank=True, null=True)
    consistency_score = models.FloatField(_('Consistency Score'), blank=True, null=True)
    validity_score = models.FloatField(_('Validity Score'), blank=True, null=True)
    uniqueness_score = models.FloatField(_('Uniqueness Score'), blank=True, null=True)
    timeliness_score = models.FloatField(_('Timeliness Score'), blank=True, null=True)
    
    # Issues found
    issues_found = models.JSONField(
        _('Issues Found'),
        default=list,
        blank=True,
        help_text=_('List of specific issues identified')
    )
    
    # Recommendations
    recommendations = models.JSONField(
        _('Recommendations'),
        default=list,
        blank=True,
        help_text=_('Automated recommendations for improvement')
    )
    
    # Assessment metadata
    assessment_duration_ms = models.PositiveIntegerField(
        _('Assessment Duration (ms)'),
        default=0
    )
    
    class Meta:
        db_table = 'monitoring_data_quality_result'
        verbose_name = _('Data Quality Result')
        verbose_name_plural = _('Data Quality Results')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['rule', '-created']),
            models.Index(fields=['passed']),
            models.Index(fields=['quality_score']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        status = "Passed" if self.passed else "Failed"
        return f"{self.rule.name} - {status} ({self.quality_score:.2f})"
    
    @property
    def quality_grade(self):
        """Get quality grade based on score"""
        if self.quality_score >= 0.95:
            return 'A+'
        elif self.quality_score >= 0.90:
            return 'A'
        elif self.quality_score >= 0.85:
            return 'B+'
        elif self.quality_score >= 0.80:
            return 'B'
        elif self.quality_score >= 0.75:
            return 'C+'
        elif self.quality_score >= 0.70:
            return 'C'
        elif self.quality_score >= 0.65:
            return 'D+'
        elif self.quality_score >= 0.60:
            return 'D'
        else:
            return 'F'
    
    @property
    def issue_count(self):
        """Get total number of issues found"""
        return len(self.issues_found) if isinstance(self.issues_found, list) else 0


class SystemHealthMetric(TimeStampedModel):
    """
    Model to store system health metrics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # System metrics
    cpu_usage_percent = models.FloatField(_('CPU Usage (%)'))
    memory_usage_percent = models.FloatField(_('Memory Usage (%)'))
    disk_usage_percent = models.FloatField(_('Disk Usage (%)'))
    
    # Database metrics
    db_connections_active = models.PositiveIntegerField(_('Active DB Connections'))
    db_connections_idle = models.PositiveIntegerField(_('Idle DB Connections'))
    db_query_avg_time_ms = models.FloatField(_('Average Query Time (ms)'))
    
    # Redis metrics
    redis_memory_usage_mb = models.PositiveIntegerField(_('Redis Memory Usage (MB)'))
    redis_connected_clients = models.PositiveIntegerField(_('Redis Connected Clients'))
    redis_operations_per_sec = models.PositiveIntegerField(_('Redis Ops/sec'))
    
    # Celery metrics
    celery_active_tasks = models.PositiveIntegerField(_('Active Celery Tasks'))
    celery_pending_tasks = models.PositiveIntegerField(_('Pending Celery Tasks'))
    celery_failed_tasks = models.PositiveIntegerField(_('Failed Celery Tasks'))
    
    # Application metrics
    active_users = models.PositiveIntegerField(_('Active Users'))
    api_requests_per_minute = models.PositiveIntegerField(_('API Requests/min'))
    api_error_rate_percent = models.FloatField(_('API Error Rate (%)'))
    
    # Health status
    overall_health = models.CharField(
        _('Overall Health'),
        max_length=20,
        choices=[
            ('excellent', _('Excellent')),
            ('good', _('Good')),
            ('warning', _('Warning')),
            ('critical', _('Critical')),
            ('error', _('Error')),
        ],
        default='good'
    )
    
    class Meta:
        db_table = 'monitoring_system_health_metric'
        verbose_name = _('System Health Metric')
        verbose_name_plural = _('System Health Metrics')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['created']),
            models.Index(fields=['overall_health']),
            models.Index(fields=['cpu_usage_percent']),
            models.Index(fields=['memory_usage_percent']),
        ]
    
    def __str__(self):
        return f"System Health - {self.get_overall_health_display()} - {self.created.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def get_latest(cls):
        """Get the latest health metric"""
        return cls.objects.order_by('-created').first()
    
    @classmethod
    def get_average_metrics(cls, hours=24):
        """Get average metrics for the specified time period"""
        from django.db.models import Avg
        from django.utils import timezone
        
        since = timezone.now() - timezone.timedelta(hours=hours)
        return cls.objects.filter(created__gte=since).aggregate(
            avg_cpu=Avg('cpu_usage_percent'),
            avg_memory=Avg('memory_usage_percent'),
            avg_disk=Avg('disk_usage_percent'),
            avg_db_query_time=Avg('db_query_avg_time_ms'),
            avg_api_error_rate=Avg('api_error_rate_percent'),
        )
