"""
SMGI Backend - GIS Services Views
Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction # Importar transaction
from django.db.models import Avg, Count, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.gis_services.models import (
    ArcGISService, SpatialLayer, ServiceTag,
    ServiceEndpoint, ServiceMetrics, ServiceStatus, LayerField # Añadido LayerField
)
from apps.gis_services.serializers import (
    ArcGISServiceListSerializer, ArcGISServiceDetailSerializer,
    ArcGISServiceCreateSerializer, SpatialLayerListSerializer,
    SpatialLayerDetailSerializer, SpatialLayerCreateSerializer,
    ServiceTagSerializer, ServiceEndpointSerializer,
    ServiceMetricsSerializer, ServiceHealthSerializer,
    TestConnectionSerializer, SyncLayersSerializer
)
from apps.gis_services.clients.arcgis_client import ArcGISClient


@extend_schema(tags=['Services'])
class ArcGISServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ArcGIS Services
    """
    permission_classes = [IsAuthenticated]
    filterset_fields = ['service_type', 'status', 'is_monitored']
    search_fields = ['name', 'description', 'base_url']
    ordering_fields = ['name', 'created', 'last_check']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = ArcGISService.objects.filter(is_removed=False)
        
        # Filter by tags
        tags = self.request.query_params.get('tags')
        if tags:
            tag_ids = tags.split(',')
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()
        
        return queryset.select_related('created_by')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArcGISServiceListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ArcGISServiceCreateSerializer
        return ArcGISServiceDetailSerializer
    
    @extend_schema(
        summary='Test Service Connection',
        request=TestConnectionSerializer,
        responses={200: {'type': 'object', 'properties': {
            'success': {'type': 'boolean'},
            'message': {'type': 'string'},
            'service_info': {'type': 'object'}
        }}}
    )
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to ArcGIS service"""
        service = self.get_object()
        
        try:
            client = ArcGISClient(service)
            success, message = client.test_connection()
            
            if success:
                # Get service info
                info = client.get_service_info(use_cache=False)
                
                # Update service status
                service.update_status(ServiceStatus.ACTIVE)
                
                return Response({
                    'success': True,
                    'message': message,
                    'service_info': info
                })
            else:
                service.update_status(ServiceStatus.ERROR, message)
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            service.update_status(ServiceStatus.ERROR, str(e))
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary='Sync Layers from Service',
        request=SyncLayersSerializer,
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['post'])
    def sync_layers(self, request, pk=None):
        """Synchronize layers from ArcGIS service"""
        service = self.get_object()
        serializer = SyncLayersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        auto_monitor = serializer.validated_data.get('auto_monitor', False)
        specific_layer_ids = serializer.validated_data.get('layer_ids', [])
        
        try:
            client = ArcGISClient(service)
            service_info = client.get_service_info(use_cache=False)
            
            layers_data = service_info.get('layers', [])
            synced_layers = []
            updated_layers = []
            errors = []
            
            # Usar transacción para asegurar consistencia
            with transaction.atomic():
                for layer_data in layers_data:
                    layer_id = layer_data.get('id')
                    
                    # Skip if specific layers requested and this isn't one of them
                    if specific_layer_ids and layer_id not in specific_layer_ids:
                        continue
                    
                    try:
                        # Get detailed layer info
                        layer_info = client.get_layer_info(layer_id, use_cache=False)
                        
                        # Check if layer already exists
                        layer, created = SpatialLayer.objects.update_or_create(
                            service=service,
                            layer_id=layer_id,
                            defaults={
                                'name': layer_info.get('name', f'Layer {layer_id}'),
                                'description': layer_info.get('description', ''),
                                'geometry_type': layer_info.get('geometryType', 'unknown'),
                                'min_scale': layer_info.get('minScale'),
                                'max_scale': layer_info.get('maxScale'),
                                'spatial_reference': layer_info.get('spatialReference', {}),
                                'supports_query': layer_info.get('supportsAdvancedQueries', False),
                                'supports_statistics': layer_info.get('supportsStatistics', False),
                                # REMOVED: 'fields': layer_info.get('fields', []), # Ya no se usa
                                'is_monitored': auto_monitor,
                                'monitoring_enabled': auto_monitor,
                                'created_by': request.user if created else None
                            }
                        )
                        
                        # --- NUEVO: Sincronizar campos (LayerField) ---
                        layer_fields_data = layer_info.get('fields', [])
                        if layer_fields_data:
                            # Obtener o crear LayerField para cada campo del layer_info
                            for field_data in layer_fields_data:
                                LayerField.objects.update_or_create(
                                    layer=layer,
                                    name=field_data.get('name', ''),
                                    defaults={
                                        'alias': field_data.get('alias', ''),
                                        'field_type': field_data.get('type', ''),
                                        'length': field_data.get('length'),
                                        'is_nullable': field_data.get('nullable', True),
                                        'default_value': field_data.get('defaultValue', ''),
                                        # Puedes añadir lógica para 'monitor_for_changes' aquí si proviene de la configuración
                                        'monitor_for_changes': False, # Por defecto, o según regla
                                        'change_threshold': None, # Por defecto
                                    }
                                )
                        # --- FIN NUEVO ---

                        if created:
                            synced_layers.append(layer.name)
                        else:
                            updated_layers.append(layer.name)
                            
                    except Exception as e:
                        errors.append({
                            'layer_id': layer_id,
                            'error': str(e)
                        })
            
            return Response({
                'success': True,
                'synced': len(synced_layers),
                'updated': len(updated_layers),
                'errors': len(errors),
                'synced_layers': synced_layers,
                'updated_layers': updated_layers,
                'error_details': errors
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(summary='Get Service Health Status')
    @action(detail=True, methods=['get'])
    def health(self, request, pk=None):
        """Get service health status"""
        service = self.get_object()
        
        # Calculate metrics
        avg_response = ServiceMetrics.get_average_response_time(service, hours=24)
        success_rate = ServiceMetrics.get_success_rate(service, hours=24)
        monitored_layers = service.spatial_layers.filter(
            is_monitored=True,
            is_removed=False
        ).count()
        
        health_data = {
            'service_id': service.id,
            'service_name': service.name,
            'status': service.status,
            'is_online': service.is_online,
            'last_check': service.last_check,
            'last_successful_check': service.last_successful_check,
            'consecutive_failures': service.consecutive_failures,
            'average_response_time': avg_response,
            'success_rate': success_rate,
            'monitored_layers': monitored_layers
        }
        
        serializer = ServiceHealthSerializer(health_data)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Service Metrics')
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get service performance metrics"""
        service = self.get_object()
        
        # Get time period from query params (default 24 hours)
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timezone.timedelta(hours=hours)
        
        metrics = ServiceMetrics.objects.filter(
            service=service,
            created__gte=since
        ).order_by('-created')[:100]
        
        serializer = ServiceMetricsSerializer(metrics, many=True)
        
        return Response({
            'period_hours': hours,
            'total_requests': metrics.count(),
            'metrics': serializer.data
        })
    
    @extend_schema(summary='Enable/Disable Monitoring')
    @action(detail=True, methods=['post'])
    def toggle_monitoring(self, request, pk=None):
        """Enable or disable monitoring for service"""
        service = self.get_object()
        service.is_monitored = not service.is_monitored
        service.save(update_fields=['is_monitored'])
        
        return Response({
            'message': _('Monitoring {}').format(
                _('enabled') if service.is_monitored else _('disabled')
            ),
            'is_monitored': service.is_monitored
        })
    
    @extend_schema(summary='Get Service Statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get overall service statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_services': queryset.count(),
            'active_services': queryset.filter(status=ServiceStatus.ACTIVE).count(),
            'monitored_services': queryset.filter(is_monitored=True).count(),
            'services_with_errors': queryset.filter(status=ServiceStatus.ERROR).count(),
            'by_type': {},
            'total_layers': SpatialLayer.objects.filter(is_removed=False).count(),
            'monitored_layers': SpatialLayer.objects.filter(
                is_monitored=True,
                is_removed=False
            ).count()
        }
        
        # Group by service type
        by_type = queryset.values('service_type').annotate(count=Count('id'))
        for item in by_type:
            stats['by_type'][item['service_type']] = item['count']
        
        return Response(stats)


@extend_schema(tags=['Layers'])
class SpatialLayerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Spatial Layers
    """
    permission_classes = [IsAuthenticated]
    filterset_fields = [
        'service', 'geometry_type', 'is_monitored',
        'monitoring_enabled', 'change_detection_enabled'
    ]
    search_fields = ['name', 'display_name', 'description']
    ordering_fields = ['name', 'feature_count', 'last_check', 'created']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = SpatialLayer.objects.filter(is_removed=False)
        
        # Filter by service status
        service_status = self.request.query_params.get('service_status')
        if service_status:
            queryset = queryset.filter(service__status=service_status)
        
        return queryset.select_related('service', 'created_by')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SpatialLayerListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SpatialLayerCreateSerializer
        return SpatialLayerDetailSerializer
    
    @extend_schema(summary='Manually Monitor Layer')
    @action(detail=True, methods=['post'])
    def monitor_now(self, request, pk=None):
        """Trigger immediate monitoring of this layer"""
        layer = self.get_object()
        
        # Trigger monitoring task
        from apps.monitoring.tasks import monitor_layer
        result = monitor_layer.delay(str(layer.id))
        
        return Response({
            'message': _('Monitoring task initiated'),
            'task_id': result.id,
            'layer_id': str(layer.id),
            'layer_name': layer.name
        })
    
    @extend_schema(summary='Get Layer Feature Count')
    @action(detail=True, methods=['get'])
    def feature_count(self, request, pk=None):
        """Get current feature count from service"""
        layer = self.get_object()
        
        try:
            client = ArcGISClient(layer.service)
            count = client.get_feature_count(layer.layer_id)
            
            return Response({
                'layer_id': layer.layer_id,
                'layer_name': layer.name,
                'current_count': count,
                'cached_count': layer.feature_count,
                'difference': count - layer.feature_count
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(summary='Get Layer Snapshots')
    @action(detail=True, methods=['get'])
    def snapshots(self, request, pk=None):
        """Get layer snapshots history"""
        layer = self.get_object()
        
        # Get time period
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timezone.timedelta(days=days)
        
        # Asumiendo que LayerSnapshot existe y tiene related_name='snapshots'
        # y campos 'total_area', 'is_valid'.
        # Si no, este código fallará o necesitará ajustes.
        try:
            from apps.monitoring.models import LayerSnapshot
            snapshots = layer.snapshots.filter(
                created__gte=since
            ).order_by('-created')[:50]
            
            snapshot_data = [{
                'id': str(snap.id),
                'feature_count': snap.feature_count,
                # Asumiendo que LayerSnapshot tiene estos campos
                'total_area': snap.total_area,
                'is_valid': snap.is_valid,
                'created': snap.created
            } for snap in snapshots]
            
            return Response({
                'layer_name': layer.name,
                'period_days': days,
                'snapshot_count': len(snapshot_data),
                'snapshots': snapshot_data
            })
        except ImportError:
            # Manejar el caso si la app monitoring no está disponible
            # o si el modelo no existe aún
            return Response({
                'error': 'Monitoring app or LayerSnapshot model not available'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)
        except AttributeError:
            # Manejar el caso si LayerSnapshot no tiene los campos esperados
            return Response({
                'error': 'LayerSnapshot model does not have expected fields (total_area, is_valid)'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    @extend_schema(summary='Enable/Disable Layer Monitoring')
    @action(detail=True, methods=['post'])
    def toggle_monitoring(self, request, pk=None):
        """Enable or disable monitoring for layer"""
        layer = self.get_object()
        layer.is_monitored = not layer.is_monitored
        layer.save(update_fields=['is_monitored'])
        
        return Response({
            'message': _('Monitoring {}').format(
                _('enabled') if layer.is_monitored else _('disabled')
            ),
            'is_monitored': layer.is_monitored
        })
    
    @extend_schema(summary='Get Layers Requiring Attention')
    @action(detail=False, methods=['get'])
    def needs_attention(self, request):
        """Get layers that need attention"""
        queryset = self.get_queryset()
        
        # Layers with significant changes
        changed_layers = queryset.filter(
            is_monitored=True,
            check_failures__lt=3
        ).exclude(
            last_feature_count=0
        )
        
        needs_attention = []
        for layer in changed_layers:
            if layer.has_significant_change:
                needs_attention.append({
                    'id': str(layer.id),
                    'name': layer.name,
                    'service': layer.service.name,
                    'change_percentage': layer.change_percentage,
                    'feature_count': layer.feature_count,
                    'last_feature_count': layer.last_feature_count,
                    'last_check': layer.last_check
                })
        
        # Layers with failures
        failed_layers = queryset.filter(check_failures__gte=3)
        
        for layer in failed_layers:
            needs_attention.append({
                'id': str(layer.id),
                'name': layer.name,
                'service': layer.service.name,
                'reason': 'consecutive_failures',
                'check_failures': layer.check_failures,
                'last_check': layer.last_check
            })
        
        return Response({
            'count': len(needs_attention),
            'layers': needs_attention
        })


@extend_schema(tags=['Service Tags'])
class ServiceTagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Service Tags
    """
    queryset = ServiceTag.objects.filter(is_removed=False)
    serializer_class = ServiceTagSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'description']
    ordering = ['name']


@extend_schema(tags=['Service Endpoints'])
class ServiceEndpointViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Service Endpoints
    """
    queryset = ServiceEndpoint.objects.filter(is_removed=False)
    serializer_class = ServiceEndpointSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['service', 'method', 'is_monitored']
    ordering = ['service', 'name']
