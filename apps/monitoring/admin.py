"""
Admin configuration for Monitoring app.
"""
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html
from .models import (
    MonitoringProject,
    Monitor,
    Detection,
    ChangeRecord,
    MonitoringReport,
    Baseline
)


@admin.register(MonitoringProject)
class MonitoringProjectAdmin(GISModelAdmin):
    """Admin configuration for MonitoringProject model."""
    list_display = ['name', 'status_badge', 'start_date', 'end_date', 'is_active', 'created_at']
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'status')
        }),
        ('Área de Interés', {
            'fields': ('area_of_interest',)
        }),
        ('Configuración', {
            'fields': ('configuration', 'tags', 'metadata')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date')
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
            'paused': 'orange',
            'completed': 'blue',
            'archived': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    """Admin configuration for Monitor model."""
    list_display = ['name', 'project', 'monitor_type', 'status_badge', 'check_interval', 'last_check', 'detection_count', 'is_active']
    list_filter = ['monitor_type', 'status', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'project__name']
    readonly_fields = ['last_check', 'next_check', 'check_count', 'detection_count', 'created_by', 'updated_by', 'created_at', 'updated_at']
    filter_horizontal = ['layers', 'data_sources']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('project', 'name', 'description', 'monitor_type', 'status')
        }),
        ('Objetivos de Monitoreo', {
            'fields': ('layers', 'data_sources')
        }),
        ('Configuración de Análisis', {
            'fields': ('agent', 'parameters')
        }),
        ('Programación', {
            'fields': ('check_interval', 'last_check', 'next_check')
        }),
        ('Estadísticas', {
            'fields': ('check_count', 'detection_count'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('tags',),
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
            'paused': 'orange',
            'error': 'red',
            'inactive': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(Detection)
class DetectionAdmin(GISModelAdmin):
    """Admin configuration for Detection model."""
    list_display = ['title', 'monitor', 'severity_badge', 'status_badge', 'detected_at', 'reviewed_by']
    list_filter = ['severity', 'status', 'detected_at', 'monitor__project']
    search_fields = ['title', 'description', 'monitor__name']
    readonly_fields = ['detected_at', 'created_by', 'updated_by', 'created_at', 'updated_at']
    filter_horizontal = ['related_layers']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('monitor', 'title', 'description', 'severity', 'status')
        }),
        ('Ubicación', {
            'fields': ('location', 'affected_area')
        }),
        ('Análisis', {
            'fields': ('analysis_data', 'confidence_score', 'evidence')
        }),
        ('Capas Relacionadas', {
            'fields': ('related_layers',)
        }),
        ('Revisión', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('detected_at',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def severity_badge(self, obj):
        """Display severity with color badge."""
        colors = {
            'low': 'blue',
            'medium': 'orange',
            'high': 'red',
            'critical': 'darkred'
        }
        color = colors.get(obj.severity, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_severity_display()
        )
    severity_badge.short_description = 'Severidad'
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'new': 'blue',
            'confirmed': 'green',
            'false_positive': 'orange',
            'resolved': 'gray',
            'ignored': 'lightgray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(ChangeRecord)
class ChangeRecordAdmin(GISModelAdmin):
    """Admin configuration for ChangeRecord model."""
    list_display = ['detection', 'change_type', 'layer', 'feature_id', 'change_magnitude', 'created_at']
    list_filter = ['change_type', 'layer', 'created_at']
    search_fields = ['detection__title', 'layer__name', 'feature_id']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('detection', 'change_type', 'layer', 'feature_id')
        }),
        ('Geometrías', {
            'fields': ('before_geometry', 'after_geometry')
        }),
        ('Atributos', {
            'fields': ('before_attributes', 'after_attributes')
        }),
        ('Magnitud', {
            'fields': ('change_magnitude', 'metadata')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MonitoringReport)
class MonitoringReportAdmin(admin.ModelAdmin):
    """Admin configuration for MonitoringReport model."""
    list_display = ['title', 'project', 'report_type', 'start_date', 'end_date', 'generated_at']
    list_filter = ['report_type', 'generated_at', 'project']
    search_fields = ['title', 'project__name']
    readonly_fields = ['generated_at', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('project', 'title', 'report_type')
        }),
        ('Período', {
            'fields': ('start_date', 'end_date')
        }),
        ('Contenido', {
            'fields': ('summary', 'statistics', 'detections_summary')
        }),
        ('Archivo', {
            'fields': ('report_file',)
        }),
        ('Fechas', {
            'fields': ('generated_at',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation."""
        return False


@admin.register(Baseline)
class BaselineAdmin(admin.ModelAdmin):
    """Admin configuration for Baseline model."""
    list_display = ['name', 'monitor', 'baseline_date', 'feature_count', 'is_current', 'is_active']
    list_filter = ['is_current', 'is_active', 'baseline_date', 'monitor__project']
    search_fields = ['name', 'monitor__name']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('monitor', 'name', 'description')
        }),
        ('Datos de Referencia', {
            'fields': ('baseline_date', 'baseline_data')
        }),
        ('Estadísticas', {
            'fields': ('feature_count', 'area_coverage')
        }),
        ('Estado', {
            'fields': ('is_current', 'is_active')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
