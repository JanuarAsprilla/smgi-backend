"""
Views for Geodata app - Updated with export functionality.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.http import FileResponse
import os

from .models import DataSource, Layer, Feature, Dataset, SyncLog
from .serializers import (
    DataSourceSerializer,
    LayerSerializer,
    FeatureSerializer,
    FeatureCreateSerializer,
    DatasetSerializer,
    SyncLogSerializer,
)
from .serializers_export import ExportRequestSerializer
from .filters import DataSourceFilter, LayerFilter, FeatureFilter
from .tasks import sync_data_source
from .exporters import ShapefileExporter, GeoJSONExporter
from apps.users.permissions import IsAnalystOrAbove


class ExportMixin:
    """Mixin para agregar funcionalidad de exportación."""
    
    @action(detail=True, methods=['post'], url_path='export')
    def export_data(self, request, pk=None):
        """
        Exporta los datos a Shapefile o GeoJSON.
        
        POST /api/v1/geodata/layers/{id}/export/
        
        Body:
        {
            "format": "shapefile|geojson|both",
            "filename": "mi_capa" (opcional),
            "crs": "EPSG:4326" (opcional)
        }
        """
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        obj = self.get_object()
        export_format = serializer.validated_data['format']
        filename = serializer.validated_data.get('filename')
        
        files = []
        
        try:
            # Exportar Shapefile
            if export_format in ['shapefile', 'both']:
                shp_exporter = ShapefileExporter(output_dir='data/exports/shapefiles')
                
                if hasattr(obj, 'features'):  # Es una Layer
                    shp_path = shp_exporter.export_layer(obj, filename)
                elif hasattr(obj, 'layers'):  # Es un Dataset
                    shp_path = shp_exporter.export_dataset(obj, filename)
                else:
                    return Response({
                        'error': 'Tipo de objeto no soportado'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                files.append({
                    'format': 'shapefile',
                    'filename': os.path.basename(shp_path),
                    'size': os.path.getsize(shp_path),
                    'download_url': request.build_absolute_uri(
                        f'/api/v1/geodata/download/{os.path.basename(shp_path)}'
                    )
                })
            
            # Exportar GeoJSON
            if export_format in ['geojson', 'both']:
                geojson_exporter = GeoJSONExporter(output_dir='data/exports/geojson')
                
                if hasattr(obj, 'features'):
                    geojson_path = geojson_exporter.export_layer(obj, filename)
                    
                    files.append({
                        'format': 'geojson',
                        'filename': os.path.basename(geojson_path),
                        'size': os.path.getsize(geojson_path),
                        'download_url': request.build_absolute_uri(
                            f'/api/v1/geodata/download/{os.path.basename(geojson_path)}'
                        )
                    })
            
            return Response({
                'success': True,
                'message': 'Exportación completada exitosamente',
                'files': files
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='download/<str:format>')
    def download_export(self, request, pk=None, format=None):
        """
        Genera y descarga archivo directamente.
        
        GET /api/v1/geodata/layers/{id}/download/shapefile/
        GET /api/v1/geodata/layers/{id}/download/geojson/
        """
        obj = self.get_object()
        
        try:
            if format == 'shapefile':
                exporter = ShapefileExporter(output_dir='data/exports/shapefiles')
                file_path = exporter.export_layer(obj)
                content_type = 'application/zip'
            else:
                exporter = GeoJSONExporter(output_dir='data/exports/geojson')
                file_path = exporter.export_layer(obj)
                content_type = 'application/geo+json'
            
            if os.path.exists(file_path):
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=content_type
                )
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response
            
            return Response({
                'error': 'Archivo no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DataSourceViewSet(viewsets.ModelViewSet):
    """ViewSet for DataSource model."""
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DataSourceFilter
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger manual sync for this data source."""
        data_source = self.get_object()
        task = sync_data_source.delay(data_source.id)
        return Response({
            'message': 'Sincronización iniciada',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


class LayerViewSet(ExportMixin, viewsets.ModelViewSet):
    """ViewSet for Layer model with export functionality."""
    queryset = Layer.objects.select_related('data_source').all()
    serializer_class = LayerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LayerFilter
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(created_by=self.request.user)
            )
        return queryset


class FeatureViewSet(viewsets.ModelViewSet):
    """ViewSet for Feature model."""
    queryset = Feature.objects.select_related('layer').all()
    serializer_class = FeatureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = FeatureFilter
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FeatureCreateSerializer
        return FeatureSerializer


class DatasetViewSet(ExportMixin, viewsets.ModelViewSet):
    """ViewSet for Dataset model with export functionality."""
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SyncLog model (read-only)."""
    queryset = SyncLog.objects.select_related('data_source').all()
    serializer_class = SyncLogSerializer
    permission_classes = [IsAuthenticated]

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse
from .exporters import ShapefileExporter, GeoJSONExporter
from .serializers_export import ExportRequestSerializer, ExportResponseSerializer
import os


# Agregar estos métodos a DataSourceViewSet, LayerViewSet, etc.
# Los agregaremos en un mixin para reutilizar

class ExportMixin:
    """Mixin para agregar funcionalidad de exportación."""
    
    @action(detail=True, methods=['post'], url_path='export')
    def export_data(self, request, pk=None):
        """
        Exporta los datos a Shapefile o GeoJSON.
        
        Parámetros:
        - format: 'shapefile', 'geojson', o 'both'
        - filename: Nombre personalizado (opcional)
        - crs: Sistema de coordenadas (default: EPSG:4326)
        """
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        obj = self.get_object()
        export_format = serializer.validated_data['format']
        filename = serializer.validated_data.get('filename')
        crs = serializer.validated_data.get('crs', 'EPSG:4326')
        
        files = []
        
        try:
            # Exportar Shapefile
            if export_format in ['shapefile', 'both']:
                shp_exporter = ShapefileExporter(output_dir='data/exports/shapefiles')
                
                if hasattr(obj, 'features'):  # Es una Layer
                    shp_path = shp_exporter.export_layer(obj, filename)
                elif hasattr(obj, 'layers'):  # Es un Dataset
                    shp_path = shp_exporter.export_dataset(obj, filename)
                else:
                    return Response({
                        'error': 'Tipo de objeto no soportado para exportación'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                files.append({
                    'format': 'shapefile',
                    'path': shp_path,
                    'filename': os.path.basename(shp_path),
                    'size': os.path.getsize(shp_path)
                })
            
            # Exportar GeoJSON
            if export_format in ['geojson', 'both']:
                geojson_exporter = GeoJSONExporter(output_dir='data/exports/geojson')
                
                if hasattr(obj, 'features'):
                    geojson_path = geojson_exporter.export_layer(obj, filename)
                else:
                    return Response({
                        'error': 'GeoJSON solo soporta capas individuales'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                files.append({
                    'format': 'geojson',
                    'path': geojson_path,
                    'filename': os.path.basename(geojson_path),
                    'size': os.path.getsize(geojson_path)
                })
            
            # Construir URLs de descarga
            download_urls = [
                request.build_absolute_uri(f'/api/v1/geodata/download/{os.path.basename(f["path"])}')
                for f in files
            ]
            
            return Response({
                'success': True,
                'message': f'Exportación completada exitosamente',
                'files': files,
                'download_urls': download_urls
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error en exportación: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='download/<str:format>')
    def download(self, request, pk=None, format=None):
        """
        Descarga directa del archivo exportado.
        """
        obj = self.get_object()
        
        try:
            if format == 'shapefile':
                exporter = ShapefileExporter(output_dir='data/exports/shapefiles')
                file_path = exporter.export_layer(obj)
                content_type = 'application/zip'
            else:  # geojson
                exporter = GeoJSONExporter(output_dir='data/exports/geojson')
                file_path = exporter.export_layer(obj)
                content_type = 'application/geo+json'
            
            if os.path.exists(file_path):
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=content_type
                )
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response
            else:
                return Response({
                    'error': 'Archivo no encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Actualizar LayerViewSet para incluir el mixin
# Modificar la línea de definición de clase:
# class LayerViewSet(ExportMixin, viewsets.ModelViewSet):
