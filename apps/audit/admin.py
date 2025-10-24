# apps/audit/admin.py
"""
SMGI Backend - Audit Admin
Sistema de Monitoreo Geoespacial Inteligente
Configuración del panel de administración de Django para la app de auditoría
"""
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin # Opcional si se usan campos geoespaciales
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from datetime import timedelta

from apps.audit.models import (
    AuditLog, AuditTrail, AuditPolicy, AuditConfiguration,
    AuditEventType, AuditEventSeverity, AuditEventStatus,
    DataClassification
)
# Importar modelos relacionados
from apps.authentication.models import User
# from apps.alerts.models import Alert # Si se usa Alert en AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin para registros de auditoría"""
    
    list_display = (
        'event_id', 'title', 'user_email', 'event_type', 'severity',
        'status', 'is_read', 'created'
    )
    list_filter = (
        'event_type', 'severity', 'status', 'is_read', 'created', 'user'
    )
    search_fields = (
        'title', 'message', 'short_message', 'user__email', 'user__username',
        'alert__title', 'alert__alert_id' # Si se usa Alert en AuditLog
    )
    readonly_fields = (
        'id', 'event_id', 'created', 'modified', 'read_at', 'alert_link'
    )
    raw_id_fields = ('user', 'alert') # Si se usa Alert en AuditLog
    date_hierarchy = 'created'
    ordering = ['-created']
    list_editable = ('is_read',) # Permite marcar como leído desde la lista
    
    fieldsets = (
        ('Identificación del Evento', {
            'fields': ('event_id', 'title', 'message', 'short_message')
        }),
        ('Clasificación del Evento', {
            'fields': ('event_type', 'severity', 'status', 'is_read', 'read_at')
        }),
        ('Actor y Recurso', {
            'fields': ('user', 'user_email', 'ip_address', 'user_agent', 'resource_type', 'resource_id', 'alert_link')
        }),
        ('Acción y Detalles', {
            'fields': ('action', 'description', 'details', 'metadata', 'tags')
        }),
        ('Timing y Outcome', {
            'fields': ('timestamp', 'duration_ms', 'success', 'error_message')
        }),
        ('Relaciones', {
            'fields': ('related_events', 'parent_event')
        }),
        ('Referencias Externas', {
            'fields': ('external_reference_id', 'external_system')
        }),
        ('Archivado', {
            'fields': ('is_archived', 'archived_at', 'archived_by')
        }),
        ('Políticas y Clasificación', {
            'fields': ('retention_policy', 'data_classification')
        }),
        ('Fechas', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',) # Oculto por defecto
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'archive_selected', 'delete_selected']
    
    def user_email(self, obj):
        return obj.user.email if obj.user else '-'
    user_email.short_description = _('User Email')
    user_email.admin_order_field = 'user__email'
    
    def alert_link(self, obj):
        # Si se usa Alert en AuditLog, crear un enlace al admin de Alert
        if obj.alert:
            from django.urls import reverse
            from django.utils.html import format_html
            alert_admin_url = reverse('admin:alerts_alert_change', args=[obj.alert.id])
            return format_html('<a href="{}">{}</a>', alert_admin_url, obj.alert.alert_id)
        return "-"
    alert_link.short_description = _('Alert Link')
    
    def mark_as_read(self, request, queryset):
        """Marcar registros seleccionados como leídos"""
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, _("Successfully marked %(count)d audit logs as read.") % {'count': updated})
    mark_as_read.short_description = _("Mark selected audit logs as read")
    
    def mark_as_unread(self, request, queryset):
        """Marcar registros seleccionados como no leídos"""
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, _("Successfully marked %(count)d audit logs as unread.") % {'count': updated})
    mark_as_unread.short_description = _("Mark selected audit logs as unread")
    
    def archive_selected(self, request, queryset):
        """Archivar registros seleccionados"""
        updated = queryset.update(is_archived=True, archived_at=timezone.now())
        self.message_user(request, _("Successfully archived %(count)d audit logs.") % {'count': updated})
    archive_selected.short_description = _("Archive selected audit logs")
    
    def delete_selected(self, request, queryset):
        """Eliminar registros seleccionados"""
        # Usar soft delete si el modelo lo soporta
        deleted = queryset.delete()
        self.message_user(request, _("Successfully deleted %(count)d audit logs.") % {'count': deleted[0]})
    delete_selected.short_description = _("Delete selected audit logs")


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    """Admin para trails de auditoría"""
    
    list_display = (
        'model_name', 'object_id', 'field_name', 'change_type',
        'user_email', 'timestamp'
    )
    list_filter = (
        'model_name', 'change_type', 'timestamp', 'user'
    )
    search_fields = (
        'model_name', 'object_id', 'field_name', 'user__email', 'user__username'
    )
    readonly_fields = (
        'id', 'created', 'modified'
    )
    raw_id_fields = ('user',)
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Información del Modelo', {
            'fields': ('model_name', 'object_id', 'field_name')
        }),
        ('Valores del Campo', {
            'fields': ('old_value', 'new_value')
        }),
        ('Tipo de Cambio', {
            'fields': ('change_type',)
        }),
        ('Actor', {
            'fields': ('user', 'user_email', 'ip_address', 'user_agent')
        }),
        ('Timing', {
            'fields': ('timestamp',)
        }),
        ('Sesión y Solicitud', {
            'fields': ('session_key', 'request_id', 'correlation_id')
        }),
        ('Archivado', {
            'fields': ('is_archived', 'archived_at', 'archived_by')
        }),
        ('Políticas y Clasificación', {
            'fields': ('retention_policy', 'data_classification')
        }),
        ('Fechas', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',) # Oculto por defecto
        }),
    )
    
    actions = ['archive_selected', 'delete_selected']
    
    def user_email(self, obj):
        return obj.user.email if obj.user else '-'
    user_email.short_description = _('User Email')
    user_email.admin_order_field = 'user__email'
    
    def archive_selected(self, request, queryset):
        """Archivar trails seleccionados"""
        updated = queryset.update(is_archived=True, archived_at=timezone.now())
        self.message_user(request, _("Successfully archived %(count)d audit trails.") % {'count': updated})
    archive_selected.short_description = _("Archive selected audit trails")
    
    def delete_selected(self, request, queryset):
        """Eliminar trails seleccionados"""
        # Usar soft delete si el modelo lo soporta
        deleted = queryset.delete()
        self.message_user(request, _("Successfully deleted %(count)d audit trails.") % {'count': deleted[0]})
    delete_selected.short_description = _("Delete selected audit trails")


@admin.register(AuditPolicy)
class AuditPolicyAdmin(admin.ModelAdmin):
    """Admin para políticas de auditoría"""
    
    list_display = (
        'name', 'is_active', 'resource_count', 'user_count',
        'ip_address_count', 'user_agent_count', 'created'
    )
    list_filter = (
        'is_active', 'created', 'modified'
    )
    search_fields = (
        'name', 'description', 'users__email', 'users__username',
        'ip_addresses', 'user_agents'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'resource_count', 'user_count',
        'ip_address_count', 'user_agent_count'
    )
    raw_id_fields = ('users', 'notification_recipients', 'created_by', 'modified_by')
    filter_horizontal = ('users', 'notification_recipients')
    date_hierarchy = 'created'
    ordering = ['name']
    
    fieldsets = (
        ('Identificación de la Política', {
            'fields': ('name', 'description')
        }),
        ('Activación', {
            'fields': ('is_active',)
        }),
        ('Alcance', {
            'fields': (
                'resource_types', 'event_types', 'severity_levels',
                'actions', 'users', 'ip_addresses', 'user_agents'
            )
        }),
        ('Retención', {
            'fields': ('retention_days', 'archive_after_days')
        }),
        ('Notificación', {
            'fields': ('notify_on_events', 'notification_channels', 'notification_recipients')
        }),
        ('Usuarios y Gestión', {
            'fields': ('created_by', 'modified_by')
        }),
        ('Fechas', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',) # Oculto por defecto
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'delete_selected']
    
    def resource_count(self, obj):
        return len(obj.resource_types) if obj.resource_types else 0
    resource_count.short_description = _('Resource Count')
    
    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = _('User Count')
    
    def ip_address_count(self, obj):
        return len(obj.ip_addresses) if obj.ip_addresses else 0
    ip_address_count.short_description = _('IP Address Count')
    
    def user_agent_count(self, obj):
        return len(obj.user_agents) if obj.user_agents else 0
    user_agent_count.short_description = _('User Agent Count')
    
    def make_active(self, request, queryset):
        """Activar políticas seleccionadas"""
        updated = queryset.update(is_active=True)
        self.message_user(request, _("Successfully activated %(count)d audit policies.") % {'count': updated})
    make_active.short_description = _("Activate selected audit policies")
    
    def make_inactive(self, request, queryset):
        """Desactivar políticas seleccionadas"""
        updated = queryset.update(is_active=False)
        self.message_user(request, _("Successfully deactivated %(count)d audit policies.") % {'count': updated})
    make_inactive.short_description = _("Deactivate selected audit policies")
    
    def delete_selected(self, request, queryset):
        """Eliminar políticas seleccionadas"""
        # Usar soft delete si el modelo lo soporta
        deleted = queryset.delete()
        self.message_user(request, _("Successfully deleted %(count)d audit policies.") % {'count': deleted[0]})
    delete_selected.short_description = _("Delete selected audit policies")


@admin.register(AuditConfiguration)
class AuditConfigurationAdmin(admin.ModelAdmin):
    """Admin para configuración de auditoría"""
    
    list_display = (
        'name', 'is_active', 'default_retention_days', 'default_archive_after_days',
        'total_storage_options_enabled', 'created'
    )
    list_filter = (
        'is_active', 'created', 'modified'
    )
    search_fields = (
        'name', 'description'
    )
    readonly_fields = (
        'id', 'created', 'modified', 'total_storage_options_enabled', 'total_sensitive_fields_excluded'
    )
    raw_id_fields = ('created_by', 'modified_by')
    date_hierarchy = 'created'
    ordering = ['name']
    
    fieldsets = (
        ('Identificación de la Configuración', {
            'fields': ('name', 'description')
        }),
        ('Activación', {
            'fields': ('is_active',)
        }),
        ('Retención por Defecto', {
            'fields': ('default_retention_days', 'default_archive_after_days', 'default_data_classification')
        }),
        ('Logging', {
            'fields': ('enable_real_time_logging', 'enable_batch_logging', 'batch_size')
        }),
        ('Nivel de Log', {
            'fields': ('log_level',)
        }),
        ('Manejo de Datos Sensibles', {
            'fields': ('exclude_sensitive_fields', 'mask_sensitive_data', 'encrypt_audit_logs')
        }),
        ('Opciones de Almacenamiento', {
            'fields': (
                'store_audit_trails', 'store_user_sessions', 'store_api_calls',
                'store_external_api_calls', 'store_internal_api_calls',
                'store_database_queries', 'store_cache_operations',
                'store_file_operations', 'store_email_sending',
                'store_sms_sending', 'store_webhook_sending',
                'store_push_notification_sending', 'store_report_generation',
                'store_alert_triggering', 'store_monitoring_job_scheduling',
                'store_system_health_checks', 'store_data_validation',
                'store_gis_service_interaction', 'store_authentication',
                'store_authorization', 'store_error_handling',
                'store_performance_monitoring'
            )
        }),
        ('Usuarios y Gestión', {
            'fields': ('created_by', 'modified_by')
        }),
        ('Fechas', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',) # Oculto por defecto
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'delete_selected']
    
    def total_storage_options_enabled(self, obj):
        return obj.total_storage_options_enabled
    total_storage_options_enabled.short_description = _('Storage Options Enabled')
    
    def total_sensitive_fields_excluded(self, obj):
        return obj.total_sensitive_fields_excluded
    total_sensitive_fields_excluded.short_description = _('Sensitive Fields Excluded')
    
    def make_active(self, request, queryset):
        """Activar configuraciones seleccionadas"""
        updated = queryset.update(is_active=True)
        self.message_user(request, _("Successfully activated %(count)d audit configurations.") % {'count': updated})
    make_active.short_description = _("Activate selected audit configurations")
    
    def make_inactive(self, request, queryset):
        """Desactivar configuraciones seleccionadas"""
        updated = queryset.update(is_active=False)
        self.message_user(request, _("Successfully deactivated %(count)d audit configurations.") % {'count': updated})
    make_inactive.short_description = _("Deactivate selected audit configurations")
    
    def delete_selected(self, request, queryset):
        """Eliminar configuraciones seleccionadas"""
        # Usar soft delete si el modelo lo soporta
        deleted = queryset.delete()
        self.message_user(request, _("Successfully deleted %(count)d audit configurations.") % {'count': deleted[0]})
    delete_selected.short_description = _("Delete selected audit configurations")
