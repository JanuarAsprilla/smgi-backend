"""
Admin configuration for Agents app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AgentCategory,
    Agent,
    AgentExecution,
    AgentSchedule,
    AgentRating,
    AgentTemplate
)


@admin.register(AgentCategory)
class AgentCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for AgentCategory model."""
    list_display = ['name', 'icon', 'color_badge', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    def color_badge(self, obj):
        """Display color badge."""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 15px; border-radius: 3px;">{}</span>',
            obj.color,
            obj.color
        )
    color_badge.short_description = 'Color'


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """Admin configuration for Agent model."""
    list_display = ['name', 'agent_type', 'version', 'status_badge', 'is_public', 'is_verified', 'rating', 'execution_count', 'created_at']
    list_filter = ['agent_type', 'status', 'is_public', 'is_verified', 'created_at']
    search_fields = ['name', 'description', 'tags']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at', 'execution_count', 'success_count', 'failure_count', 'downloads', 'rating', 'success_rate']
    filter_horizontal = []
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'category', 'agent_type', 'version', 'status')
        }),
        ('Código y Configuración', {
            'fields': ('code', 'requirements', 'parameters_schema', 'default_parameters')
        }),
        ('Publicación', {
            'fields': ('is_public', 'is_verified', 'tags', 'metadata')
        }),
        ('Estadísticas', {
            'fields': ('execution_count', 'success_count', 'failure_count', 'success_rate', 'downloads', 'rating'),
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
            'published': 'green',
            'archived': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(AgentExecution)
class AgentExecutionAdmin(admin.ModelAdmin):
    """Admin configuration for AgentExecution model."""
    list_display = ['id', 'agent', 'status_badge', 'started_at', 'completed_at', 'duration_display', 'created_by', 'created_at']
    list_filter = ['status', 'started_at', 'agent']
    search_fields = ['agent__name', 'name', 'task_id']
    readonly_fields = ['agent', 'status', 'started_at', 'completed_at', 'output_data', 'output_layers', 
                      'logs', 'error_message', 'processing_time', 'memory_usage', 'task_id', 
                      'created_by', 'updated_by', 'created_at', 'updated_at']
    filter_horizontal = ['input_layers', 'input_datasets']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('agent', 'name', 'status')
        }),
        ('Entrada', {
            'fields': ('input_layers', 'input_datasets', 'parameters')
        }),
        ('Ejecución', {
            'fields': ('started_at', 'completed_at', 'processing_time', 'memory_usage', 'task_id')
        }),
        ('Resultados', {
            'fields': ('output_data', 'output_layers', 'logs', 'error_message'),
            'classes': ('collapse',)
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
            'cancelled': 'orange'
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


@admin.register(AgentSchedule)
class AgentScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for AgentSchedule model."""
    list_display = ['name', 'agent', 'schedule_type', 'is_enabled', 'last_run', 'next_run', 'run_count']
    list_filter = ['schedule_type', 'is_enabled', 'is_active', 'created_at']
    search_fields = ['name', 'agent__name']
    readonly_fields = ['last_run', 'next_run', 'run_count', 'created_by', 'updated_by', 'created_at', 'updated_at']
    filter_horizontal = ['input_layers', 'input_datasets']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'agent')
        }),
        ('Programación', {
            'fields': ('schedule_type', 'interval_minutes', 'cron_expression', 'scheduled_time')
        }),
        ('Entrada', {
            'fields': ('input_layers', 'input_datasets', 'parameters')
        }),
        ('Estado', {
            'fields': ('is_enabled', 'is_active', 'last_run', 'next_run', 'run_count')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AgentRating)
class AgentRatingAdmin(admin.ModelAdmin):
    """Admin configuration for AgentRating model."""
    list_display = ['agent', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['agent__name', 'user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AgentTemplate)
class AgentTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for AgentTemplate model."""
    list_display = ['name', 'agent_type', 'category', 'usage_count', 'is_featured', 'is_active']
    list_filter = ['agent_type', 'is_featured', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'tags']
    readonly_fields = ['usage_count', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'category', 'agent_type')
        }),
        ('Plantilla', {
            'fields': ('code_template', 'parameters_schema', 'default_parameters')
        }),
        ('Presentación', {
            'fields': ('tags', 'thumbnail', 'is_featured')
        }),
        ('Estadísticas', {
            'fields': ('usage_count',),
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
