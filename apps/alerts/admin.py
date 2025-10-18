# apps/alerts/admin.py
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin # Otra opción es LeafletAdmin si se usa django-leaflet
from .models import Alert, AlertAction


@admin.register(Alert)
class AlertAdmin(OSMGeoAdmin):
    list_display = (
        'alert_id', 'title', 'category', 'severity', 'status',
        'service', 'layer', 'affected_features_count', 'first_detected',
        'assigned_to', 'resolved_at'
    )
    list_filter = (
        'category', 'severity', 'status', 'first_detected',
        'auto_resolve', 'suppress_similar', 'assigned_to'
    )
    search_fields = (
        'alert_id', 'title', 'description', 'service__name', 'layer__name',
        'assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name'
    )
    readonly_fields = (
        'alert_id', 'first_detected', 'last_updated', 'acknowledged_at',
        'resolved_at', 'notification_count', 'last_notification_sent',
        # --- MEJORA: Añadir propiedades calculadas como readonly_fields ---
        'is_expired', 'should_auto_resolve'
        # --- FIN MEJORA ---
    )
    raw_id_fields = ('service', 'layer', 'assigned_to', 'acknowledged_by', 'resolved_by')
    filter_horizontal = ('related_alerts',) # Si se desea un widget horizontal para M2M
    date_hierarchy = 'first_detected'
    ordering = ['-severity', '-first_detected']

    # Opcional: Agrupar campos en fieldsets
    fieldsets = (
        ('Identification', {
            'fields': ('title', 'description', 'alert_id', 'category', 'severity')
        }),
        ('Source & Details', {
            'fields': ('service', 'layer', 'affected_features_count', 'change_percentage', 'threshold_value', 'actual_value', 'alert_extent')
        }),
        ('Status & Lifecycle', {
            'fields': ('status', 'first_detected', 'last_updated', 'expires_at', 'is_expired', 'should_auto_resolve')
        }),
        ('Assignment & Actions', {
            'fields': ('assigned_to', 'acknowledged_at', 'acknowledged_by', 'resolved_at', 'resolved_by')
        }),
        ('Configuration', {
            'fields': ('auto_resolve', 'auto_resolve_duration', 'suppress_similar', 'suppression_duration')
        }),
        ('Notifications & Tracking', {
            'fields': ('notification_sent', 'notification_count', 'last_notification_sent', 'external_ticket_id')
        }),
        ('Metadata', {
            'fields': ('metadata', 'tags', 'related_alerts')
        }),
    )

    # Opcional: Permitir ediciones rápidas desde la lista
    list_editable = ('status', 'assigned_to')


@admin.register(AlertAction)
class AlertActionAdmin(admin.ModelAdmin):
    list_display = (
        'alert', 'action_type', 'user', 'timestamp'
    )
    list_filter = ('action_type', 'timestamp', 'user')
    search_fields = (
        'alert__alert_id', 'alert__title', 'user__username', 'user__first_name', 'user__last_name', 'notes'
    )
    readonly_fields = ('timestamp',)
    raw_id_fields = ('alert', 'user')
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    # Opcional: Agrupar campos en fieldsets
    fieldsets = (
        ('Action Details', {
            'fields': ('alert', 'action_type', 'user', 'notes')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )

# Opcional: Personalizar el encabezado del sitio de administración para esta app
# admin.site.site_header = "SMGI Alerts Administration"
# admin.site.site_title = "SMGI Alerts Admin Portal"
# admin.site.index_title = "Welcome to SMGI Alerts Admin Portal"
