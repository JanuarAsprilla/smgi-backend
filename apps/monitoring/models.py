"""
Models for Monitoring app.
"""
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import User
from apps.geodata.models import Layer, DataSource
from apps.agents.models import Agent


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


class MonitoringProject(BaseModel):
    """
    Model for monitoring projects.
    Groups multiple monitors and areas of interest.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Activo')
        PAUSED = 'paused', _('Pausado')
        COMPLETED = 'completed', _('Completado')
        ARCHIVED = 'archived', _('Archivado')
    
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción')
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    # Area of interest
    area_of_interest = gis_models.PolygonField(
        _('área de interés'),
        null=True,
        blank=True,
        help_text=_('Polígono que define el área de monitoreo')
    )
    
    # Configuration
    configuration = models.JSONField(
        _('configuración'),
        default=dict,
        blank=True
    )
    
    # Metadata
    tags = models.JSONField(
        _('etiquetas'),
        default=list,
        blank=True
    )
    metadata = models.JSONField(
        _('metadatos'),
        default=dict,
        blank=True
    )
    
    # Dates
    start_date = models.DateTimeField(
        _('fecha de inicio'),
        null=True,
        blank=True
    )
    end_date = models.DateTimeField(
        _('fecha de fin'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('proyecto de monitoreo')
        verbose_name_plural = _('proyectos de monitoreo')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return self.name


class Monitor(BaseModel):
    """
    Model for monitors.
    Monitors track changes in specific layers or data sources.
    """
    
    class MonitorType(models.TextChoices):
        CHANGE_DETECTION = 'change_detection', _('Detección de Cambios')
        THRESHOLD = 'threshold', _('Umbral')
        ANOMALY = 'anomaly', _('Anomalía')
        PATTERN = 'pattern', _('Patrón')
        TEMPORAL = 'temporal', _('Temporal')
        SPATIAL = 'spatial', _('Espacial')
        CUSTOM = 'custom', _('Personalizado')
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Activo')
        PAUSED = 'paused', _('Pausado')
        ERROR = 'error', _('Error')
        INACTIVE = 'inactive', _('Inactivo')
    
    project = models.ForeignKey(
        MonitoringProject,
        on_delete=models.CASCADE,
        related_name='monitors',
        verbose_name=_('proyecto')
    )
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    monitor_type = models.CharField(
        _('tipo de monitor'),
        max_length=30,
        choices=MonitorType.choices
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    # Monitoring targets
    layers = models.ManyToManyField(
        Layer,
        related_name='monitors',
        verbose_name=_('capas'),
        blank=True
    )
    data_sources = models.ManyToManyField(
        DataSource,
        related_name='monitors',
        verbose_name=_('fuentes de datos'),
        blank=True
    )
    
    # Analysis configuration
    agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monitors',
        verbose_name=_('agente de análisis')
    )
    parameters = models.JSONField(
        _('parámetros'),
        default=dict,
        blank=True,
        help_text=_('Parámetros para el análisis')
    )
    
    # Monitoring schedule
    check_interval = models.IntegerField(
        _('intervalo de verificación (minutos)'),
        default=60,
        help_text=_('Frecuencia de verificación')
    )
    last_check = models.DateTimeField(
        _('última verificación'),
        null=True,
        blank=True
    )
    next_check = models.DateTimeField(
        _('próxima verificación'),
        null=True,
        blank=True
    )
    
    # Statistics
    check_count = models.IntegerField(
        _('número de verificaciones'),
        default=0
    )
    detection_count = models.IntegerField(
        _('número de detecciones'),
        default=0
    )
    
    # Metadata
    tags = models.JSONField(
        _('etiquetas'),
        default=list,
        blank=True
    )
    
    class Meta:
        verbose_name = _('monitor')
        verbose_name_plural = _('monitores')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['monitor_type', 'is_active']),
            models.Index(fields=['next_check', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.project.name}"


class Detection(BaseModel):
    """
    Model for detections.
    Records when a monitor detects a change or event.
    """
    
    class Severity(models.TextChoices):
        LOW = 'low', _('Baja')
        MEDIUM = 'medium', _('Media')
        HIGH = 'high', _('Alta')
        CRITICAL = 'critical', _('Crítica')
    
    class Status(models.TextChoices):
        NEW = 'new', _('Nueva')
        CONFIRMED = 'confirmed', _('Confirmada')
        FALSE_POSITIVE = 'false_positive', _('Falso Positivo')
        RESOLVED = 'resolved', _('Resuelta')
        IGNORED = 'ignored', _('Ignorada')
    
    monitor = models.ForeignKey(
        Monitor,
        on_delete=models.CASCADE,
        related_name='detections',
        verbose_name=_('monitor')
    )
    title = models.CharField(
        _('título'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    severity = models.CharField(
        _('severidad'),
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )
    
    # Detection data
    detected_at = models.DateTimeField(
        _('detectado en'),
        auto_now_add=True
    )
    location = gis_models.PointField(
        _('ubicación'),
        null=True,
        blank=True
    )
    affected_area = gis_models.PolygonField(
        _('área afectada'),
        null=True,
        blank=True
    )
    
    # Analysis results
    analysis_data = models.JSONField(
        _('datos de análisis'),
        default=dict,
        blank=True,
        help_text=_('Resultados del análisis que generó la detección')
    )
    confidence_score = models.FloatField(
        _('puntuación de confianza'),
        null=True,
        blank=True,
        help_text=_('0.0 a 1.0')
    )
    
    # Related data
    related_layers = models.ManyToManyField(
        Layer,
        related_name='detections',
        verbose_name=_('capas relacionadas'),
        blank=True
    )
    
    # Evidence
    evidence = models.JSONField(
        _('evidencia'),
        default=dict,
        blank=True,
        help_text=_('Evidencia de la detección (imágenes, datos, etc.)')
    )
    
    # Review information
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_detections',
        verbose_name=_('revisado por')
    )
    reviewed_at = models.DateTimeField(
        _('revisado en'),
        null=True,
        blank=True
    )
    review_notes = models.TextField(
        _('notas de revisión'),
        blank=True
    )
    
    class Meta:
        verbose_name = _('detección')
        verbose_name_plural = _('detecciones')
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['monitor', 'status']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['detected_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.monitor.name}"


class ChangeRecord(BaseModel):
    """
    Model for recording specific changes detected.
    """
    
    class ChangeType(models.TextChoices):
        ADDED = 'added', _('Añadido')
        REMOVED = 'removed', _('Eliminado')
        MODIFIED = 'modified', _('Modificado')
        MOVED = 'moved', _('Movido')
    
    detection = models.ForeignKey(
        Detection,
        on_delete=models.CASCADE,
        related_name='changes',
        verbose_name=_('detección')
    )
    change_type = models.CharField(
        _('tipo de cambio'),
        max_length=20,
        choices=ChangeType.choices
    )
    
    # Change details
    feature_id = models.CharField(
        _('ID de feature'),
        max_length=255,
        blank=True
    )
    layer = models.ForeignKey(
        Layer,
        on_delete=models.CASCADE,
        related_name='change_records',
        verbose_name=_('capa')
    )
    
    # Geometric data
    before_geometry = gis_models.GeometryField(
        _('geometría anterior'),
        null=True,
        blank=True
    )
    after_geometry = gis_models.GeometryField(
        _('geometría posterior'),
        null=True,
        blank=True
    )
    
    # Attribute data
    before_attributes = models.JSONField(
        _('atributos anteriores'),
        default=dict,
        blank=True
    )
    after_attributes = models.JSONField(
        _('atributos posteriores'),
        default=dict,
        blank=True
    )
    
    # Metadata
    change_magnitude = models.FloatField(
        _('magnitud del cambio'),
        null=True,
        blank=True,
        help_text=_('Medida cuantitativa del cambio')
    )
    metadata = models.JSONField(
        _('metadatos'),
        default=dict,
        blank=True
    )
    
    class Meta:
        verbose_name = _('registro de cambio')
        verbose_name_plural = _('registros de cambios')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['detection', 'change_type']),
            models.Index(fields=['layer', 'feature_id']),
        ]
    
    def __str__(self):
        return f"{self.change_type} - {self.layer.name}"


class MonitoringReport(BaseModel):
    """
    Model for monitoring reports.
    Summarizes monitoring activities over a period.
    """
    
    class ReportType(models.TextChoices):
        DAILY = 'daily', _('Diario')
        WEEKLY = 'weekly', _('Semanal')
        MONTHLY = 'monthly', _('Mensual')
        CUSTOM = 'custom', _('Personalizado')
    
    project = models.ForeignKey(
        MonitoringProject,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name=_('proyecto')
    )
    title = models.CharField(
        _('título'),
        max_length=255
    )
    report_type = models.CharField(
        _('tipo de reporte'),
        max_length=20,
        choices=ReportType.choices
    )
    
    # Report period
    start_date = models.DateTimeField(
        _('fecha de inicio')
    )
    end_date = models.DateTimeField(
        _('fecha de fin')
    )
    
    # Report data
    summary = models.TextField(
        _('resumen'),
        blank=True
    )
    statistics = models.JSONField(
        _('estadísticas'),
        default=dict,
        blank=True
    )
    detections_summary = models.JSONField(
        _('resumen de detecciones'),
        default=dict,
        blank=True
    )
    
    # Files
    report_file = models.FileField(
        _('archivo de reporte'),
        upload_to='monitoring_reports/',
        blank=True,
        null=True
    )
    
    # Metadata
    generated_at = models.DateTimeField(
        _('generado en'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('reporte de monitoreo')
        verbose_name_plural = _('reportes de monitoreo')
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['project', 'report_type']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.project.name}"


class Baseline(BaseModel):
    """
    Model for baseline data.
    Stores reference state for comparison.
    """
    monitor = models.ForeignKey(
        Monitor,
        on_delete=models.CASCADE,
        related_name='baselines',
        verbose_name=_('monitor')
    )
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    
    # Baseline data
    baseline_date = models.DateTimeField(
        _('fecha de referencia')
    )
    baseline_data = models.JSONField(
        _('datos de referencia'),
        default=dict,
        help_text=_('Estado de referencia para comparación')
    )
    
    # Statistics
    feature_count = models.IntegerField(
        _('número de features'),
        default=0
    )
    area_coverage = models.FloatField(
        _('cobertura de área'),
        null=True,
        blank=True,
        help_text=_('Área cubierta en km²')
    )
    
    # Status
    is_current = models.BooleanField(
        _('es actual'),
        default=True,
        help_text=_('Si es la línea base actual para el monitor')
    )
    
    class Meta:
        verbose_name = _('línea base')
        verbose_name_plural = _('líneas base')
        ordering = ['-baseline_date']
        indexes = [
            models.Index(fields=['monitor', 'is_current']),
            models.Index(fields=['baseline_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.monitor.name}"
