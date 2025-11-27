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

import tempfile
import zipfile
from pathlib import Path
from osgeo import ogr, osr
from datetime import datetime


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


    def _export_shapefile_complete(self, layer, gdf):
        """
        Exportar Shapefile COMPLETO con todos los archivos necesarios:
        .shp, .shx, .dbf, .prj, .cpg, .sbn, .sbx, .shp.xml
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / layer.name.replace(' ', '_')
            shp_path = str(base_path) + '.shp'
            
            # 1. Escribir Shapefile base (.shp, .shx, .dbf)
            gdf.to_file(shp_path, driver='ESRI Shapefile', encoding='utf-8')
            
            # 2. Crear archivo .prj (Sistema de coordenadas)
            self._create_prj_file(str(base_path) + '.prj', layer.srid)
            
            # 3. Crear archivo .cpg (Codificación UTF-8)
            self._create_cpg_file(str(base_path) + '.cpg')
            
            # 4. Crear índice espacial (.sbn, .sbx) si hay muchos features
            if gdf.shape[0] > 100:
                self._create_spatial_index(shp_path)
            
            # 5. Crear metadata XML (.shp.xml)
            self._create_shapefile_metadata(
                str(base_path) + '.shp.xml',
                layer,
                gdf
            )
            
            # 6. Comprimir todo en ZIP
            zip_filename = f'{layer.name.replace(" ", "_")}_shapefile.zip'
            zip_path = Path(tmpdir) / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx', '.shp.xml']:
                    file_path = str(base_path) + ext
                    if os.path.exists(file_path):
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
            
            # 7. Retornar ZIP
            with open(zip_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
                return response
    
    
    def _create_prj_file(self, prj_path, srid):
        """Crear archivo .prj con la proyección WKT"""
        try:
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(srid)
            with open(prj_path, 'w') as f:
                f.write(srs.ExportToWkt())
        except Exception as e:
            # Fallback a WGS84 si falla
            with open(prj_path, 'w') as f:
                f.write('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]')
    
    
    def _create_cpg_file(self, cpg_path):
        """Crear archivo .cpg con codificación UTF-8"""
        with open(cpg_path, 'w') as f:
            f.write('UTF-8')
    
    
    def _create_spatial_index(self, shp_path):
        """Crear índice espacial (.sbn, .sbx) usando OGR"""
        try:
            driver = ogr.GetDriverByName('ESRI Shapefile')
            dataSource = driver.Open(shp_path, 1)  # 1 = write mode
            if dataSource:
                layer = dataSource.GetLayer()
                # Crear índice espacial
                dataSource.ExecuteSQL(f'CREATE SPATIAL INDEX ON {layer.GetName()}')
                dataSource = None  # Cerrar
        except Exception as e:
            # No crítico si falla
            pass
    
    
    def _create_shapefile_metadata(self, xml_path, layer, gdf):
        """Crear metadata ISO 19139 en XML"""
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
    <metadata xml:lang="es">
      <idinfo>
        <citation>
          <citeinfo>
            <origin>SMGI System</origin>
            <pubdate>{datetime.now().strftime("%Y%m%d")}</pubdate>
            <title>{layer.name}</title>
          </citeinfo>
        </citation>
        <descript>
          <abstract>{layer.description or "Sin descripción"}</abstract>
          <purpose>Datos geoespaciales exportados desde SMGI</purpose>
        </descript>
        <spdom>
          <bounding>
            <westbc>{gdf.total_bounds[0]}</westbc>
            <eastbc>{gdf.total_bounds[2]}</eastbc>
            <northbc>{gdf.total_bounds[3]}</northbc>
            <southbc>{gdf.total_bounds[1]}</southbc>
          </bounding>
        </spdom>
      </idinfo>
      <spdoinfo>
        <direct>Vector</direct>
        <ptvctinf>
          <sdtsterm>
            <sdtstype>{layer.geometry_type}</sdtstype>
            <ptvctcnt>{gdf.shape[0]}</ptvctcnt>
          </sdtsterm>
        </ptvctinf>
      </spdoinfo>
      <spref>
        <horizsys>
          <geodetic>
            <horizdn>WGS84</horizdn>
            <ellips>WGS84</ellips>
          </geodetic>
        </horizsys>
      </spref>
      <metainfo>
        <metd>{datetime.now().strftime("%Y%m%d")}</metd>
        <metc>
          <cntinfo>
            <cntorgp>
              <cntorg>SMGI System</cntorg>
            </cntorgp>
          </cntinfo>
        </metc>
        <metstdn>FGDC Content Standards for Digital Geospatial Metadata</metstdn>
        <metstdv>FGDC-STD-001-1998</metstdv>
      </metainfo>
    </metadata>'''
        
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
    

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


from rest_framework.decorators import action
from .serializers_sources import (
    URLLayerSerializer,
    ArcGISLayerSerializer,
    DatabaseLayerSerializer,
    FileLayerSerializer
)
from .services.url_loader import URLLayerLoader
from .services.arcgis_loader import ArcGISLoader
from .services.database_loader import DatabaseLoader


class LayerViewSet(viewsets.ModelViewSet):
    # ... código existente ...
    
    @action(detail=False, methods=['post'])
    def from_url(self, request):
        """
        Subir capa desde URL (WMS, WFS, ArcGIS REST, GeoJSON)
        POST /api/v1/geodata/layers/from-url/
        """
        serializer = URLLayerSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Cargar según tipo de servicio
            if data['service_type'] == 'wfs':
                gdf = URLLayerLoader.load_wfs(
                    data['url'],
                    data.get('layers'),
                    data.get('username'),
                    data.get('password')
                )
            elif data['service_type'] == 'geojson':
                gdf = URLLayerLoader.load_geojson_url(
                    data['url'],
                    data.get('username'),
                    data.get('password')
                )
            elif data['service_type'] == 'arcgis':
                gdf = URLLayerLoader.load_arcgis_rest(
                    data['url'],
                    data.get('parameters', {}).get('layer_index', 0),
                    data.get('password')  # token
                )
            else:
                return Response(
                    {'error': f'Tipo de servicio {data["service_type"]} no implementado aún'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear capa
            layer = self._create_layer_from_gdf(
                gdf,
                data['name'],
                data.get('description', ''),
                request.user
            )
            
            return Response({
                'message': f'Capa cargada exitosamente desde {data["service_type"].upper()}',
                'layer': LayerSerializer(layer).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def from_arcgis(self, request):
        """
        Subir capa desde ArcGIS Online/Enterprise
        POST /api/v1/geodata/layers/from-arcgis/
        """
        serializer = ArcGISLayerSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Cargar desde ArcGIS
            if data.get('item_id'):
                gdf = ArcGISLoader.load_from_item_id(
                    data['item_id'],
                    data.get('token'),
                    data.get('layer_index', 0)
                )
            else:
                gdf = ArcGISLoader.load_feature_service(
                    data['service_url'],
                    data.get('layer_index', 0),
                    data.get('token')
                )
            
            # Crear capa
            layer = self._create_layer_from_gdf(
                gdf,
                data['name'],
                data.get('description', ''),
                request.user
            )
            
            # Si sync está habilitado, crear tarea periódica (TODO)
            if data.get('sync_enabled'):
                # Implementar con Celery Beat
                pass
            
            return Response({
                'message': 'Capa cargada exitosamente desde ArcGIS',
                'layer': LayerSerializer(layer).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def from_database(self, request):
        """
        Subir capa desde base de datos PostGIS
        POST /api/v1/geodata/layers/from-database/
        """
        serializer = DatabaseLayerSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Cargar desde PostGIS
            gdf = DatabaseLoader.load_from_postgis(
                data['host'],
                data['port'],
                data['database'],
                data['username'],
                data['password'],
                data['schema'],
                data['table'],
                data['geometry_column'],
                data.get('query')
            )
            
            # Crear capa
            layer = self._create_layer_from_gdf(
                gdf,
                data['name'],
                data.get('description', ''),
                request.user
            )
            
            return Response({
                'message': 'Capa cargada exitosamente desde base de datos',
                'layer': LayerSerializer(layer).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def get_service_info(self, request):
        """
        Obtener información de un servicio antes de cargarlo
        POST /api/v1/geodata/layers/get-service-info/
        """
        service_type = request.data.get('service_type')
        url = request.data.get('url')
        
        try:
            if service_type == 'wfs':
                info = URLLayerLoader.get_wfs_info(url)
            elif service_type == 'wms':
                info = URLLayerLoader.get_wms_info(url)
            elif service_type == 'arcgis':
                info = ArcGISLoader.get_service_info(url, request.data.get('token'))
            else:
                return Response(
                    {'error': 'Tipo de servicio no soportado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(info)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_layer_from_gdf(self, gdf, name, description, user):
        """Crear capa y features desde GeoDataFrame"""
        from django.contrib.gis.geos import GEOSGeometry
        import json
        
        # Detectar tipo de geometría
        geom_type = gdf.geometry.geom_type.value_counts().index[0]
        
        # Detectar SRID
        srid = gdf.crs.to_epsg() if gdf.crs else 4326
        
        # Crear capa
        layer = Layer.objects.create(
            name=name,
            description=description,
            geometry_type=geom_type.upper(),
            srid=srid,
            uploaded_by=user
        )
        
        # Crear features
        from .models import Feature
        features = []
        
        for idx, row in gdf.iterrows():
            geom = row.geometry
            properties = row.drop('geometry').to_dict()
            
            # Convertir geometría a GEOS
            geom_wkt = geom.wkt
            geos_geom = GEOSGeometry(geom_wkt, srid=srid)
            
            feature = Feature(
                layer=layer,
                geom=geos_geom,
                properties=properties
            )
            features.append(feature)
        
        # Bulk create
        Feature.objects.bulk_create(features, batch_size=1000)
        
        # Actualizar feature_count
        layer.feature_count = len(features)
        layer.save()
        
        return layer
