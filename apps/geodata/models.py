"""
Models for Geodata app.
SMGI - Sistema de Monitoreo Geoespacial Inteligente
"""
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import User


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


class DataSource(BaseModel):
    """
    Model for external data sources (APIs, WMS, WFS, etc.)
    """
    
    class SourceType(models.TextChoices):
        WMS = 'wms', _('Web Map Service')
        WFS = 'wfs', _('Web Feature Service')
        WMTS = 'wmts', _('Web Map Tile Service')
        API = 'api', _('REST API')
        DATABASE = 'database', _('Base de Datos')
        FILE = 'file', _('Archivo')
        SENTINEL = 'sentinel', _('Sentinel Hub')
        LANDSAT = 'landsat', _('Landsat')
        ARCGIS = 'arcgis', _('ArcGIS Online')
        CUSTOM = 'custom', _('Personalizado')
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Activo')
        INACTIVE = 'inactive', _('Inactivo')
        ERROR = 'error', _('Error')
        MAINTENANCE = 'maintenance', _('Mantenimiento')
    
    name = models.CharField(
        _('nombre'),
        max_length=255,
        unique=True
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    source_type = models.CharField(
        _('tipo de fuente'),
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.FILE
    )
    url = models.URLField(
        _('URL'),
        max_length=500,
        blank=True
    )
    credentials = models.JSONField(
        _('credenciales'),
        default=dict,
        blank=True,
        help_text=_('API keys, tokens, usuario/contraseña encriptados')
    )
    configuration = models.JSONField(
        _('configuración'),
        default=dict,
        blank=True,
        help_text=_('Parámetros adicionales de configuración')
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    refresh_interval = models.IntegerField(
        _('intervalo de actualización (minutos)'),
        default=60,
        help_text=_('0 para actualización manual')
    )
    last_sync = models.DateTimeField(
        _('última sincronización'),
        null=True,
        blank=True
    )
    metadata = models.JSONField(
        _('metadatos'),
        default=dict,
        blank=True
    )
    tags = models.JSONField(
        _('etiquetas'),
        default=list,
        blank=True
    )
    
    class Meta:
        verbose_name = _('fuente de datos')
        verbose_name_plural = _('fuentes de datos')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_type', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def can_sync(self):
        """Verifica si la fuente puede sincronizarse."""
        return self.status == self.Status.ACTIVE and self.is_active
    
    def is_sync_needed(self):
        """Verifica si es necesario sincronizar (basado en intervalo)."""
        if not self.can_sync() or self.refresh_interval == 0:
            return False
        
        if not self.last_sync:
            return True
        
        from django.utils import timezone
        from datetime import timedelta
        
        next_sync = self.last_sync + timedelta(minutes=self.refresh_interval)
        return timezone.now() >= next_sync
    
    def get_connection_info(self):
        """Retorna información de conexión ofuscada."""
        info = {
            'type': self.source_type,
            'url': self.url,
            'status': self.status,
            'has_credentials': bool(self.credentials)
        }
        return info


class Layer(BaseModel):
    """
    Model for geographic layers.
    Supports both file uploads and external data sources.
    """
    
    class LayerType(models.TextChoices):
        VECTOR = 'vector', _('Vectorial')
        RASTER = 'raster', _('Raster')
        POINT_CLOUD = 'point_cloud', _('Nube de Puntos')
        TILE = 'tile', _('Tiles')
    
    class GeometryType(models.TextChoices):
        POINT = 'POINT', _('Punto')
        LINESTRING = 'LINESTRING', _('Línea')
        POLYGON = 'POLYGON', _('Polígono')
        MULTIPOINT = 'MULTIPOINT', _('Multipunto')
        MULTILINESTRING = 'MULTILINESTRING', _('Multilínea')
        MULTIPOLYGON = 'MULTIPOLYGON', _('Multipolígono')
        GEOMETRYCOLLECTION = 'GEOMETRYCOLLECTION', _('Colección')
        GEOMETRY = 'GEOMETRY', _('Geometría Mixta')
        RASTER = 'RASTER', _('Raster')
    
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name='layers',
        verbose_name=_('fuente de datos'),
        null=True,
        blank=True
    )
    layer_type = models.CharField(
        _('tipo de capa'),
        max_length=20,
        choices=LayerType.choices,
        default=LayerType.VECTOR
    )
    geometry_type = models.CharField(
        _('tipo de geometría'),
        max_length=30,
        choices=GeometryType.choices,
        default=GeometryType.GEOMETRY
    )
    srid = models.IntegerField(
        _('SRID'),
        default=4326,
        help_text=_('Sistema de referencia espacial (EPSG)')
    )
    feature_count = models.IntegerField(
        _('número de features'),
        default=0
    )
    extent = gis_models.PolygonField(
        _('extensión'),
        null=True,
        blank=True,
        help_text=_('Bounding box de la capa')
    )
    style = models.JSONField(
        _('estilo'),
        default=dict,
        blank=True,
        help_text=_('Configuración de estilos para visualización')
    )
    properties_schema = models.JSONField(
        _('esquema de propiedades'),
        default=dict,
        blank=True,
        help_text=_('Definición de campos y tipos de datos')
    )
    is_public = models.BooleanField(
        _('público'),
        default=False
    )
    is_queryable = models.BooleanField(
        _('consultable'),
        default=True
    )
    metadata = models.JSONField(
        _('metadatos'),
        default=dict,
        blank=True
    )
    tags = models.JSONField(
        _('etiquetas'),
        default=list,
        blank=True
    )
    original_filename = models.CharField(
        _('nombre de archivo original'),
        max_length=500,
        blank=True
    )
    file_size = models.BigIntegerField(
        _('tamaño del archivo (bytes)'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('capa')
        verbose_name_plural = _('capas')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['layer_type', 'is_active']),
            models.Index(fields=['is_public']),
            models.Index(fields=['created_at']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        if self.data_source:
            return f"{self.name} ({self.data_source.name})"
        return self.name
    
    def update_feature_count(self):
        """Actualiza el conteo de features."""
        self.feature_count = self.features.filter(is_active=True).count()
        self.save(update_fields=['feature_count'])
    
    def get_bounds(self):
        """Retorna los límites de la capa en formato [minx, miny, maxx, maxy]."""
        if self.extent:
            return list(self.extent.extent)
        return None
    
    def has_data(self):
        """Verifica si la capa tiene features."""
        return self.feature_count > 0
    
    def get_size_mb(self):
        """Retorna el tamaño del archivo en MB."""
        if self.file_size:
            return round(self.file_size / 1024 / 1024, 2)
        return 0


class Feature(BaseModel):
    """
    Model for individual geographic features.
    """
    layer = models.ForeignKey(
        Layer,
        on_delete=models.CASCADE,
        related_name='features',
        verbose_name=_('capa')
    )
    geometry = gis_models.GeometryField(
        _('geometría'),
        srid=4326
    )
    properties = models.JSONField(
        _('propiedades'),
        default=dict,
        help_text=_('Atributos del feature en formato GeoJSON')
    )
    feature_id = models.CharField(
        _('ID de feature'),
        max_length=255,
        blank=True,
        help_text=_('ID externo del feature')
    )
    
    class Meta:
        verbose_name = _('feature')
        verbose_name_plural = _('features')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['layer', 'is_active']),
            models.Index(fields=['feature_id']),
        ]
    
    def __str__(self):
        return f"Feature {self.id} - {self.layer.name}"


class Dataset(BaseModel):
    """
    Model for datasets (collections of layers).
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
    layers = models.ManyToManyField(
        Layer,
        related_name='datasets',
        verbose_name=_('capas'),
        blank=True
    )
    is_public = models.BooleanField(
        _('público'),
        default=False
    )
    metadata = models.JSONField(
        _('metadatos'),
        default=dict,
        blank=True
    )
    tags = models.JSONField(
        _('etiquetas'),
        default=list,
        blank=True
    )
    
    class Meta:
        verbose_name = _('dataset')
        verbose_name_plural = _('datasets')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class SyncLog(models.Model):
    """
    Model to track synchronization logs.
    """
    
    class Status(models.TextChoices):
        SUCCESS = 'success', _('Exitoso')
        FAILED = 'failed', _('Fallido')
        PARTIAL = 'partial', _('Parcial')
        PROCESSING = 'processing', _('Procesando')
    
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name='sync_logs',
        verbose_name=_('fuente de datos'),
        null=True,
        blank=True
    )
    layer = models.ForeignKey(
        Layer,
        on_delete=models.CASCADE,
        related_name='sync_logs',
        verbose_name=_('capa'),
        null=True,
        blank=True
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING
    )
    started_at = models.DateTimeField(
        _('iniciado en'),
        auto_now_add=True
    )
    completed_at = models.DateTimeField(
        _('completado en'),
        null=True,
        blank=True
    )
    records_processed = models.IntegerField(
        _('registros procesados'),
        default=0
    )
    records_added = models.IntegerField(
        _('registros añadidos'),
        default=0
    )
    records_updated = models.IntegerField(
        _('registros actualizados'),
        default=0
    )
    records_failed = models.IntegerField(
        _('registros fallidos'),
        default=0
    )
    error_message = models.TextField(
        _('mensaje de error'),
        blank=True
    )
    details = models.JSONField(
        _('detalles'),
        default=dict,
        blank=True
    )
    
    class Meta:
        verbose_name = _('log de sincronización')
        verbose_name_plural = _('logs de sincronización')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['data_source', 'status']),
            models.Index(fields=['layer', 'status']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        source = self.data_source.name if self.data_source else (self.layer.name if self.layer else 'N/A')
        return f"Sync {source} - {self.status} ({self.started_at})"
    
    def get_duration_seconds(self):
        """Retorna la duración de la sincronización en segundos."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return round(delta.total_seconds(), 2)
        return None
    
    def get_success_rate(self):
        """Retorna el porcentaje de éxito de los registros procesados."""
        if self.records_processed == 0:
            return 0.0
        successful = self.records_added + self.records_updated
        return round((successful / self.records_processed) * 100, 2)