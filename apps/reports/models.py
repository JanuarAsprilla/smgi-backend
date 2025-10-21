# apps/reports/models.py
"""
SMGI Backend - Reports Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos para generación, almacenamiento y programación de informes
"""
import uuid
import os
from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel, SoftDeletableModel
from apps.common.models import BaseModel
from apps.authentication.models import User
# Asumimos que estas apps existen y tienen estos modelos
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert


class ReportType(models.TextChoices):
    """Tipos de informes disponibles en el sistema"""
    MONITORING_SUMMARY = 'monitoring_summary', _('Monitoring Summary')
    ALERT_HISTORY = 'alert_history', _('Alert History')
    DATA_QUALITY = 'data_quality', _('Data Quality Report')
    PERFORMANCE = 'performance', _('Performance Report')
    CHANGE_DETECTION = 'change_detection', _('Change Detection Report')
    CUSTOM = 'custom', _('Custom Report')
    LAYER_INVENTORY = 'layer_inventory', _('Layer Inventory')
    SERVICE_HEALTH = 'service_health', _('Service Health Report')
    USER_ACTIVITY = 'user_activity', _('User Activity Report')
    SYSTEM_AUDIT = 'system_audit', _('System Audit Report')


class ReportFormat(models.TextChoices):
    """Formatos de salida para los informes"""
    PDF = 'pdf', _('PDF Document')
    EXCEL = 'xlsx', _('Excel Spreadsheet')
    CSV = 'csv', _('CSV File')
    GEOJSON = 'geojson', _('GeoJSON File')
    HTML = 'html', _('HTML Document')
    DOCX = 'docx', _('Word Document')
    JSON = 'json', _('JSON Data')
    ZIP = 'zip', _('Zipped Archive')


class ReportStatus(models.TextChoices):
    """Estados del proceso de generación de informes"""
    PENDING = 'pending', _('Pending')
    GENERATING = 'generating', _('Generating')
    COMPLETED = 'completed', _('Completed')
    FAILED = 'failed', _('Failed')
    CANCELLED = 'cancelled', _('Cancelled')


class ReportTemplate(BaseModel):
    """
    Modelo para plantillas de informes
    """
    name = models.CharField(_('Template Name'), max_length=200, unique=True)
    description = models.TextField(_('Description'), blank=True)
    template_type = models.CharField(
        _('Template Type'),
        max_length=20,
        choices=ReportType.choices,
        default=ReportType.CUSTOM,
        db_index=True
    )
    format_type = models.CharField(
        _('Format Type'),
        max_length=10,
        choices=ReportFormat.choices,
        default=ReportFormat.HTML,
        db_index=True
    )
    
    # Contenido de la plantilla
    template_file = models.FileField(
        _('Template File'),
        upload_to='reports/templates/',
        blank=True,
        help_text=_('File containing the report template (e.g., .html, .tex, .docx)')
    )
    template_content = models.TextField(
        _('Template Content'),
        blank=True,
        help_text=_('Raw template content (alternative to uploading a file)')
    )
    
    # Configuración
    is_active = models.BooleanField(_('Is Active'), default=True)
    default_parameters = JSONField(
        _('Default Parameters'),
        default=dict,
        blank=True,
        help_text=_('Default parameters for this template')
    )
    
    # Metadata
    version = models.CharField(_('Version'), max_length=20, blank=True)
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_report_templates'
    )
    
    class Meta:
        db_table = 'reports_template'
        verbose_name = _('Report Template')
        verbose_name_plural = _('Report Templates')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['template_type']),
            models.Index(fields=['format_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['author']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class Report(BaseModel):
    """
    Modelo para definir informes configurables
    """
    name = models.CharField(_('Report Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    report_type = models.CharField(
        _('Report Type'),
        max_length=30,
        choices=ReportType.choices,
        default=ReportType.CUSTOM,
        db_index=True
    )
    
    # Fuente de datos
    service = models.ForeignKey(
        ArcGISService,
        on_delete=models.CASCADE,
        related_name='reports',
        blank=True,
        null=True
    )
    layer = models.ForeignKey(
        SpatialLayer,
        on_delete=models.CASCADE,
        related_name='reports',
        blank=True,
        null=True
    )
    monitoring_job = models.ForeignKey(
        MonitoringJob,
        on_delete=models.CASCADE,
        related_name='reports',
        blank=True,
        null=True
    )
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name='reports',
        blank=True,
        null=True
    )
    
    # Configuración del informe
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )
    format_type = models.CharField(
        _('Output Format'),
        max_length=10,
        choices=ReportFormat.choices,
        default=ReportFormat.PDF,
        db_index=True
    )
    parameters = JSONField(
        _('Parameters'),
        default=dict,
        blank=True,
        help_text=_('Parameters for report generation')
    )
    
    # Configuración de programación
    is_scheduled = models.BooleanField(_('Is Scheduled'), default=False)
    schedule_expression = models.CharField(
        _('Schedule Expression'),
        max_length=100,
        blank=True,
        help_text=_('Cron expression for scheduling (e.g., "0 2 * * *")')
    )
    
    # Configuración de notificación
    notify_on_completion = models.BooleanField(_('Notify on Completion'), default=True)
    notify_users = models.ManyToManyField(
        User,
        related_name='subscribed_reports',
        blank=True,
        verbose_name=_('Notify Users')
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_reports'
    )
    last_generated = models.DateTimeField(_('Last Generated'), blank=True, null=True)
    generation_count = models.PositiveIntegerField(_('Generation Count'), default=0)
    
    class Meta:
        db_table = 'reports_report'
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['report_type']),
            models.Index(fields=['format_type']),
            models.Index(fields=['is_scheduled']),
            models.Index(fields=['service']),
            models.Index(fields=['layer']),
            models.Index(fields=['monitoring_job']),
            models.Index(fields=['alert']),
            models.Index(fields=['template']),
            models.Index(fields=['created_by']),
            models.Index(fields=['last_generated']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class GeneratedReport(BaseModel):
    """
    Modelo para informes generados
    """
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='generated_reports'
    )
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reports'
    )
    
    # Identificación
    report_id = models.CharField(
        _('Report ID'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('Unique identifier for this generated report')
    )
    
    # Contenido del informe
    file = models.FileField(
        _('Report File'),
        upload_to='reports/generated/',
        blank=True,
        help_text=_('Generated report file')
    )
    file_size_bytes = models.PositiveIntegerField(_('File Size (bytes)'), default=0)
    file_checksum = models.CharField(
        _('File Checksum'),
        max_length=64,
        blank=True,
        help_text=_('SHA-256 checksum of the report file')
    )
    
    # Metadatos de generación
    format_type = models.CharField(
        _('Output Format'),
        max_length=10,
        choices=ReportFormat.choices,
        default=ReportFormat.PDF,
        db_index=True
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True
    )
    parameters_used = JSONField(
        _('Parameters Used'),
        default=dict,
        blank=True,
        help_text=_('Parameters used for this specific generation')
    )
    generation_duration_ms = models.PositiveIntegerField(
        _('Generation Duration (ms)'),
        default=0,
        help_text=_('Time taken to generate the report in milliseconds')
    )
    
    # Fechas
    started_at = models.DateTimeField(_('Started At'), auto_now_add=True)
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)
    
    # Resultados
    record_count = models.PositiveIntegerField(_('Record Count'), default=0)
    page_count = models.PositiveIntegerField(_('Page Count'), default=0, blank=True, null=True)
    
    # Errores
    error_message = models.TextField(_('Error Message'), blank=True)
    
    # Notificación
    notification_sent = models.BooleanField(_('Notification Sent'), default=False)
    
    class Meta:
        db_table = 'reports_generated'
        verbose_name = _('Generated Report')
        verbose_name_plural = _('Generated Reports')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['report', '-started_at']),
            models.Index(fields=['report_id']),
            models.Index(fields=['format_type']),
            models.Index(fields=['status']),
            models.Index(fields=['generated_by']),
            models.Index(fields=['started_at']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['notification_sent']),
        ]
    
    def __str__(self):
        return f"{self.report.name} - {self.started_at.strftime('%Y-%m-%d %H:%M')} ({self.get_status_display()})"

    @property
    def file_name(self):
        """Get the file name of the generated report"""
        if self.file:
            return os.path.basename(self.file.name)
        return None

    @property
    def file_url(self):
        """Get the URL of the generated report file"""
        if self.file:
            return self.file.url
        return None

    @property
    def is_complete(self):
        """Check if report generation is complete"""
        return self.status == ReportStatus.COMPLETED

    @property
    def is_failed(self):
        """Check if report generation failed"""
        return self.status == ReportStatus.FAILED

    def mark_as_generating(self):
        """Mark report as generating"""
        self.status = ReportStatus.GENERATING
        self.save(update_fields=['status'])

    def mark_as_completed(self, file_path=None, file_size=None, checksum=None, duration_ms=None, record_count=None, page_count=None):
        """Mark report as completed"""
        self.status = ReportStatus.COMPLETED
        self.completed_at = timezone.now()
        if file_path:
            self.file.name = file_path
        if file_size:
            self.file_size_bytes = file_size
        if checksum:
            self.file_checksum = checksum
        if duration_ms:
            self.generation_duration_ms = duration_ms
        if record_count:
            self.record_count = record_count
        if page_count:
            self.page_count = page_count
        self.save(update_fields=[
            'status', 'completed_at', 'file', 'file_size_bytes',
            'file_checksum', 'generation_duration_ms', 'record_count', 'page_count'
        ])

    def mark_as_failed(self, error_message=None, duration_ms=None):
        """Mark report as failed"""
        self.status = ReportStatus.FAILED
        self.completed_at = timezone.now()
        if error_message:
            self.error_message = error_message
        if duration_ms:
            self.generation_duration_ms = duration_ms
        self.save(update_fields=['status', 'completed_at', 'error_message', 'generation_duration_ms'])

    def mark_as_cancelled(self):
        """Mark report as cancelled"""
        self.status = ReportStatus.CANCELLED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])

    def increment_generation_count(self):
        """Increment the generation count of the parent report"""
        if self.report:
            self.report.generation_count += 1
            self.report.last_generated = timezone.now()
            self.report.save(update_fields=['generation_count', 'last_generated'])


class ReportSchedule(BaseModel):
    """
    Modelo para programar la generación automática de informes
    """
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    
    # Programación
    name = models.CharField(_('Schedule Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    schedule_expression = models.CharField(
        _('Schedule Expression'),
        max_length=100,
        help_text=_('Cron expression for scheduling (e.g., "0 2 * * *")')
    )
    is_active = models.BooleanField(_('Is Active'), default=True)
    
    # Configuración de ejecución
    run_on_weekends = models.BooleanField(_('Run on Weekends'), default=True)
    run_on_holidays = models.BooleanField(_('Run on Holidays'), default=False)
    max_runtime_minutes = models.PositiveIntegerField(
        _('Max Runtime (minutes)'),
        default=60,
        validators=[MinValueValidator(1), MaxValueValidator(1440)] # 1 min to 24 hours
    )
    
    # Notificación
    notify_on_completion = models.BooleanField(_('Notify on Completion'), default=True)
    notify_on_failure = models.BooleanField(_('Notify on Failure'), default=True)
    notify_users = models.ManyToManyField(
        User,
        related_name='scheduled_report_subscriptions',
        blank=True,
        verbose_name=_('Notify Users')
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_report_schedules'
    )
    last_run = models.DateTimeField(_('Last Run'), blank=True, null=True)
    last_successful_run = models.DateTimeField(_('Last Successful Run'), blank=True, null=True)
    next_run = models.DateTimeField(_('Next Scheduled Run'), blank=True, null=True)
    consecutive_failures = models.PositiveIntegerField(_('Consecutive Failures'), default=0)
    
    class Meta:
        db_table = 'reports_schedule'
        verbose_name = _('Report Schedule')
        verbose_name_plural = _('Report Schedules')
        ordering = ['name']
        indexes = [
            models.Index(fields=['report']),
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_run']),
            models.Index(fields=['next_run']),
            models.Index(fields=['created_by']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.report.name})"

    @property
    def is_overdue(self):
        """Check if schedule is overdue for execution"""
        if not self.next_run or not self.is_active:
            return False
        return timezone.now() > self.next_run

    def calculate_next_run(self):
        """
        Calculate next run time based on schedule expression.
        Uses croniter library for robust cron parsing.
        """
        from django.utils import timezone
        try:
            from croniter import croniter
            # Asegurar que el schedule_expression es un cron válido
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

    @transaction.atomic # Asegura que la actualización del schedule y la creación de la ejecución sean atómicas
    def record_execution(self, success=True, error_message=None):
        """
        Record schedule execution result.
        Now uses signals or a separate Celery task for creating ReportExecution
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
        ReportExecution.objects.create(
            schedule=self,
            success=success,
            error_message=error_message or ''
        )
        
        # Disable schedule after too many consecutive failures
        if self.consecutive_failures >= 5:
            self.is_active = False
        
        # Guardar solo los campos actualizados
        update_fields = [
            'last_run', 'last_successful_run', 'consecutive_failures', 'is_active', 'next_run'
        ]
        self.save(update_fields=update_fields)


class ReportExecution(TimeStampedModel):
    """
    Modelo para registrar ejecuciones de programaciones de informes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(
        ReportSchedule,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    
    # Detalles de ejecución
    started_at = models.DateTimeField(_('Started At'), auto_now_add=True)
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(_('Duration (seconds)'), blank=True, null=True)
    
    # Resultados de ejecución
    success = models.BooleanField(_('Success'), default=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    reports_generated = models.PositiveIntegerField(_('Reports Generated'), default=0)
    
    # Métricas de rendimiento
    memory_usage_mb = models.PositiveIntegerField(_('Memory Usage (MB)'), blank=True, null=True)
    cpu_usage_percent = models.FloatField(_('CPU Usage (%)'), blank=True, null=True)
    
    # Registro detallado
    execution_log = JSONField(
        _('Execution Log'),
        default=list,
        blank=True,
        help_text=_('Registro detallado de pasos de ejecución')
    )
    performance_metrics = JSONField(
        _('Performance Metrics'),
        default=dict,
        blank=True
    )
    
    class Meta:
        db_table = 'reports_execution'
        verbose_name = _('Report Execution')
        verbose_name_plural = _('Report Executions')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['schedule', '-started_at']),
            models.Index(fields=['success']),
            models.Index(fields=['started_at']),
            models.Index(fields=['completed_at']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.schedule.name} - {status} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
    
    @transaction.atomic
    def mark_completed(self, success=True, error_message=None, reports_generated=0):
        """Marcar ejecución como completada"""
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        self.success = success
        if error_message:
            self.error_message = error_message
        self.reports_generated = reports_generated
        self.save(update_fields=[
            'completed_at', 'duration_seconds', 'success', 'error_message', 'reports_generated'
        ])
    
    @transaction.atomic
    def add_log_entry(self, level, message, **kwargs):
        """Agregar entrada al registro de ejecución"""
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


class ReportParameter(BaseModel):
    """
    Modelo para parámetros específicos de informes generados
    """
    generated_report = models.ForeignKey(
        GeneratedReport,
        on_delete=models.CASCADE,
        related_name='parameters'
    )
    name = models.CharField(_('Parameter Name'), max_length=100)
    value = models.TextField(_('Parameter Value'), blank=True)
    value_type = models.CharField(
        _('Value Type'),
        max_length=20,
        choices=[
            ('string', _('String')),
            ('integer', _('Integer')),
            ('float', _('Float')),
            ('boolean', _('Boolean')),
            ('date', _('Date')),
            ('datetime', _('DateTime')),
            ('list', _('List')),
            ('dict', _('Dictionary')),
        ],
        default='string'
    )
    
    class Meta:
        db_table = 'reports_parameter'
        verbose_name = _('Report Parameter')
        verbose_name_plural = _('Report Parameters')
        ordering = ['name']
        indexes = [
            models.Index(fields=['generated_report', 'name']),
            models.Index(fields=['name']),
            models.Index(fields=['value_type']),
        ]
        unique_together = ['generated_report', 'name']
    
    def __str__(self):
        return f"{self.generated_report.report.name} - {self.name}: {self.value}"


class ReportSection(BaseModel):
    """
    Modelo para secciones dentro de un informe (opcional)
    """
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='sections'
    )
    name = models.CharField(_('Section Name'), max_length=200)
    title = models.CharField(_('Section Title'), max_length=200, blank=True)
    description = models.TextField(_('Description'), blank=True)
    order = models.PositiveIntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Is Active'), default=True)
    content_template = models.TextField(
        _('Content Template'),
        blank=True,
        help_text=_('Template snippet for this section')
    )
    data_source = models.TextField(
        _('Data Source'),
        blank=True,
        help_text=_('SQL query or API endpoint to fetch data for this section')
    )
    
    class Meta:
        db_table = 'reports_section'
        verbose_name = _('Report Section')
        verbose_name_plural = _('Report Sections')
        ordering = ['report', 'order']
        indexes = [
            models.Index(fields=['report', 'order']),
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['report', 'name']
    
    def __str__(self):
        return f"{self.report.name} - {self.name}"
