"""
Models for Agents app.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import User
from apps.geodata.models import Layer, Dataset


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


class AgentCategory(BaseModel):
    """
    Categories for organizing agents.
    """
    name = models.CharField(
        _('nombre'),
        max_length=100,
        unique=True
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    icon = models.CharField(
        _('icono'),
        max_length=50,
        blank=True,
        help_text=_('Nombre del icono (ej: map, chart, alert)')
    )
    color = models.CharField(
        _('color'),
        max_length=7,
        default='#3B82F6',
        help_text=_('Color hexadecimal')
    )
    
    class Meta:
        verbose_name = _('categoría de agente')
        verbose_name_plural = _('categorías de agentes')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Agent(BaseModel):
    """
    Model for analysis agents.
    Agents are reusable analysis components that can be configured and executed.
    """
    
    class AgentType(models.TextChoices):
        CHANGE_DETECTION = 'change_detection', _('Detección de Cambios')
        CLASSIFICATION = 'classification', _('Clasificación')
        SEGMENTATION = 'segmentation', _('Segmentación')
        PREDICTION = 'prediction', _('Predicción')
        STATISTICS = 'statistics', _('Estadísticas')
        CUSTOM = 'custom', _('Personalizado')
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Borrador')
        PUBLISHED = 'published', _('Publicado')
        ARCHIVED = 'archived', _('Archivado')
    
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción')
    )
    category = models.ForeignKey(
        AgentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        verbose_name=_('categoría')
    )
    agent_type = models.CharField(
        _('tipo de agente'),
        max_length=30,
        choices=AgentType.choices
    )
    version = models.CharField(
        _('versión'),
        max_length=20,
        default='1.0.0'
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Code and configuration
    code = models.TextField(
        _('código'),
        help_text=_('Código Python del agente')
    )
    requirements = models.JSONField(
        _('dependencias'),
        default=list,
        blank=True,
        help_text=_('Lista de paquetes Python requeridos')
    )
    parameters_schema = models.JSONField(
        _('esquema de parámetros'),
        default=dict,
        blank=True,
        help_text=_('JSON Schema para validar parámetros de entrada')
    )
    default_parameters = models.JSONField(
        _('parámetros por defecto'),
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
    
    # Usage statistics
    execution_count = models.IntegerField(
        _('número de ejecuciones'),
        default=0
    )
    success_count = models.IntegerField(
        _('ejecuciones exitosas'),
        default=0
    )
    failure_count = models.IntegerField(
        _('ejecuciones fallidas'),
        default=0
    )
    
    # Publishing
    is_public = models.BooleanField(
        _('público'),
        default=False,
        help_text=_('Si es público, estará disponible en el marketplace')
    )
    is_verified = models.BooleanField(
        _('verificado'),
        default=False,
        help_text=_('Agentes verificados por el equipo de SMGI')
    )
    downloads = models.IntegerField(
        _('descargas'),
        default=0
    )
    rating = models.DecimalField(
        _('calificación'),
        max_digits=3,
        decimal_places=2,
        default=0.0
    )
    
    class Meta:
        verbose_name = _('agente')
        verbose_name_plural = _('agentes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent_type', 'status']),
            models.Index(fields=['is_public', 'is_verified']),
            models.Index(fields=['-rating']),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100


class AgentExecution(BaseModel):
    """
    Model for tracking agent executions.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pendiente')
        RUNNING = 'running', _('Ejecutando')
        SUCCESS = 'success', _('Exitoso')
        FAILED = 'failed', _('Fallido')
        CANCELLED = 'cancelled', _('Cancelado')
    
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name=_('agente')
    )
    name = models.CharField(
        _('nombre'),
        max_length=255,
        blank=True
    )
    
    # Input configuration
    input_layers = models.ManyToManyField(
        Layer,
        related_name='agent_executions',
        verbose_name=_('capas de entrada'),
        blank=True
    )
    input_datasets = models.ManyToManyField(
        Dataset,
        related_name='agent_executions',
        verbose_name=_('datasets de entrada'),
        blank=True
    )
    parameters = models.JSONField(
        _('parámetros'),
        default=dict
    )
    
    # Execution details
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    started_at = models.DateTimeField(
        _('iniciado en'),
        null=True,
        blank=True
    )
    completed_at = models.DateTimeField(
        _('completado en'),
        null=True,
        blank=True
    )
    
    # Results
    output_data = models.JSONField(
        _('datos de salida'),
        default=dict,
        blank=True
    )
    output_layers = models.JSONField(
        _('capas de salida'),
        default=list,
        blank=True,
        help_text=_('IDs de capas generadas')
    )
    logs = models.TextField(
        _('logs'),
        blank=True
    )
    error_message = models.TextField(
        _('mensaje de error'),
        blank=True
    )
    
    # Performance metrics
    processing_time = models.FloatField(
        _('tiempo de procesamiento (segundos)'),
        null=True,
        blank=True
    )
    memory_usage = models.FloatField(
        _('uso de memoria (MB)'),
        null=True,
        blank=True
    )
    
    # Celery task
    task_id = models.CharField(
        _('ID de tarea'),
        max_length=255,
        blank=True,
        help_text=_('ID de la tarea Celery')
    )
    
    class Meta:
        verbose_name = _('ejecución de agente')
        verbose_name_plural = _('ejecuciones de agentes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['task_id']),
        ]
    
    def __str__(self):
        return f"{self.agent.name} - {self.status} ({self.created_at})"
    
    @property
    def duration(self):
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None


class AgentSchedule(BaseModel):
    """
    Model for scheduling automatic agent executions.
    """
    
    class ScheduleType(models.TextChoices):
        INTERVAL = 'interval', _('Intervalo')
        CRON = 'cron', _('Cron')
        ONCE = 'once', _('Una vez')
    
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name=_('agente')
    )
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    
    # Schedule configuration
    schedule_type = models.CharField(
        _('tipo de programación'),
        max_length=20,
        choices=ScheduleType.choices
    )
    interval_minutes = models.IntegerField(
        _('intervalo (minutos)'),
        null=True,
        blank=True,
        help_text=_('Para tipo interval')
    )
    cron_expression = models.CharField(
        _('expresión cron'),
        max_length=100,
        blank=True,
        help_text=_('Para tipo cron (ej: 0 0 * * *)')
    )
    scheduled_time = models.DateTimeField(
        _('hora programada'),
        null=True,
        blank=True,
        help_text=_('Para tipo once')
    )
    
    # Execution configuration
    input_layers = models.ManyToManyField(
        Layer,
        related_name='agent_schedules',
        verbose_name=_('capas de entrada'),
        blank=True
    )
    input_datasets = models.ManyToManyField(
        Dataset,
        related_name='agent_schedules',
        verbose_name=_('datasets de entrada'),
        blank=True
    )
    parameters = models.JSONField(
        _('parámetros'),
        default=dict
    )
    
    # Status
    is_enabled = models.BooleanField(
        _('habilitado'),
        default=True
    )
    last_run = models.DateTimeField(
        _('última ejecución'),
        null=True,
        blank=True
    )
    next_run = models.DateTimeField(
        _('próxima ejecución'),
        null=True,
        blank=True
    )
    run_count = models.IntegerField(
        _('número de ejecuciones'),
        default=0
    )
    
    class Meta:
        verbose_name = _('programación de agente')
        verbose_name_plural = _('programaciones de agentes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'is_enabled']),
            models.Index(fields=['next_run', 'is_enabled']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.agent.name}"


class AgentRating(models.Model):
    """
    Model for user ratings of agents.
    """
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_('agente')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='agent_ratings',
        verbose_name=_('usuario')
    )
    rating = models.IntegerField(
        _('calificación'),
        choices=[(i, i) for i in range(1, 6)],
        help_text=_('Calificación de 1 a 5 estrellas')
    )
    comment = models.TextField(
        _('comentario'),
        blank=True
    )
    created_at = models.DateTimeField(
        _('fecha de creación'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('fecha de actualización'),
        auto_now=True
    )
    
    class Meta:
        verbose_name = _('calificación de agente')
        verbose_name_plural = _('calificaciones de agentes')
        unique_together = ['agent', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.agent.name}: {self.rating}★"


class AgentTemplate(BaseModel):
    """
    Model for agent templates (pre-built agent configurations).
    """
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción')
    )
    category = models.ForeignKey(
        AgentCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='templates',
        verbose_name=_('categoría')
    )
    agent_type = models.CharField(
        _('tipo de agente'),
        max_length=30,
        choices=Agent.AgentType.choices
    )
    
    # Template configuration
    code_template = models.TextField(
        _('plantilla de código'),
        help_text=_('Código con placeholders para personalización')
    )
    parameters_schema = models.JSONField(
        _('esquema de parámetros'),
        default=dict
    )
    default_parameters = models.JSONField(
        _('parámetros por defecto'),
        default=dict
    )
    
    # Metadata
    tags = models.JSONField(
        _('etiquetas'),
        default=list,
        blank=True
    )
    thumbnail = models.ImageField(
        _('miniatura'),
        upload_to='agent_templates/',
        blank=True,
        null=True
    )
    
    # Usage
    usage_count = models.IntegerField(
        _('veces usado'),
        default=0
    )
    is_featured = models.BooleanField(
        _('destacado'),
        default=False
    )
    
    class Meta:
        verbose_name = _('plantilla de agente')
        verbose_name_plural = _('plantillas de agentes')
        ordering = ['-usage_count', 'name']
    
    def __str__(self):
        return self.name
