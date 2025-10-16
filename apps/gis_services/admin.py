# apps/gis_services/admin.py
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin # Otra opción es LeafletAdmin si se usa django-leaflet
from .models import (
    ArcGISService, SpatialLayer, LayerField,
    ServiceEndpoint, ServiceCredential,
    ServiceConfiguration, ServiceTag, ServiceTagRelation,
    ServiceMetrics
)

@admin.register(ArcGISService)
class ArcGISServiceAdmin(OSMGeoAdmin):
    list_display = ('name', 'service_type', 'status', 'is_monitored', 'created_by', 'created')
    list_filter = ('service_type', 'status', 'is_monitored', 'created')
    search_fields = ('name', 'base_url', 'description')
    readonly_fields = ('created', 'modified', 'last_check', 'last_successful_check', 'consecutive_failures')
    filter_horizontal = ('tags',) # Para el ManyToManyField con tags

@admin.register(SpatialLayer)
class SpatialLayerAdmin(OSMGeoAdmin):
    list_display = ('name', 'service', 'geometry_type', 'is_monitored', 'feature_count', 'created')
    list_filter = ('geometry_type', 'is_monitored', 'monitoring_enabled', 'created')
    search_fields = ('name', 'service__name', 'description')
    readonly_fields = ('created', 'modified', 'last_check', 'last_successful_check', 'check_failures')
    raw_id_fields = ('service',) # Para campos ForeignKey con muchos objetos

@admin.register(LayerField)
class LayerFieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'layer', 'field_type', 'monitor_for_changes')
    list_filter = ('field_type', 'monitor_for_changes')
    search_fields = ('name', 'layer__name', 'layer__service__name')
    raw_id_fields = ('layer',)

@admin.register(ServiceEndpoint)
class ServiceEndpointAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'method', 'is_monitored', 'last_response_time')
    list_filter = ('method', 'is_monitored')
    search_fields = ('name', 'service__name', 'path')
    raw_id_fields = ('service',)

@admin.register(ServiceCredential)
class ServiceCredentialAdmin(admin.ModelAdmin):
    list_display = ('service', 'username') # Mostrar solo el nombre de usuario, no la contraseña
    search_fields = ('service__name', 'username')
    readonly_fields = ('created', 'modified') # De TimeStampedModel
    raw_id_fields = ('service',)

@admin.register(ServiceConfiguration)
class ServiceConfigurationAdmin(admin.ModelAdmin):
    list_display = ('service',)
    search_fields = ('service__name',)
    readonly_fields = ('created', 'modified') # De BaseModel
    raw_id_fields = ('service',)

@admin.register(ServiceTag)
class ServiceTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'description')
    search_fields = ('name', 'description')

@admin.register(ServiceTagRelation)
class ServiceTagRelationAdmin(admin.ModelAdmin):
    list_display = ('service', 'tag', 'added_by', 'added_at')
    search_fields = ('service__name', 'tag__name', 'added_by__username')
    raw_id_fields = ('service', 'tag', 'added_by')

@admin.register(ServiceMetrics)
class ServiceMetricsAdmin(admin.ModelAdmin):
    list_display = ('service', 'method', 'status_code', 'success', 'response_time_ms', 'created')
    list_filter = ('success', 'status_code', 'method', 'created')
    search_fields = ('service__name', 'endpoint')
    readonly_fields = ('created', 'modified') # De TimeStampedModel
    raw_id_fields = ('service',)
    date_hierarchy = 'created' # Facilita la navegación por fechas