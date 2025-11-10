"""
Admin configuration for Geodata app.
"""
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html
from .models import DataSource, Layer, Feature, Dataset, SyncLog


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    """Admin configuration for DataSource model."""
    list_display = ['name', 'source_type', 'status_badge', 'refresh_interval', 'last_sync', 'is_active', 'created_at']
    list_filter = ['source_type', 'status', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'url']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at', 'last_sync']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'source_type', 'status')
        }),
        ('Configuración de Conexión', {
            'fields': ('url', 'credentials', 'configuration')
        }),
        ('Sincronización', {
            'fields': ('refresh_interval', 'last_sync')
        }),
        ('Metadatos', {
            'fields': ('metadata', 'tags'),
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
            'inactive': 'gray',
            'error': 'red',
            'maintenance': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(Layer)
class LayerAdmin(GISModelAdmin):
    """Admin configuration for Layer model."""
    list_display = ['name', 'data_source', 'layer_type', 'geometry_type', 'is_public', 'is_queryable', 'is_active', 'created_at']
    list_filter = ['layer_type', 'geometry_type', 'is_public', 'is_queryable', 'is_active', 'data_source', 'created_at']
    search_fields = ['name', 'description', 'data_source__name']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'data_source')
        }),
        ('Configuración Geoespacial', {
            'fields': ('layer_type', 'geometry_type', 'srid', 'extent')
        }),
        ('Configuración de Visualización', {
            'fields': ('style', 'properties_schema')
        }),
        ('Permisos y Opciones', {
            'fields': ('is_public', 'is_queryable', 'is_active')
        }),
        ('Metadatos', {
            'fields': ('metadata', 'tags'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Feature)
class FeatureAdmin(GISModelAdmin):
    """Admin configuration for Feature model."""
    list_display = ['id', 'layer', 'feature_id', 'is_active', 'created_at']
    list_filter = ['layer', 'is_active', 'created_at']
    search_fields = ['feature_id', 'properties', 'layer__name']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('layer', 'feature_id')
        }),
        ('Datos Geoespaciales', {
            'fields': ('geometry', 'properties')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin configuration for Dataset model."""
    list_display = ['name', 'layer_count', 'is_public', 'is_active', 'created_at']
    list_filter = ['is_public', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['layers']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description')
        }),
        ('Capas', {
            'fields': ('layers',)
        }),
        ('Configuración', {
            'fields': ('is_public', 'is_active')
        }),
        ('Metadatos', {
            'fields': ('metadata', 'tags'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def layer_count(self, obj):
        """Display number of layers."""
        return obj.layers.count()
    layer_count.short_description = 'Número de Capas'


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    """Admin configuration for SyncLog model."""
    list_display = ['id', 'data_source', 'status_badge', 'started_at', 'completed_at', 'duration', 'records_processed']
    list_filter = ['status', 'started_at', 'data_source']
    search_fields = ['data_source__name', 'error_message']
    readonly_fields = ['data_source', 'status', 'started_at', 'completed_at', 'records_processed', 
                      'records_added', 'records_updated', 'records_failed', 'error_message', 'details']
    
    fieldsets = (
        ('Información de Sincronización', {
            'fields': ('data_source', 'status', 'started_at', 'completed_at')
        }),
        ('Estadísticas', {
            'fields': ('records_processed', 'records_added', 'records_updated', 'records_failed')
        }),
        ('Detalles y Errores', {
            'fields': ('error_message', 'details'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation of sync logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of old logs."""
        return True
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'success': 'green',
            'failed': 'red',
            'partial': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def duration(self, obj):
        """Calculate and display duration."""
        if obj.completed_at:
            delta = obj.completed_at - obj.started_at
            seconds = delta.total_seconds()
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h"
        return "En progreso"
    duration.short_description = 'Duración'
