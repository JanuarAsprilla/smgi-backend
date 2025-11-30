"""
Admin configuration for Alerts app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AlertChannel,
    AlertRule,
    Alert,
    AlertLog,
    AlertSubscription,
    AlertTemplate
)


@admin.register(AlertChannel)
class AlertChannelAdmin(admin.ModelAdmin):
    """Admin configuration for AlertChannel model."""
    list_display = ['name', 'channel_type', 'is_enabled', 'total_sent', 'total_failed', 'success_rate_display', 'last_used']
    list_filter = ['channel_type', 'is_enabled', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['last_used', 'total_sent', 'total_failed', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'channel_type')
        }),
        ('Configuración', {
            'fields': ('configuration',)
        }),
        ('Estado', {
            'fields': ('is_enabled', 'is_active')
        }),
        ('Estadísticas', {
            'fields': ('last_used', 'total_sent', 'total_failed'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate_display(self, obj):
        """Display success rate."""
        rate = obj.success_rate
        if obj.total_sent == 0:
            return "N/A"
        color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            rate
        )
    success_rate_display.short_description = 'Tasa de Éxito'


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    """Admin configuration for AlertRule model."""
    list_display = ['name', 'severity_badge', 'trigger_type', 'is_enabled', 'is_throttled_display', 'trigger_count', 'last_triggered']
    list_filter = ['severity', 'trigger_type', 'is_enabled', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['trigger_count', 'last_triggered', 'created_by', 'updated_by', 'created_at', 'updated_at']
    filter_horizontal = ['monitors', 'projects', 'recipients', 'channels']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'severity', 'trigger_type')
        }),
        ('Condiciones', {
            'fields': ('conditions',)
        }),
        ('Objetivos', {
            'fields': ('monitors', 'projects')
        }),
        ('Destinatarios y Canales', {
            'fields': ('recipients', 'channels')
        }),
        ('Mensaje', {
            'fields': ('message_template',)
        }),
        ('Configuración', {
            'fields': ('throttle_minutes', 'is_enabled', 'is_active')
        }),
        ('Estadísticas', {
            'fields': ('trigger_count', 'last_triggered'),
            'classes': ('collapse',)
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


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin configuration for Alert model."""
    list_display = ['title', 'rule', 'severity_badge', 'status_badge', 'age_display', 'sent_at', 'acknowledged_by', 'created_at']
    list_filter = ['severity', 'status', 'created_at', 'sent_at']
    search_fields = ['title', 'message', 'rule__name']
    readonly_fields = ['sent_at', 'delivery_details', 'acknowledged_by', 'acknowledged_at', 'resolved_by', 'resolved_at', 'created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('rule', 'title', 'message', 'severity', 'status')
        }),
        ('Relacionado', {
            'fields': ('detection', 'monitor')
        }),
        ('Datos de Alerta', {
            'fields': ('alert_data',),
            'classes': ('collapse',)
        }),
        ('Entrega', {
            'fields': ('sent_at', 'delivery_details'),
            'classes': ('collapse',)
        }),
        ('Reconocimiento', {
            'fields': ('acknowledged_by', 'acknowledged_at'),
            'classes': ('collapse',)
        }),
        ('Resolución', {
            'fields': ('resolved_by', 'resolved_at', 'resolution_notes'),
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
            'pending': 'gray',
            'sent': 'green',
            'failed': 'red',
            'acknowledged': 'blue',
            'resolved': 'purple'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def age_display(self, obj):
        """Display alert age in hours."""
        age = obj.age_hours
        color = 'red' if age > 24 else 'orange' if age > 12 else 'green'
        icon = '🔴' if obj.is_critical else ''
        return format_html(
            '<span style="color: {};">{} {:.1f}h</span>',
            color,
            icon,
            age
        )
    age_display.short_description = 'Edad'


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    """Admin configuration for AlertLog model."""
    list_display = ['alert', 'channel', 'recipient', 'status_badge', 'sent_at', 'retry_count']
    list_filter = ['status', 'channel', 'sent_at']
    search_fields = ['alert__title', 'channel__name', 'recipient__username']
    readonly_fields = ['alert', 'channel', 'recipient', 'status', 'sent_at', 'response', 'error_message', 'retry_count', 'metadata']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('alert', 'channel', 'recipient', 'status')
        }),
        ('Detalles de Entrega', {
            'fields': ('sent_at', 'response', 'error_message', 'retry_count')
        }),
        ('Metadatos', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation."""
        return False
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'success': 'green',
            'failed': 'red',
            'pending': 'gray',
            'retry': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(AlertSubscription)
class AlertSubscriptionAdmin(admin.ModelAdmin):
    """Admin configuration for AlertSubscription model."""
    list_display = ['user', 'min_severity', 'is_enabled', 'quiet_hours_display', 'created_at']
    list_filter = ['min_severity', 'is_enabled', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'created_by', 'updated_by', 'created_at', 'updated_at']
    filter_horizontal = ['projects', 'monitors', 'channels']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Suscripciones', {
            'fields': ('projects', 'monitors')
        }),
        ('Preferencias', {
            'fields': ('min_severity', 'channels')
        }),
        ('Horas Silenciosas', {
            'fields': ('quiet_hours_start', 'quiet_hours_end')
        }),
        ('Estado', {
            'fields': ('is_enabled', 'is_active')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def quiet_hours_display(self, obj):
        """Display quiet hours."""
        if obj.quiet_hours_start and obj.quiet_hours_end:
            return f"{obj.quiet_hours_start.strftime('%H:%M')} - {obj.quiet_hours_end.strftime('%H:%M')}"
        return "No configurado"
    quiet_hours_display.short_description = 'Horas Silenciosas'


@admin.register(AlertTemplate)
class AlertTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for AlertTemplate model."""
    list_display = ['name', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_default', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'is_default')
        }),
        ('Plantillas', {
            'fields': ('subject_template', 'body_template')
        }),
        ('Variables', {
            'fields': ('variables',),
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
