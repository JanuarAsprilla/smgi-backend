# apps/monitoring/admin.py
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin # Otra opción es LeafletAdmin si se usa django-leaflet
from .models import (
    LayerSnapshot, ChangeDetectionResult, MonitoringJob,
    MonitoringJobExecution, DataQualityRule, DataQualityResult,
    SystemHealthMetric, AffectedFeature # Asegúrate de importar AffectedFeature
)

@admin.register(LayerSnapshot)
class LayerSnapshotAdmin(OSMGeoAdmin):
    list_display = ('id', 'layer', 'feature_count', 'is_valid', 'created')
    list_filter = ('is_valid', 'created', 'layer__service') # Filtrar por servicio del layer
    search_fields = ('layer__name', 'layer__service__name', 'snapshot_hash')
    readonly_fields = ('created', 'modified', 'snapshot_hash', 'data_checksum') # Campos generados
    raw_id_fields = ('layer',) # Para campos ForeignKey con muchos objetos
    date_hierarchy = 'created' # Facilita la navegación por fechas
    # Permitir ediciones rápidas desde la lista
    list_editable = ('is_valid',)
    # Mostrar un mapa si el modelo tiene un campo geométrico relevante (centroid aquí)
    # openlayers_url = '...' # Si se usa un proveedor diferente
    # map_width = 600
    # map_height = 400
    # geom_field = 'centroid' # Campo geométrico a mostrar en el mapa del admin


@admin.register(ChangeDetectionResult)
class ChangeDetectionResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'layer', 'algorithm_used', 'has_changes', 'change_severity', 'exceeds_threshold', 'created')
    list_filter = ('has_changes', 'exceeds_threshold', 'processing_status', 'algorithm_used', 'created')
    search_fields = ('current_snapshot__layer__name', 'current_snapshot__layer__service__name')
    readonly_fields = ('created', 'modified', 'detection_duration_ms', 'confidence_score')
    raw_id_fields = ('current_snapshot', 'previous_snapshot')
    date_hierarchy = 'created'
    # Permitir ediciones rápidas desde la lista
    list_editable = ('exceeds_threshold',)

    # Opcional: Método para mostrar la severidad con colores o etiquetas si se desea en la lista
    # def get_change_severity_display(self, obj):
    #     severity = obj.change_severity
    #     # Puedes devolver un HTML con estilos o solo el texto
    #     color_map = {'critical': 'red', 'high': 'orange', 'medium': 'yellow', 'low': 'green', 'none': 'grey'}
    #     color = color_map.get(severity, 'black')
    #     return format_html('<span style="color: {};">{}</span>', color, severity)
    # get_change_severity_display.short_description = 'Severity'


@admin.register(AffectedFeature)
class AffectedFeatureAdmin(admin.ModelAdmin):
    list_display = ('id', 'change_result', 'feature_id', 'created')
    list_filter = ('created',)
    search_fields = ('feature_id', 'change_result__id', 'change_result__current_snapshot__layer__name')
    readonly_fields = ('created',)
    raw_id_fields = ('change_result',)
    date_hierarchy = 'created'
    # Opcional: Filtrar rápidamente por change_result
    list_select_related = ('change_result', 'change_result__current_snapshot__layer')


@admin.register(MonitoringJob)
class MonitoringJobAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'status', 'total_layers', 'total_services', 'last_run', 'next_run', 'created_by')
    list_filter = ('is_active', 'status', 'created_by', 'last_run', 'next_run')
    search_fields = ('name', 'description', 'created_by__username', 'layers__name', 'services__name')
    readonly_fields = ('created', 'modified', 'last_run', 'last_successful_run', 'next_run', 'consecutive_failures', 'total_layers', 'total_services')
    raw_id_fields = ('layers', 'services', 'created_by')
    filter_horizontal = ('layers', 'services') # Para relaciones ManyToMany
    date_hierarchy = 'created'


@admin.register(MonitoringJobExecution)
class MonitoringJobExecutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'success', 'started_at', 'completed_at', 'duration_seconds', 'layers_processed')
    list_filter = ('success', 'started_at', 'job')
    search_fields = ('job__name',)
    readonly_fields = ('id', 'started_at', 'completed_at', 'duration_seconds', 'success', 'error_message',
                       'layers_processed', 'snapshots_created', 'changes_detected', 'alerts_created',
                       'memory_usage_mb', 'cpu_usage_percent', 'execution_log', 'performance_metrics')
    raw_id_fields = ('job',)
    date_hierarchy = 'started_at'


@admin.register(DataQualityRule)
class DataQualityRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'rule_type', 'is_active', 'needs_check', 'current_status', 'last_check', 'layer', 'service')
    list_filter = ('is_active', 'rule_type', 'needs_check', 'current_status', 'last_check')
    search_fields = ('name', 'description', 'layer__name', 'service__name')
    readonly_fields = ('created', 'modified', 'last_check', 'last_score')
    raw_id_fields = ('layer', 'service')
    date_hierarchy = 'created'
    # Permitir ediciones rápidas desde la lista
    list_editable = ('is_active',)


@admin.register(DataQualityResult)
class DataQualityResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'rule', 'quality_score', 'quality_grade', 'passed', 'created')
    list_filter = ('passed', 'quality_grade', 'created')
    search_fields = ('rule__name', 'rule__layer__name', 'rule__service__name')
    readonly_fields = ('id', 'created', 'quality_score', 'passed', 'total_records', 'valid_records', 'invalid_records',
                       'completeness_score', 'accuracy_score', 'consistency_score', 'validity_score',
                       'uniqueness_score', 'timeliness_score', 'issues_found', 'recommendations',
                       'assessment_duration_ms')
    raw_id_fields = ('rule',)
    date_hierarchy = 'created'


@admin.register(SystemHealthMetric)
class SystemHealthMetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'overall_health', 'cpu_usage_percent', 'memory_usage_percent', 'disk_usage_percent', 'created')
    list_filter = ('overall_health', 'created')
    search_fields = [] # Pocos campos textuales para buscar
    readonly_fields = ('id', 'created', 'cpu_usage_percent', 'memory_usage_percent', 'disk_usage_percent',
                       'db_connections_active', 'db_connections_idle', 'db_query_avg_time_ms',
                       'redis_memory_usage_mb', 'redis_connected_clients', 'redis_operations_per_sec',
                       'celery_active_tasks', 'celery_pending_tasks', 'celery_failed_tasks',
                       'active_users', 'api_requests_per_minute', 'api_error_rate_percent',
                       'overall_health')
    date_hierarchy = 'created'

# Opcional: Personalizar el encabezado del sitio de administración
# admin.site.site_header = "SMGI Monitoring Administration"
# admin.site.site_title = "SMGI Monitoring Admin Portal"
# admin.site.index_title = "Welcome to SMGI Monitoring Admin Portal"
