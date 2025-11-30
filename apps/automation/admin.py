"""
Admin configuration for Automation app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Workflow,
    WorkflowTask,
    WorkflowExecution,
    TaskExecution,
    AutomationRule,
    WorkflowSchedule
)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin configuration for Workflow model."""
    list_display = ['name', 'status_badge', 'trigger_type', 'execution_count', 'success_rate_display', 'last_execution', 'is_active']
    list_filter = ['status', 'trigger_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'tags']
    readonly_fields = ['execution_count', 'success_count', 'failure_count', 'last_execution', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'status')
        }),
        ('Definición', {
            'fields': ('workflow_definition',)
        }),
        ('Activación', {
            'fields': ('trigger_type', 'trigger_config')
        }),
        ('Configuración de Ejecución', {
            'fields': ('timeout_minutes', 'retry_count')
        }),
        ('Estadísticas', {
            'fields': ('execution_count', 'success_count', 'failure_count', 'last_execution'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('tags', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'draft': 'gray',
            'active': 'green',
            'paused': 'orange',
            'archived': 'lightgray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def success_rate_display(self, obj):
        """Display success rate."""
        rate = obj.success_rate
        color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            rate
        )
    success_rate_display.short_description = 'Tasa de Éxito'


@admin.register(WorkflowTask)
class WorkflowTaskAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowTask model."""
    list_display = ['name', 'workflow', 'task_type', 'order', 'retry_on_failure', 'is_active']
    list_filter = ['task_type', 'retry_on_failure', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'workflow__name']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    filter_horizontal = ['depends_on']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('workflow', 'name', 'description', 'task_type')
        }),
        ('Configuración', {
            'fields': ('configuration',)
        }),
        ('Orden y Dependencias', {
            'fields': ('order', 'depends_on')
        }),
        ('Configuración de Ejecución', {
            'fields': ('timeout_minutes', 'retry_on_failure', 'continue_on_failure')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowExecution model."""
    list_display = ['id', 'workflow', 'status_badge', 'started_at', 'completed_at', 'duration_display', 'progress_display']
    list_filter = ['status', 'trigger_source', 'created_at']
    search_fields = ['workflow__name', 'task_id']
    readonly_fields = ['workflow', 'status', 'started_at', 'completed_at', 'input_data', 'output_data', 
                      'trigger_source', 'trigger_data', 'logs', 'error_message', 'tasks_total', 
                      'tasks_completed', 'tasks_failed', 'task_id', 'created_by', 'updated_by', 
                      'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('workflow', 'status')
        }),
        ('Ejecución', {
            'fields': ('started_at', 'completed_at', 'task_id')
        }),
        ('Entrada/Salida', {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        ('Activación', {
            'fields': ('trigger_source', 'trigger_data'),
            'classes': ('collapse',)
        }),
        ('Resultados', {
            'fields': ('logs', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Métricas', {
            'fields': ('tasks_total', 'tasks_completed', 'tasks_failed')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation."""
        return False
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'pending': 'gray',
            'running': 'blue',
            'success': 'green',
            'failed': 'red',
            'cancelled': 'orange',
            'timeout': 'darkred'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def duration_display(self, obj):
        """Display execution duration."""
        duration = obj.duration
        if duration:
            if duration < 60:
                return f"{duration:.1f}s"
            elif duration < 3600:
                return f"{duration/60:.1f}m"
            else:
                return f"{duration/3600:.1f}h"
        return "-"
    duration_display.short_description = 'Duración'
    
    def progress_display(self, obj):
        """Display execution progress."""
        progress = obj.progress_percentage
        return f"{progress:.0f}%"
    progress_display.short_description = 'Progreso'


@admin.register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    """Admin configuration for TaskExecution model."""
    list_display = ['task', 'workflow_execution', 'status_badge', 'started_at', 'completed_at', 'duration_display']
    list_filter = ['status', 'started_at']
    search_fields = ['task__name', 'workflow_execution__workflow__name']
    readonly_fields = ['workflow_execution', 'task', 'status', 'started_at', 'completed_at', 
                      'input_data', 'output_data', 'logs', 'error_message', 'retry_count']
    
    def has_add_permission(self, request):
        """Disable manual creation."""
        return False
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'pending': 'gray',
            'running': 'blue',
            'success': 'green',
            'failed': 'red',
            'skipped': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def duration_display(self, obj):
        """Display task duration."""
        duration = obj.duration
        if duration:
            return f"{duration:.2f}s"
        return "-"
    duration_display.short_description = 'Duración'


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    """Admin configuration for AutomationRule model."""
    list_display = ['name', 'status_badge', 'trigger_event', 'workflow', 'trigger_count', 'last_triggered', 'is_active']
    list_filter = ['status', 'trigger_event', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'workflow__name']
    readonly_fields = ['trigger_count', 'last_triggered', 'created_by', 'updated_by', 'created_at', 'updated_at']
    filter_horizontal = ['monitors', 'data_sources']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'status')
        }),
        ('Activación', {
            'fields': ('trigger_event', 'conditions')
        }),
        ('Acción', {
            'fields': ('workflow', 'workflow_input')
        }),
        ('Objetivos', {
            'fields': ('monitors', 'data_sources')
        }),
        ('Configuración', {
            'fields': ('throttle_minutes',)
        }),
        ('Estadísticas', {
            'fields': ('trigger_count', 'last_triggered'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'active': 'green',
            'inactive': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(WorkflowSchedule)
class WorkflowScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for WorkflowSchedule model."""
    list_display = ['name', 'workflow', 'schedule_type', 'is_enabled', 'last_run', 'next_run', 'run_count']
    list_filter = ['schedule_type', 'is_enabled', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'workflow__name']
    readonly_fields = ['last_run', 'next_run', 'run_count', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'workflow')
        }),
        ('Programación', {
            'fields': ('schedule_type', 'interval_minutes', 'cron_expression', 'scheduled_time')
        }),
        ('Entrada', {
            'fields': ('input_data',)
        }),
        ('Estado', {
            'fields': ('is_enabled', 'is_active', 'last_run', 'next_run', 'run_count')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
