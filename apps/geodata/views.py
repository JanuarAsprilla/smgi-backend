"""
Views for Geodata app - SMGI Sistema de Monitoreo Geoespacial Inteligente.
Includes upload functionality for shapefiles, GeoJSON, KML, GeoPackage.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Q
from django.http import FileResponse, HttpResponse
import os
import json
import tempfile
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import logging

from .models import DataSource, Layer, Feature, Dataset, SyncLog
from .serializers import (
    DataSourceSerializer,
    LayerSerializer,
    FeatureSerializer,
    FeatureCreateSerializer,
    DatasetSerializer,
    SyncLogSerializer,
    URLLayerSerializer,
    ArcGISLayerSerializer,
    DatabaseLayerSerializer,
)
from .serializers_export import ExportRequestSerializer
from .filters import DataSourceFilter, LayerFilter, FeatureFilter
from .tasks import sync_data_source
from .exporters import ShapefileExporter, GeoJSONExporter
from apps.users.permissions import IsAnalystOrAbove

logger = logging.getLogger(__name__)


class ExportMixin:
    """Mixin para agregar funcionalidad de exportación."""
    
    @action(detail=True, methods=['post'], url_path='export')
    def export_data(self, request, pk=None):
        """
        Exporta los datos a Shapefile o GeoJSON.
        """
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        obj = self.get_object()
        export_format = serializer.validated_data['format']
        filename = serializer.validated_data.get('filename')
        
        files = []
        
        try:
            if export_format in ['shapefile', 'both']:
                shp_exporter = ShapefileExporter(output_dir='data/exports/shapefiles')
                
                if hasattr(obj, 'features'):
                    result = shp_exporter.export_layer(obj, filename)
                    shp_path = result.get('file_path', result) if isinstance(result, dict) else result
                elif hasattr(obj, 'layers'):
                    result = shp_exporter.export_dataset(obj, filename)
                    shp_path = result.get('file_path', result) if isinstance(result, dict) else result
                else:
                    return Response({
                        'error': 'Tipo de objeto no soportado'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                files.append({
                    'format': 'shapefile',
                    'filename': os.path.basename(shp_path),
                    'size': os.path.getsize(shp_path) if os.path.exists(shp_path) else 0,
                    'download_url': request.build_absolute_uri(
                        f'/api/v1/geodata/download/{os.path.basename(shp_path)}'
                    )
                })
            
            if export_format in ['geojson', 'both']:
                geojson_exporter = GeoJSONExporter(output_dir='data/exports/geojson')
                
                if hasattr(obj, 'features'):
                    result = geojson_exporter.export_layer(obj, filename)
                    geojson_path = result.get('file_path', result) if isinstance(result, dict) else result
                    
                    files.append({
                        'format': 'geojson',
                        'filename': os.path.basename(geojson_path),
                        'size': os.path.getsize(geojson_path) if os.path.exists(geojson_path) else 0,
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
            logger.error(f"Export error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='download/(?P<format_type>[^/.]+)')
    def download_export(self, request, pk=None, format_type=None):
        """Genera y descarga archivo directamente."""
        obj = self.get_object()
        
        try:
            if format_type == 'shapefile':
                exporter = ShapefileExporter(output_dir='data/exports/shapefiles')
                result = exporter.export_layer(obj)
                file_path = result.get('file_path', result) if isinstance(result, dict) else result
                content_type = 'application/zip'
            else:
                exporter = GeoJSONExporter(output_dir='data/exports/geojson')
                result = exporter.export_layer(obj)
                file_path = result.get('file_path', result) if isinstance(result, dict) else result
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
            logger.error(f"Download error: {str(e)}", exc_info=True)
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
    """
    ViewSet for Layer model with upload and export functionality.
    """
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = [DjangoFilterBackend]
    filterset_class = LayerFilter
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = Layer.objects.all()
        user = self.request.user
        if not user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(created_by=user)
            )
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user,)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """
        Upload shapefile, geojson, kml, gpkg.
        
        POST /api/v1/geodata/layers/upload/
        """
        import geopandas as gpd
        
        logger.info(f"Upload request - FILES: {request.FILES}")
        logger.info(f"Upload request - DATA: {request.data}")
        
        file = request.FILES.get('file')
        if not file:
            logger.error("No file in request")
            return Response(
                {'error': 'No se proporcionó ningún archivo'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        max_size = 500 * 1024 * 1024
        if file.size > max_size:
            return Response(
                {'error': f'El archivo excede el tamaño máximo permitido (500MB). Tamaño: {file.size / (1024*1024):.2f}MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        name = request.data.get('name', '').strip()
        if not name:
            name = file.name.rsplit('.', 1)[0]
        
        description = request.data.get('description', '')
        temp_dir = tempfile.mkdtemp()
        
        logger.info(f"Processing file: {file.name}, size: {file.size}")
        
        try:
            file_path = os.path.join(temp_dir, file.name)
            with open(file_path, 'wb') as f:
                for chunk in file.chunks():
                    f.write(chunk)
            
            logger.info(f"File saved to: {file_path}")
            
            gdf = self._read_geodata_file(file_path, file.name, temp_dir)
            
            logger.info(f"Read {len(gdf)} features from file")
            
            if len(gdf) == 0:
                raise ValueError('El archivo no contiene features')
            
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
                gdf = gdf.to_crs(epsg=4326)
            elif gdf.crs is None:
                logger.warning("No CRS found, assuming EPSG:4326")
                gdf = gdf.set_crs(epsg=4326)
            
            geom_types = gdf.geometry.geom_type.unique()
            if len(geom_types) > 1:
                geom_type = 'GEOMETRY'
            else:
                geom_type = str(geom_types[0]).upper()
                geom_type_mapping = {
                    'POINT': 'POINT',
                    'LINESTRING': 'LINESTRING',
                    'POLYGON': 'POLYGON',
                    'MULTIPOINT': 'MULTIPOINT',
                    'MULTILINESTRING': 'MULTILINESTRING',
                    'MULTIPOLYGON': 'MULTIPOLYGON',
                    'GEOMETRYCOLLECTION': 'GEOMETRYCOLLECTION',
                }
                geom_type = geom_type_mapping.get(geom_type, 'GEOMETRY')
            
            logger.info(f"Geometry type: {geom_type}")
            
            layer = Layer.objects.create(
                name=name,
                description=description,
                geometry_type=geom_type,
                layer_type='vector',
                srid=4326,
                created_by=request.user,
                feature_count=0,
                original_filename=file.name,
                file_size=file.size,
                is_public=False
            )
            
            logger.info(f"Created layer: {layer.id}")
            
            features_created = self._create_features_batch(layer, gdf, request.user)
            
            if features_created > 0:
                layer.feature_count = features_created
                layer.save(update_fields=['feature_count'])
                logger.info(f"Created {features_created} features")
            else:
                layer.delete()
                raise ValueError('No se pudieron crear features válidos')
            
            return Response({
                'message': f'Capa "{name}" subida exitosamente',
                'layer': {
                    'id': layer.id,
                    'name': layer.name,
                    'description': layer.description,
                    'geometry_type': layer.geometry_type,
                    'feature_count': layer.feature_count,
                    'srid': layer.srid,
                    'created_at': layer.created_at.isoformat(),
                    'original_filename': layer.original_filename,
                    'file_size': layer.file_size,
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Upload error: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _read_geodata_file(self, file_path, filename, temp_dir):
        """Lee archivos geoespaciales de diferentes formatos."""
        import geopandas as gpd
        
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.zip'):
            logger.info("Processing ZIP file")
            with zipfile.ZipFile(file_path) as zf:
                zf.extractall(temp_dir)
            
            shp_files = list(Path(temp_dir).rglob('*.shp'))
            if shp_files:
                logger.info(f"Found .shp file: {shp_files[0]}")
                return gpd.read_file(str(shp_files[0]))
            
            geojson_files = list(Path(temp_dir).rglob('*.geojson')) + list(Path(temp_dir).rglob('*.json'))
            if geojson_files:
                logger.info(f"Found GeoJSON file: {geojson_files[0]}")
                return gpd.read_file(str(geojson_files[0]))
            
            gpkg_files = list(Path(temp_dir).rglob('*.gpkg'))
            if gpkg_files:
                logger.info(f"Found GeoPackage file: {gpkg_files[0]}")
                return gpd.read_file(str(gpkg_files[0]))
            
            kml_files = list(Path(temp_dir).rglob('*.kml'))
            if kml_files:
                logger.info(f"Found KML file: {kml_files[0]}")
                return gpd.read_file(str(kml_files[0]), driver='KML')
            
            raise ValueError('No se encontró archivo geoespacial válido en el ZIP')
        
        elif filename_lower.endswith(('.geojson', '.json')):
            logger.info("Processing GeoJSON file")
            return gpd.read_file(file_path)
        
        elif filename_lower.endswith('.kml'):
            logger.info("Processing KML file")
            return gpd.read_file(file_path, driver='KML')
        
        elif filename_lower.endswith('.gpkg'):
            logger.info("Processing GeoPackage file")
            return gpd.read_file(file_path)
        
        elif filename_lower.endswith('.shp'):
            logger.info("Processing Shapefile")
            return gpd.read_file(file_path)
        
        else:
            raise ValueError(f'Formato de archivo no soportado: {filename}')
    
    def _create_features_batch(self, layer, gdf, user, batch_size=1000):
        """Crea features en lotes para mejor rendimiento."""
        features = []
        created_count = 0
        skipped_count = 0
        
        for idx, row in gdf.iterrows():
            if row.geometry is None or row.geometry.is_empty:
                skipped_count += 1
                continue
            
            props = {}
            for col in gdf.columns:
                if col != 'geometry':
                    val = row[col]
                    if hasattr(val, 'item'):
                        val = val.item()
                    if val != val:
                        val = None
                    if val is not None and not isinstance(val, (str, int, float, bool, list, dict)):
                        val = str(val)
                    props[col] = val
            
            try:
                geom = GEOSGeometry(row.geometry.wkt, srid=4326)
                features.append(Feature(
                    layer=layer, 
                    geometry=geom,
                    properties=props,
                    created_by=user
                ))
                
                if len(features) >= batch_size:
                    Feature.objects.bulk_create(features, batch_size=batch_size)
                    created_count += len(features)
                    logger.info(f"Batch inserted: {created_count} features")
                    features = []
                    
            except Exception as e:
                logger.warning(f"Failed to create feature {idx}: {e}")
                skipped_count += 1
                continue
        
        if features:
            Feature.objects.bulk_create(features, batch_size=batch_size)
            created_count += len(features)
        
        if skipped_count > 0:
            logger.warning(f"Skipped {skipped_count} invalid features")
        
        return created_count

    @action(detail=True, methods=['get'])
    def geojson(self, request, pk=None):
        """Retorna la capa como GeoJSON para visualización en mapa."""
        layer = self.get_object()
        features = layer.features.filter(is_active=True)
        
        geojson = {
            "type": "FeatureCollection",
            "name": layer.name,
            "crs": {
                "type": "name",
                "properties": {
                    "name": f"urn:ogc:def:crs:EPSG::{layer.srid}"
                }
            },
            "features": []
        }
        
        for feature in features:
            try:
                geojson["features"].append({
                    "type": "Feature",
                    "id": feature.id,
                    "geometry": json.loads(feature.geometry.geojson),
                    "properties": feature.properties or {}
                })
            except Exception as e:
                logger.warning(f"Error serializing feature {feature.id}: {e}")
                continue
        
        return Response(geojson)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Retorna estadísticas de la capa."""
        layer = self.get_object()
        features = layer.features.filter(is_active=True)
        
        return Response({
            'layer_id': layer.id,
            'name': layer.name,
            'feature_count': features.count(),
            'geometry_type': layer.geometry_type,
            'srid': layer.srid,
            'is_public': layer.is_public,
            'created_at': layer.created_at.isoformat(),
            'updated_at': layer.updated_at.isoformat(),
            'original_filename': layer.original_filename,
            'file_size': layer.file_size,
        })

    @action(detail=False, methods=['post'], url_path='from-url')
    def from_url(self, request):
        """
        Crear capa desde URL externa (GeoJSON, KML, WMS, WFS).
        
        POST /api/v1/geodata/layers/from-url/
        {
            "name": "Mi Capa",
            "description": "Descripción opcional",
            "url": "https://example.com/data.geojson",
            "service_type": "geojson",
            "is_public": false,
            "tags": ["tag1", "tag2"]
        }
        """
        serializer = URLLayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            import requests
            import geopandas as gpd
            
            # Descargar datos desde URL
            logger.info(f"Fetching data from URL: {data['url']}")
            response = requests.get(data['url'], timeout=30)
            response.raise_for_status()
            
            # Procesar según el tipo de servicio
            temp_dir = tempfile.mkdtemp()
            try:
                service_type = data['service_type']
                
                if service_type == 'geojson':
                    # Cargar GeoJSON directamente
                    gdf = gpd.read_file(data['url'])
                    
                elif service_type == 'kml':
                    # Guardar y cargar KML
                    temp_file = os.path.join(temp_dir, 'data.kml')
                    with open(temp_file, 'wb') as f:
                        f.write(response.content)
                    gdf = gpd.read_file(temp_file, driver='KML')
                    
                elif service_type in ['wms', 'wfs']:
                    return Response({
                        'error': f'Tipo de servicio {service_type} aún no soportado. Use geojson o kml.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        'error': f'Tipo de servicio no reconocido: {service_type}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Reproyectar a EPSG:4326 si es necesario
                if gdf.crs and gdf.crs.to_epsg() != 4326:
                    logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
                    gdf = gdf.to_crs(epsg=4326)
                elif gdf.crs is None:
                    gdf = gdf.set_crs(epsg=4326)
                
                # Detectar tipo de geometría
                geom_types = gdf.geometry.geom_type.unique()
                if len(geom_types) > 1:
                    geom_type = 'GEOMETRY'
                else:
                    geom_type = str(geom_types[0]).upper()
                
                # Crear capa
                layer = Layer.objects.create(
                    name=data['name'],
                    description=data.get('description', ''),
                    geometry_type=geom_type,
                    layer_type='vector',
                    srid=4326,
                    created_by=request.user,
                    is_public=data.get('is_public', False),
                    tags=data.get('tags', []),
                    feature_count=0
                )
                
                # Crear features
                features_created = self._create_features_batch(layer, gdf, request.user)
                
                if features_created > 0:
                    layer.feature_count = features_created
                    layer.save(update_fields=['feature_count'])
                else:
                    layer.delete()
                    raise ValueError('No se pudieron crear features válidos')
                
                return Response({
                    'message': f'Capa "{layer.name}" creada desde URL exitosamente',
                    'layer': {
                        'id': layer.id,
                        'name': layer.name,
                        'description': layer.description,
                        'geometry_type': layer.geometry_type,
                        'feature_count': layer.feature_count,
                        'source_url': data['url'],
                    }
                }, status=status.HTTP_201_CREATED)
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except requests.RequestException as e:
            logger.error(f"Error fetching URL: {str(e)}")
            return Response({
                'error': f'Error al acceder a la URL: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating layer from URL: {str(e)}", exc_info=True)
            return Response({
                'error': f'Error al crear capa: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='from-arcgis')
    def from_arcgis(self, request):
        """
        Crear capa desde servicio ArcGIS (MapServer o FeatureServer).
        
        POST /api/v1/geodata/layers/from-arcgis/
        {
            "name": "Mi Capa ArcGIS",
            "description": "Descripción opcional",
            "service_url": "https://services.arcgis.com/.../MapServer/0",
            "layer_id": 0,
            "username": "opcional",
            "password": "opcional",
            "is_public": false,
            "tags": ["arcgis", "external"]
        }
        """
        serializer = ArcGISLayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            import requests
            import geopandas as gpd
            from io import BytesIO
            
            service_url = data['service_url']
            layer_id = data.get('layer_id', 0)
            
            # Construir URL de query
            if not service_url.endswith('/'):
                service_url += '/'
            
            # URL para obtener metadata
            metadata_url = f"{service_url}?f=json"
            
            # Preparar autenticación si es necesaria
            auth = None
            if data.get('username') and data.get('password'):
                auth = (data['username'], data['password'])
            
            logger.info(f"Fetching ArcGIS metadata from: {metadata_url}")
            response = requests.get(metadata_url, auth=auth, timeout=30)
            response.raise_for_status()
            metadata = response.json()
            
            # URL para obtener features (GeoJSON)
            query_url = f"{service_url}/query"
            params = {
                'where': '1=1',
                'outFields': '*',
                'f': 'geojson',
                'returnGeometry': 'true'
            }
            
            logger.info(f"Fetching features from: {query_url}")
            response = requests.get(query_url, params=params, auth=auth, timeout=60)
            response.raise_for_status()
            
            # Cargar GeoJSON en GeoDataFrame
            geojson_data = response.json()
            gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
            
            if len(gdf) == 0:
                raise ValueError('El servicio no contiene features')
            
            # Asegurar CRS EPSG:4326
            if gdf.crs is None:
                gdf = gdf.set_crs(epsg=4326)
            elif gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(epsg=4326)
            
            # Detectar tipo de geometría
            geom_types = gdf.geometry.geom_type.unique()
            if len(geom_types) > 1:
                geom_type = 'GEOMETRY'
            else:
                geom_type = str(geom_types[0]).upper()
            
            # Crear capa
            layer = Layer.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                geometry_type=geom_type,
                layer_type='vector',
                srid=4326,
                created_by=request.user,
                is_public=data.get('is_public', False),
                tags=data.get('tags', []),
                metadata={
                    'source': 'arcgis',
                    'service_url': service_url,
                    'layer_id': layer_id,
                    'service_metadata': metadata
                },
                feature_count=0
            )
            
            # Crear features
            features_created = self._create_features_batch(layer, gdf, request.user)
            
            if features_created > 0:
                layer.feature_count = features_created
                layer.save(update_fields=['feature_count'])
            else:
                layer.delete()
                raise ValueError('No se pudieron crear features válidos')
            
            return Response({
                'message': f'Capa "{layer.name}" creada desde ArcGIS exitosamente',
                'layer': {
                    'id': layer.id,
                    'name': layer.name,
                    'description': layer.description,
                    'geometry_type': layer.geometry_type,
                    'feature_count': layer.feature_count,
                    'service_url': service_url,
                }
            }, status=status.HTTP_201_CREATED)
            
        except requests.RequestException as e:
            logger.error(f"Error fetching ArcGIS service: {str(e)}")
            return Response({
                'error': f'Error al acceder al servicio ArcGIS: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating layer from ArcGIS: {str(e)}", exc_info=True)
            return Response({
                'error': f'Error al crear capa desde ArcGIS: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='from-database')
    def from_database(self, request):
        """
        Crear capa desde conexión a base de datos externa.
        
        POST /api/v1/geodata/layers/from-database/
        {
            "name": "Mi Capa DB",
            "description": "Descripción opcional",
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "gis_db",
            "schema": "public",
            "table": "mi_tabla",
            "geometry_column": "geom",
            "username": "user",
            "password": "pass",
            "srid": 4326,
            "is_public": false,
            "tags": ["database", "external"]
        }
        """
        serializer = DatabaseLayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            import geopandas as gpd
            from sqlalchemy import create_engine
            
            # Construir connection string según el tipo de DB
            db_type = data['db_type']
            host = data['host']
            port = data['port']
            database = data['database']
            username = data['username']
            password = data['password']
            schema = data.get('schema', 'public')
            table = data['table']
            geom_col = data.get('geometry_column', 'geom')
            srid = data.get('srid', 4326)
            
            if db_type == 'postgresql':
                conn_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            elif db_type == 'mysql':
                conn_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
            elif db_type == 'oracle':
                conn_string = f"oracle+cx_oracle://{username}:{password}@{host}:{port}/{database}"
            elif db_type == 'sqlserver':
                conn_string = f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}"
            else:
                return Response({
                    'error': f'Tipo de base de datos no soportado: {db_type}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Connecting to {db_type} database: {host}:{port}/{database}")
            
            # Crear engine de SQLAlchemy
            engine = create_engine(conn_string)
            
            # Leer datos geoespaciales
            query = f'SELECT * FROM {schema}.{table}'
            logger.info(f"Executing query: {query}")
            
            gdf = gpd.read_postgis(
                query,
                engine,
                geom_col=geom_col,
                crs=f'EPSG:{srid}'
            )
            
            if len(gdf) == 0:
                raise ValueError('La tabla no contiene registros')
            
            # Reproyectar a EPSG:4326 si es necesario
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                logger.info(f"Reprojecting from EPSG:{srid} to EPSG:4326")
                gdf = gdf.to_crs(epsg=4326)
            elif gdf.crs is None:
                gdf = gdf.set_crs(epsg=4326)
            
            # Detectar tipo de geometría
            geom_types = gdf.geometry.geom_type.unique()
            if len(geom_types) > 1:
                geom_type = 'GEOMETRY'
            else:
                geom_type = str(geom_types[0]).upper()
            
            # Crear capa
            layer = Layer.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                geometry_type=geom_type,
                layer_type='vector',
                srid=4326,
                created_by=request.user,
                is_public=data.get('is_public', False),
                tags=data.get('tags', []),
                metadata={
                    'source': 'database',
                    'db_type': db_type,
                    'host': host,
                    'database': database,
                    'schema': schema,
                    'table': table,
                    'geometry_column': geom_col,
                    'original_srid': srid
                },
                feature_count=0
            )
            
            # Crear features
            features_created = self._create_features_batch(layer, gdf, request.user)
            
            # Cerrar conexión
            engine.dispose()
            
            if features_created > 0:
                layer.feature_count = features_created
                layer.save(update_fields=['feature_count'])
            else:
                layer.delete()
                raise ValueError('No se pudieron crear features válidos')
            
            return Response({
                'message': f'Capa "{layer.name}" creada desde base de datos exitosamente',
                'layer': {
                    'id': layer.id,
                    'name': layer.name,
                    'description': layer.description,
                    'geometry_type': layer.geometry_type,
                    'feature_count': layer.feature_count,
                    'source': f'{db_type}://{host}:{port}/{database}/{schema}.{table}',
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating layer from database: {str(e)}", exc_info=True)
            return Response({
                'error': f'Error al conectar con la base de datos: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class FeatureViewSet(viewsets.ModelViewSet):
    """ViewSet for Feature model."""
    queryset = Feature.objects.select_related('layer').all()
    serializer_class = FeatureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = FeatureFilter
    
    def get_queryset(self):
        queryset = Feature.objects.all()
        layer_id = self.request.query_params.get('layer')
        if layer_id:
            queryset = queryset.filter(layer_id=layer_id)
        return queryset.filter(is_active=True)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FeatureCreateSerializer
        return FeatureSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DatasetViewSet(ExportMixin, viewsets.ModelViewSet):
    """ViewSet for Dataset model with export functionality."""
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SyncLog model (read-only)."""
    queryset = SyncLog.objects.all()
    serializer_class = SyncLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = SyncLog.objects.all()
        data_source_id = self.request.query_params.get('data_source')
        layer_id = self.request.query_params.get('layer')
        
        if data_source_id:
            queryset = queryset.filter(data_source_id=data_source_id)
        if layer_id:
            queryset = queryset.filter(layer_id=layer_id)
        
        return queryset.order_by('-started_at')