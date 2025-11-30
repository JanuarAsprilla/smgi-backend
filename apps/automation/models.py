"""
Models for Automation app.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.users.models import User
from apps.geodata.models import Layer, DataSource
from apps.agents.models import Agent
from apps.monitoring.models import Monitor, Detection


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


class Workflow(BaseModel):
    """
    Model for automation workflows.
    A workflow is a sequence of tasks that can be executed automatically.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Borrador')
        ACTIVE = 'active', _('Activo')
        PAUSED = 'paused', _('Pausado')
        ARCHIVED = 'archived', _('Archivado')
    
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Workflow configuration
    workflow_definition = models.JSONField(
        _('definición del workflow'),
        default=dict,
        help_text=_('Definición del flujo de trabajo en formato JSON')
    )
    
    # Trigger configuration
    trigger_type = models.CharField(
        _('tipo de activador'),
        max_length=50,
        choices=[
            ('manual', _('Manual')),
            ('schedule', _('Programado')),
            ('detection', _('Detección')),
            ('webhook', _('Webhook')),
            ('data_change', _('Cambio en Datos')),
        ],
        default='manual'
    )
    trigger_config = models.JSONField(
        _('configuración del activador'),
        default=dict,
        blank=True
    )
    
    # Execution settings
    timeout_minutes = models.IntegerField(
        _('tiempo de espera (minutos)'),
        default=60,
        help_text=_('Tiempo máximo de ejecución')
    )
    retry_count = models.IntegerField(
        _('número de reintentos'),
        default=0,
        help_text=_('Número de reintentos en caso de fallo')
    )
    
    # Statistics
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
    last_execution = models.DateTimeField(
        _('última ejecución'),
        null=True,
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
    
    class Meta:
        verbose_name = _('workflow')
        verbose_name_plural = _('workflows')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['trigger_type']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.execution_count == 0:
            return 0.0
        return round((self.success_count / self.execution_count) * 100, 2)
    
    def can_execute(self):
        """Check if workflow can be executed."""
        return self.status == 'active' and self.is_active
    
    def increment_stats(self, success=True):
        """Increment execution statistics."""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.last_execution = timezone.now()
        self.save(update_fields=['execution_count', 'success_count', 'failure_count', 'last_execution'])


class WorkflowTask(BaseModel):
    """
    Model for workflow tasks.
    Individual tasks within a workflow.
    """
    
    class TaskType(models.TextChoices):
        AGENT_EXECUTION = 'agent_execution', _('Ejecución de Agente')
        DATA_SYNC = 'data_sync', _('Sincronización de Datos')
        MONITOR_CHECK = 'monitor_check', _('Verificación de Monitor')
        NOTIFICATION = 'notification', _('Notificación')
        DATA_TRANSFORM = 'data_transform', _('Transformación de Datos')
        CONDITIONAL = 'conditional', _('Condicional')
        LOOP = 'loop', _('Bucle')
        API_CALL = 'api_call', _('Llamada API')
        SCRIPT = 'script', _('Script')
    
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_('workflow')
    )
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    task_type = models.CharField(
        _('tipo de tarea'),
        max_length=30,
        choices=TaskType.choices
    )
    
    # Task configuration
    configuration = models.JSONField(
        _('configuración'),
        default=dict,
        help_text=_('Configuración específica de la tarea')
    )
    
    # Ordering and dependencies
    order = models.IntegerField(
        _('orden'),
        default=0,
        help_text=_('Orden de ejecución en el workflow')
    )
    depends_on = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='dependent_tasks',
        verbose_name=_('depende de'),
        blank=True
    )
    
    # Execution settings
    timeout_minutes = models.IntegerField(
        _('tiempo de espera (minutos)'),
        default=30
    )
    retry_on_failure = models.BooleanField(
        _('reintentar en caso de fallo'),
        default=False
    )
    continue_on_failure = models.BooleanField(
        _('continuar en caso de fallo'),
        default=False
    )
    
    class Meta:
        verbose_name = _('tarea de workflow')
        verbose_name_plural = _('tareas de workflow')
        ordering = ['workflow', 'order']
        unique_together = ['workflow', 'order']
    
    def __str__(self):
        return f"{self.workflow.name} - {self.name}"


class WorkflowExecution(BaseModel):
    """
    Model for workflow executions.
    Records of workflow runs.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pendiente')
        RUNNING = 'running', _('Ejecutando')
        SUCCESS = 'success', _('Exitoso')
        FAILED = 'failed', _('Fallido')
        CANCELLED = 'cancelled', _('Cancelado')
        TIMEOUT = 'timeout', _('Tiempo Agotado')
    
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name=_('workflow')
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
    
    # Input/Output
    input_data = models.JSONField(
        _('datos de entrada'),
        default=dict,
        blank=True
    )
    output_data = models.JSONField(
        _('datos de salida'),
        default=dict,
        blank=True
    )
    
    # Execution context
    trigger_source = models.CharField(
        _('fuente de activación'),
        max_length=100,
        blank=True
    )
    trigger_data = models.JSONField(
        _('datos de activación'),
        default=dict,
        blank=True
    )
    
    # Results
    logs = models.TextField(
        _('logs'),
        blank=True
    )
    error_message = models.TextField(
        _('mensaje de error'),
        blank=True
    )
    
    # Metrics
    tasks_total = models.IntegerField(
        _('total de tareas'),
        default=0
    )
    tasks_completed = models.IntegerField(
        _('tareas completadas'),
        default=0
    )
    tasks_failed = models.IntegerField(
        _('tareas fallidas'),
        default=0
    )
    
    # Celery task
    task_id = models.CharField(
        _('ID de tarea'),
        max_length=255,
        blank=True
    )
    
    class Meta:
        verbose_name = _('ejecución de workflow')
        verbose_name_plural = _('ejecuciones de workflow')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['task_id']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} - {self.status} ({self.created_at})"
    
    @property
    def duration(self):
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return round(delta.total_seconds(), 2)
        return None
    
    @property
    def progress_percentage(self):
        """Calculate execution progress percentage."""
        if self.tasks_total == 0:
            return 0.0
        return round((self.tasks_completed / self.tasks_total) * 100, 2)
    
    def can_cancel(self):
        """Check if execution can be cancelled."""
        return self.status in ['pending', 'running']
    
    def can_retry(self):
        """Check if execution can be retried."""
        return self.status == 'failed'


class TaskExecution(models.Model):
    """
    Model for individual task executions within a workflow execution.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pendiente')
        RUNNING = 'running', _('Ejecutando')
        SUCCESS = 'success', _('Exitoso')
        FAILED = 'failed', _('Fallido')
        SKIPPED = 'skipped', _('Omitido')
    
    workflow_execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.CASCADE,
        related_name='task_executions',
        verbose_name=_('ejecución de workflow')
    )
    task = models.ForeignKey(
        WorkflowTask,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name=_('tarea')
    )
    
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
    input_data = models.JSONField(
        _('datos de entrada'),
        default=dict,
        blank=True
    )
    output_data = models.JSONField(
        _('datos de salida'),
        default=dict,
        blank=True
    )
    logs = models.TextField(
        _('logs'),
        blank=True
    )
    error_message = models.TextField(
        _('mensaje de error'),
        blank=True
    )
    
    retry_count = models.IntegerField(
        _('número de reintentos'),
        default=0
    )
    
    class Meta:
        verbose_name = _('ejecución de tarea')
        verbose_name_plural = _('ejecuciones de tareas')
        ordering = ['workflow_execution', 'task__order']
    
    def __str__(self):
        return f"{self.task.name} - {self.status}"
    
    @property
    def duration(self):
        """Calculate task execution duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return round(delta.total_seconds(), 2)
        return None


class AutomationRule(BaseModel):
    """
    Model for automation rules.
    Defines automatic triggering of workflows based on conditions.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Activo')
        INACTIVE = 'inactive', _('Inactivo')
    
    name = models.CharField(
        _('nombre'),
        max_length=255
    )
    description = models.TextField(
        _('descripción'),
        blank=True
    )
    status = models.CharField(
        _('estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    # Trigger conditions
    trigger_event = models.CharField(
        _('evento activador'),
        max_length=100,
        choices=[
            ('detection_created', _('Detección Creada')),
            ('monitor_alert', _('Alerta de Monitor')),
            ('data_updated', _('Datos Actualizados')),
            ('schedule', _('Programado')),
            ('threshold_exceeded', _('Umbral Excedido')),
        ]
    )
    conditions = models.JSONField(
        _('condiciones'),
        default=dict,
        blank=True,
        help_text=_('Condiciones que deben cumplirse para activar')
    )
    
    # Action
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='automation_rules',
        verbose_name=_('workflow a ejecutar')
    )
    workflow_input = models.JSONField(
        _('entrada del workflow'),
        default=dict,
        blank=True,
        help_text=_('Datos de entrada para el workflow')
    )
    
    # Related objects
    monitors = models.ManyToManyField(
        Monitor,
        related_name='automation_rules',
        verbose_name=_('monitores'),
        blank=True
    )
    data_sources = models.ManyToManyField(
        DataSource,
        related_name='automation_rules',
        verbose_name=_('fuentes de datos'),
        blank=True
    )
    
    # Throttling
    throttle_minutes = models.IntegerField(
        _('minutos de espera'),
        default=0,
        help_text=_('Minutos a esperar antes de activar nuevamente')
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
        verbose_name = _('regla de automatización')
        verbose_name_plural = _('reglas de automatización')
        ordering = ['name']
        indexes = [
            models.Index(fields=['trigger_event', 'status']),
            models.Index(fields=['status', 'is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def is_throttled(self):
        """Check if rule is currently throttled."""
        if self.throttle_minutes == 0 or not self.last_triggered:
            return False
        
        time_since_last = timezone.now() - self.last_triggered
        return time_since_last.total_seconds() < self.throttle_minutes * 60
    
    def can_trigger(self):
        """Check if rule can be triggered."""
        return self.status == 'active' and self.is_active and not self.is_throttled()
    
    def increment_trigger(self):
        """Increment trigger count and update timestamp."""
        self.trigger_count += 1
        self.last_triggered = timezone.now()
        self.save(update_fields=['trigger_count', 'last_triggered'])


class WorkflowSchedule(BaseModel):
    """
    Model for scheduled workflow executions.
    """
    
    class ScheduleType(models.TextChoices):
        INTERVAL = 'interval', _('Intervalo')
        CRON = 'cron', _('Cron')
        ONCE = 'once', _('Una vez')
    
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name=_('workflow')
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
        blank=True
    )
    cron_expression = models.CharField(
        _('expresión cron'),
        max_length=100,
        blank=True
    )
    scheduled_time = models.DateTimeField(
        _('hora programada'),
        null=True,
        blank=True
    )
    
    # Input data
    input_data = models.JSONField(
        _('datos de entrada'),
        default=dict,
        blank=True
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
        verbose_name = _('programación de workflow')
        verbose_name_plural = _('programaciones de workflows')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow', 'is_enabled']),
            models.Index(fields=['next_run', 'is_enabled']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.workflow.name}"
