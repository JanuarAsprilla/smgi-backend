# apps/reports/admin.py
"""
SMGI Backend - Reports Admin
Sistema de Monitoreo Geoespacial Inteligente
Configuración del panel de administración de Django para la app de informes.
"""
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin # Opcional si se usan campos geoespaciales
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from datetime import timedelta

from apps.reports.models import (
    Report, ReportTemplate, GeneratedReport, ReportSchedule,
    ReportExecution, NotificationPreference, ReportType,
    ReportFormat, ReportStatus, ReportParameter, ReportSection
)
# Importar modelos relacionados
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin para Reportes"""
    
    list_display = (
        'name', 'report_type', 'format_type', 'service_name', 'layer_name',
        'is_scheduled', 'created_by_name', 'last_generated', 'generation_count'
    )
    list_filter = (
        'report_type', 'format_type', 'is_scheduled', 'created', 'last_generated', 'created_by'
    )
    search_fields = (
        'name', 'description', 'service__name', 'layer__name',
        'created_by__username', 'created_by__email'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'last_generated', 'generation_count', 'created_by_name'
    )
    raw_id_fields = ('service', 'layer', 'monitoring_job', 'alert', 'template', 'created_by')
    filter_horizontal = ('notify_users',)
    date_hierarchy = 'created'
    ordering = ['name']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('name', 'description', 'report_type', 'format_type')
        }),
        ('Fuente de Datos', {
            'fields': ('service', 'layer', 'monitoring_job', 'alert')
        }),
        ('Configuración del Informe', {
            'fields': ('template', 'parameters')
        }),
        ('Programación', {
            'fields': ('is_scheduled', 'schedule_expression')
        }),
        ('Notificación', {
            'fields': ('notify_on_completion', 'notify_users')
        }),
        ('Metadatos', {
            'fields': ('created_by', 'created_by_name', 'last_generated', 'generation_count', 'created', 'modified')
        }),
    )
    
    actions = ['make_scheduled', 'make_unscheduled', 'generate_selected']
    
    def service_name(self, obj):
        return obj.service.name if obj.service else '-'
    service_name.short_description = _('Service')
    service_name.admin_order_field = 'service__name'
    
    def layer_name(self, obj):
        return obj.layer.name if obj.layer else '-'
    layer_name.short_description = _('Layer')
    layer_name.admin_order_field = 'layer__name'
    
    def created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else '-'
    created_by_name.short_description = _('Created By')
    created_by_name.admin_order_field = 'created_by__get_full_name'
    
    def make_scheduled(self, request, queryset):
        queryset.update(is_scheduled=True)
    make_scheduled.short_description = _("Mark selected reports as scheduled")
    
    def make_unscheduled(self, request, queryset):
        queryset.update(is_scheduled=False)
    make_unscheduled.short_description = _("Mark selected reports as unscheduled")
    
    def generate_selected(self, request, queryset):
        from apps.reports.tasks import generate_report
        for report in queryset:
            generate_report.delay(str(report.id))
        self.message_user(request, _("Selected reports generation initiated"))
    generate_selected.short_description = _("Generate selected reports")


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    """Admin para Plantillas de Informes"""
    
    list_display = (
        'name', 'template_type', 'format_type', 'is_active', 'author_name', 'created'
    )
    list_filter = (
        'template_type', 'format_type', 'is_active', 'created', 'author'
    )
    search_fields = (
        'name', 'description', 'author__username', 'author__email'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'author_name'
    )
    raw_id_fields = ('author',)
    date_hierarchy = 'created'
    ordering = ['name']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('name', 'description', 'template_type', 'format_type')
        }),
        ('Contenido', {
            'fields': ('template_file', 'template_content', 'default_parameters')
        }),
        ('Configuración', {
            'fields': ('is_active', 'version')
        }),
        ('Metadatos', {
            'fields': ('author', 'author_name', 'created', 'modified')
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'preview_template', 'validate_template']
    
    def author_name(self, obj):
        return obj.author.get_full_name() if obj.author else '-'
    author_name.short_description = _('Author')
    author_name.admin_order_field = 'author__get_full_name'
    
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = _("Mark selected templates as active")
    
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = _("Mark selected templates as inactive")
    
    def preview_template(self, request, queryset):
        # Esta acción podría abrir una ventana modal o redirigir a una vista de previsualización
        # Para simplificar, solo mostramos un mensaje
        self.message_user(request, _("Preview functionality not implemented in admin. Use API or frontend."))
    preview_template.short_description = _("Preview selected templates")
    
    def validate_template(self, request, queryset):
        # Esta acción podría validar el contenido de las plantillas
        # Para simplificar, solo mostramos un mensaje
        self.message_user(request, _("Validation functionality not implemented in admin. Use API or frontend."))
    validate_template.short_description = _("Validate selected templates")


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    """Admin para Informes Generados"""
    
    list_display = (
        'report_name', 'format_type', 'status', 'file_name', 'file_size_bytes',
        'generation_duration_seconds', 'generated_by_name', 'created'
    )
    list_filter = (
        'format_type', 'status', 'created', 'generated_by', 'report__service', 'report__layer'
    )
    search_fields = (
        'report__name', 'report__description', 'generated_by__username', 'generated_by__email', 'file_name'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'file_name', 'file_url', 'is_complete', 'is_failed',
        'generation_duration_seconds', 'generated_by_name'
    )
    raw_id_fields = ('report', 'generated_by')
    date_hierarchy = 'created'
    ordering = ['-created']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('report', 'report_name', 'generated_by', 'generated_by_name')
        }),
        ('Archivo', {
            'fields': ('file', 'file_name', 'file_url', 'file_size_bytes', 'file_checksum')
        }),
        ('Formato y Estado', {
            'fields': ('format_type', 'status', 'parameters_used')
        }),
        ('Métricas', {
            'fields': (
                'generation_duration_ms', 'generation_duration_seconds',
                'record_count', 'page_count', 'is_complete', 'is_failed'
            )
        }),
        ('Errores', {
            'fields': ('error_message',)
        }),
        ('Notificación', {
            'fields': ('notification_sent',)
        }),
        ('Fechas', {
            'fields': ('started_at', 'completed_at', 'created', 'modified')
        }),
    )
    
    actions = ['download_selected', 're_generate_selected']
    
    def report_name(self, obj):
        return obj.report.name if obj.report else '-'
    report_name.short_description = _('Report')
    report_name.admin_order_field = 'report__name'
    
    def generated_by_name(self, obj):
        return obj.generated_by.get_full_name() if obj.generated_by else '-'
    generated_by_name.short_description = _('Generated By')
    generated_by_name.admin_order_field = 'generated_by__get_full_name'
    
    def download_selected(self, request, queryset):
        # Esta acción podría generar un archivo zip con los informes seleccionados
        # Para simplificar, solo mostramos un mensaje
        self.message_user(request, _("Download functionality not implemented in admin. Use API or frontend."))
    download_selected.short_description = _("Download selected reports")
    
    def re_generate_selected(self, request, queryset):
        from apps.reports.tasks import generate_report
        for generated_report in queryset:
            generate_report.delay(str(generated_report.report.id), force=True)
        self.message_user(request, _("Selected reports re-generation initiated"))
    re_generate_selected.short_description = _("Re-generate selected reports")


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    """Admin para Programaciones de Informes"""
    
    list_display = (
        'name', 'report_name', 'is_active', 'schedule_expression',
        'last_run', 'next_run', 'consecutive_failures', 'created_by_name'
    )
    list_filter = (
        'is_active', 'created', 'last_run', 'next_run', 'created_by',
        'report__service', 'report__layer'
    )
    search_fields = (
        'name', 'description', 'report__name', 'created_by__username', 'created_by__email'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'last_run', 'last_successful_run',
        'next_run', 'consecutive_failures', 'created_by_name'
    )
    raw_id_fields = ('report', 'created_by')
    filter_horizontal = ('notify_users',)
    date_hierarchy = 'created'
    ordering = ['name']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('name', 'description', 'report', 'report_name')
        }),
        ('Programación', {
            'fields': ('schedule_expression', 'is_active', 'run_on_weekends', 'run_on_holidays', 'max_runtime_minutes')
        }),
        ('Notificación', {
            'fields': ('notify_on_completion', 'notify_on_failure', 'notify_users')
        }),
        ('Metadatos', {
            'fields': (
                'created_by', 'created_by_name',
                'last_run', 'last_successful_run', 'next_run',
                'consecutive_failures', 'created', 'modified'
            )
        }),
    )
    
    actions = ['toggle_active', 'run_now']
    
    def report_name(self, obj):
        return obj.report.name if obj.report else '-'
    report_name.short_description = _('Report')
    report_name.admin_order_field = 'report__name'
    
    def created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else '-'
    created_by_name.short_description = _('Created By')
    created_by_name.admin_order_field = 'created_by__get_full_name'
    
    def toggle_active(self, request, queryset):
        for schedule in queryset:
            schedule.is_active = not schedule.is_active
            schedule.save(update_fields=['is_active'])
        self.message_user(request, _("Selected schedules toggled"))
    toggle_active.short_description = _("Toggle active status for selected schedules")
    
    def run_now(self, request, queryset):
        from apps.reports.tasks import run_scheduled_report_now
        for schedule in queryset:
            run_scheduled_report_now.delay(str(schedule.id))
        self.message_user(request, _("Selected schedules run initiated"))
    run_now.short_description = _("Run selected schedules now")


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    """Admin para Ejecuciones de Programaciones de Informes"""
    
    list_display = (
        'schedule_name', 'success', 'duration_seconds', 'started_at', 'completed_at'
    )
    list_filter = (
        'success', 'started_at', 'completed_at', 'schedule__report__service', 'schedule__report__layer'
    )
    search_fields = (
        'schedule__name', 'schedule__report__name', 'error_message'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'schedule_name', 'report_name', 'duration_seconds'
    )
    raw_id_fields = ('schedule',)
    date_hierarchy = 'started_at'
    ordering = ['-started_at']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('schedule', 'schedule_name', 'report_name')
        }),
        ('Ejecución', {
            'fields': ('started_at', 'completed_at', 'duration_seconds', 'success', 'error_message')
        }),
        ('Métricas de Rendimiento', {
            'fields': ('memory_usage_mb', 'cpu_usage_percent', 'generation_duration_ms')
        }),
        ('Resultados', {
            'fields': ('reports_generated', 'record_count', 'page_count')
        }),
        ('Registro Detallado', {
            'fields': ('execution_log', 'performance_metrics')
        }),
        ('Fechas', {
            'fields': ('created', 'modified')
        }),
    )
    
    def schedule_name(self, obj):
        return obj.schedule.name if obj.schedule else '-'
    schedule_name.short_description = _('Schedule')
    schedule_name.admin_order_field = 'schedule__name'
    
    def report_name(self, obj):
        return obj.schedule.report.name if obj.schedule and obj.schedule.report else '-'
    report_name.short_description = _('Report')
    report_name.admin_order_field = 'schedule__report__name'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin para Preferencias de Notificación"""
    
    list_display = (
        'user_email', 'email_enabled', 'sms_enabled', 'push_enabled',
        'in_app_enabled', 'quiet_hours_enabled', 'digest_enabled'
    )
    list_filter = (
        'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
        'quiet_hours_enabled', 'digest_enabled', 'created'
    )
    search_fields = (
        'user__email', 'user__username'
    )
    readonly_fields = (
        'id', 'created', 'modified'
    )
    raw_id_fields = ('user',)
    date_hierarchy = 'created'
    ordering = ['user__email']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user', 'user_email')
        }),
        ('Canales Habilitados', {
            'fields': ('email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled')
        }),
        ('Tipos de Notificaciones por Canal', {
            'fields': (
                'email_alert_notifications', 'email_report_notifications',
                'email_system_notifications'
            )
        }),
        ('Horarios', {
            'fields': (
                'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end'
            )
        }),
        ('Frecuencia', {
            'fields': ('digest_enabled', 'digest_frequency')
        }),
        ('Severidad Mínima', {
            'fields': ('min_alert_severity',)
        }),
        ('Fechas', {
            'fields': ('created', 'modified')
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else '-'
    user_email.short_description = _('User Email')
    user_email.admin_order_field = 'user__email'
