# apps/reports/generators/geojson_generator.py
"""
SMGI Backend - GeoJSON Report Generator
Sistema de Monitoreo Geoespacial Inteligente
Generador de informes en formato GeoJSON
"""
import logging
import json
import time
import os
from typing import Dict, Any, Optional, List, Union
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.geos import GEOSGeometry
from django.core.serializers import serialize

from apps.reports.generators.base_generator import BaseReportGenerator
from apps.reports.models import (
    Report, GeneratedReport, ReportFormat, ReportStatus,
    LayerSnapshot, ChangeDetectionResult
)
# Importar modelos relacionados
from apps.gis_services.models import SpatialLayer


logger = logging.getLogger('apps.reports.generators.geojson')


class GeoJSONReportGenerator(BaseReportGenerator):
    """
    Generador de informes en formato GeoJSON.
    Ideal para datos geoespaciales como features, cambios detectados, etc.
    """

    def __init__(
        self,
        name: str = "GeoJSON Report Generator",
        description: str = "Generates reports in GeoJSON format",
        is_active: bool = True,
        default_options: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa el generador de informes GeoJSON.

        Args:
            name (str): Nombre del generador.
            description (str): Descripción del generador.
            is_active (bool): Indica si el generador está activo.
            default_options (Optional[Dict[str, Any]]): Opciones por defecto.
        """
        super().__init__(
            name=name,
            description=description,
            format_type=ReportFormat.GEOJSON,
            is_active=is_active,
            default_options=default_options or {
                'include_properties': True,
                'include_bbox': True,
                'include_crs': True,
                'crs_type': 'EPSG:4326', # WGS84
                'precision': 6, # Número de decimales para coordenadas
                'indent': 2, # Indentación del JSON
                'ensure_ascii': False, # Permitir caracteres Unicode
                'sort_keys': True, # Ordenar claves del JSON
                'include_metadata': True,
                'include_style': False, # Incluir estilo (no estándar en GeoJSON)
                'include_changes': False, # Incluir información de cambios si está disponible
                'changes_as_properties': True, # Incluir cambios como propiedades de features
                'include_snapshots': False, # Incluir información de snapshots
                'snapshot_as_metadata': True, # Incluir snapshots como metadatos
            }
        )
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    def generate(self, report: Report, data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera un informe en formato GeoJSON.

        Args:
            report (Report): Instancia del modelo Report que se está generando.
            data (Dict[str, Any]): Datos para generar el informe.
                                   Debe contener 'features' como lista de diccionarios
                                   con 'geometry' (GeoJSON) y 'properties' (dict).
                                   También puede contener 'metadata' (dict).
                                   Ej: {
                                       'features': [
                                           {
                                               'geometry': {...},
                                               'properties': {'name': 'Feature 1', ...}
                                           },
                                           ...
                                       ],
                                       'metadata': {...}
                                   }
            options (Optional[Dict[str, Any]]): Opciones específicas para esta generación.

        Returns:
            Dict[str, Any]: Resultado de la generación.
        """
        start_time = time.time()
        self.logger.info(f"Starting GeoJSON report generation for {report.name}")
        
        # Merge options
        merged_options = self.default_options.copy()
        if options:
            merged_options.update(options)
        
        try:
            # Validate input data
            if not self.validate_input_data(data):
                return self.handle_error(ValueError("Invalid input data"), "Data validation failed")
            
            # Prepare output path
            output_path = self.prepare_output_path(report, suffix='.geojson')
            
            # Create base GeoJSON structure
            geojson_data = self.create_geojson_structure(merged_options)
            
            # Add features to GeoJSON
            features_added = self.add_features_to_geojson(geojson_data, data.get('features', []), merged_options)
            
            # Add metadata to GeoJSON
            self.add_metadata_to_geojson(geojson_data, data.get('metadata', {}), report, merged_options)
            
            # Add changes information if requested and available
            if merged_options.get('include_changes', False):
                changes_data = data.get('changes', [])
                self.add_changes_to_geojson(geojson_data, changes_data, merged_options)
            
            # Add snapshot information if requested and available
            if merged_options.get('include_snapshots', False):
                snapshots_data = data.get('snapshots', [])
                self.add_snapshots_to_geojson(geojson_data, snapshots_data, merged_options)
            
            # Serialize and save GeoJSON to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(
                    geojson_data,
                    f,
                    indent=merged_options.get('indent', 2),
                    ensure_ascii=merged_options.get('ensure_ascii', False),
                    sort_keys=merged_options.get('sort_keys', True)
                )
            
            # Get file size
            file_size_bytes = os.path.getsize(output_path)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Calculate record/pages count
            record_count = len(data.get('features', []))
            page_count = 1 # GeoJSON es un solo "documento"
            
            self.logger.info(f"GeoJSON report generated successfully for {report.name} in {duration_ms} ms")
            
            return {
                'success': True,
                'file_path': output_path,
                'file_size_bytes': file_size_bytes,
                'duration_ms': duration_ms,
                'records': record_count,
                'pages': page_count,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Error generating GeoJSON report for {report.name}: {e}"
            self.logger.error(error_msg)
            return self.handle_error(e, "GeoJSON generation failed")
        finally:
            # Cleanup temp files (handled by context manager or explicit call)
            # self.cleanup_temp_files() # No es necesario llamarlo aquí si se usa context manager
            pass

    def create_geojson_structure(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea la estructura base de un FeatureCollection GeoJSON.

        Args:
            options (Dict[str, Any]): Opciones de generación.

        Returns:
            Dict[str, Any]: Diccionario con la estructura base de GeoJSON.
        """
        geojson = {
            'type': 'FeatureCollection',
            'features': []
        }
        
        # Add bounding box if requested
        if options.get('include_bbox', False):
            # bbox will be calculated and added when features are added
            pass # Will be added in add_features_to_geojson
        
        # Add CRS if requested
        if options.get('include_crs', False):
            crs_type = options.get('crs_type', 'EPSG:4326')
            if crs_type.startswith('EPSG:'):
                epsg_code = crs_type.split(':')[1]
                geojson['crs'] = {
                    'type': 'name',
                    'properties': {
                        'name': f'urn:ogc:def:crs:EPSG::{epsg_code}'
                    }
                }
            # Add support for other CRS types if needed
        
        return geojson

    def add_features_to_geojson(self, geojson_data: Dict[str, Any], features: List[Dict[str, Any]], options: Dict[str, Any]) -> int:
        """
        Añade features (geometrías y propiedades) al FeatureCollection GeoJSON.

        Args:
            geojson_data (Dict[str, Any]): Diccionario con la estructura GeoJSON.
            features (List[Dict[str, Any]]): Lista de features a añadir.
            options (Dict[str, Any]): Opciones de generación.

        Returns:
            int: Número de features añadidas.
        """
        added_count = 0
        all_coords = []
        
        for feature in features:
            # Validate feature
            if not self.validate_geojson_feature(feature):
                self.logger.warning(f"Skipping invalid feature: {feature}")
                continue
            
            # Create GeoJSON feature
            geojson_feature = {
                'type': 'Feature',
                'geometry': feature.get('geometry'),
                'properties': feature.get('properties', {}) if options.get('include_properties', True) else {}
            }
            
            # Add feature to GeoJSON
            geojson_data['features'].append(geojson_feature)
            added_count += 1
            
            # Collect coordinates for bbox calculation if needed
            if options.get('include_bbox', False):
                geom = feature.get('geometry')
                if geom:
                    try:
                        geos_geom = GEOSGeometry(json.dumps(geom))
                        if geos_geom:
                            # Get envelope coordinates
                            envelope = geos_geom.envelope
                            if envelope:
                                coords = envelope.coords
                                if coords:
                                    # coords is a tuple of tuples, e.g., ((minx, miny), (maxx, maxy))
                                    # For polygons, it's more complex. Simplify for bbox calculation.
                                    if hasattr(coords, '__iter__') and len(coords) > 0:
                                        if isinstance(coords[0], tuple) and len(coords[0]) >= 2:
                                            all_coords.extend(coords)
                    except Exception as e:
                        self.logger.warning(f"Could not calculate bbox for feature geometry: {e}")
        
        # Calculate and add bbox if requested
        if options.get('include_bbox', False) and all_coords:
            try:
                min_x = min(coord[0] for coord in all_coords)
                min_y = min(coord[1] for coord in all_coords)
                max_x = max(coord[0] for coord in all_coords)
                max_y = max(coord[1] for coord in all_coords)
                geojson_data['bbox'] = [min_x, min_y, max_x, max_y]
            except Exception as e:
                self.logger.warning(f"Could not calculate overall bbox: {e}")
        
        return added_count

    def add_metadata_to_geojson(self, geojson_data: Dict[str, Any], metadata: Dict[str, Any], report: Report, options: Dict[str, Any]):
        """
        Añade metadatos del informe al FeatureCollection GeoJSON.

        Args:
            geojson_data (Dict[str, Any]): Diccionario con la estructura GeoJSON.
            metadata (Dict[str, Any]): Metadatos adicionales a incluir.
            report (Report): Instancia del modelo Report.
            options (Dict[str, Any]): Opciones de generación.
        """
        if not options.get('include_metadata', True):
            return
        
        # Prepare metadata
        report_metadata = {
            'report_id': str(report.id),
            'report_name': report.name,
            'report_description': report.description,
            'report_type': report.get_report_type_display(),
            'report_format': report.get_format_type_display(),
            'generated_at': timezone.now().isoformat(),
            'generated_by': report.created_by.get_full_name() if report.created_by else 'System',
            'service_name': report.service.name if report.service else None,
            'layer_name': report.layer.name if report.layer else None,
            'feature_count': len(geojson_data['features']),
            'bbox': geojson_data.get('bbox'),
            'crs': geojson_data.get('crs'),
        }
        
        # Merge with provided metadata
        report_metadata.update(metadata)
        
        # Add to GeoJSON as a property of the FeatureCollection
        # GeoJSON standard does not define a 'metadata' field, but it's commonly used
        # Alternatively, could be added to a custom property or as part of 'properties'
        geojson_data['metadata'] = report_metadata

    def add_changes_to_geojson(self, geojson_data: Dict[str, Any], changes: List[Dict[str, Any]], options: Dict[str, Any]):
        """
        Añade información de cambios detectados al GeoJSON.

        Args:
            geojson_data (Dict[str, Any]): Diccionario con la estructura GeoJSON.
            changes (List[Dict[str, Any]]): Lista de cambios detectados.
            options (Dict[str, Any]): Opciones de generación.
        """
        if not changes:
            return
        
        try:
            # Add changes as a top-level property
            geojson_data['changes'] = changes
            
            # If requested, add change info as properties to individual features
            if options.get('changes_as_properties', True):
                changes_dict = {change.get('feature_id'): change for change in changes if change.get('feature_id')}
                
                for feature in geojson_data['features']:
                    feature_id = feature.get('properties', {}).get('id') or feature.get('id')
                    if feature_id and feature_id in changes_dict:
                        change_info = changes_dict[feature_id]
                        # Add change info to feature properties
                        if 'change_info' not in feature['properties']:
                            feature['properties']['change_info'] = change_info
                        else:
                            # Merge or append if change_info already exists
                            feature['properties']['change_info'].update(change_info)
        
        except Exception as e:
            self.logger.warning(f"Could not add changes to GeoJSON: {e}")

    def add_snapshots_to_geojson(self, geojson_data: Dict[str, Any], snapshots: List[Dict[str, Any]], options: Dict[str, Any]):
        """
        Añade información de snapshots al GeoJSON.

        Args:
            geojson_data (Dict[str, Any]): Diccionario con la estructura GeoJSON.
            snapshots (List[Dict[str, Any]]): Lista de snapshots.
            options (Dict[str, Any]): Opciones de generación.
        """
        if not snapshots:
            return
        
        try:
            # Add snapshots as a top-level property
            geojson_data['snapshots'] = snapshots
            
            # If requested, add snapshot info as metadata
            if options.get('snapshot_as_metadata', True):
                # Add snapshot summary to metadata
                snapshot_summary = {
                    'snapshot_count': len(snapshots),
                    'latest_snapshot': snapshots[0] if snapshots else None,
                    'oldest_snapshot': snapshots[-1] if snapshots else None
                }
                
                if 'metadata' not in geojson_data:
                    geojson_data['metadata'] = {}
                
                geojson_data['metadata']['snapshots_summary'] = snapshot_summary
        
        except Exception as e:
            self.logger.warning(f"Could not add snapshots to GeoJSON: {e}")

    def validate_geojson_feature(self, feature: Dict[str, Any]) -> bool:
        """
        Valida que una feature tenga una geometría válida según el estándar GeoJSON.

        Args:
            feature (Dict[str, Any]): Feature a validar.

        Returns:
            bool: True si la feature es válida, False en caso contrario.
        """
        if not isinstance(feature, dict):
            return False
        
        geometry = feature.get('geometry')
        if not geometry or not isinstance(geometry, dict):
            return False
        
        geom_type = geometry.get('type')
        if not geom_type or not isinstance(geom_type, str):
            return False
        
        coordinates = geometry.get('coordinates')
        if coordinates is None: # Allow empty geometries like null geometries?
            # According to GeoJSON spec, coordinates is required for geometries
            # except for GeometryCollection. For simplicity, we require it.
            return False
        
        # Basic validation of geometry types
        valid_geom_types = [
            'Point', 'MultiPoint', 'LineString', 'MultiLineString',
            'Polygon', 'MultiPolygon', 'GeometryCollection'
        ]
        
        if geom_type not in valid_geom_types:
            return False
        
        # More rigorous validation would require checking coordinate structure
        # This is a basic check. For production, consider using a GeoJSON validator library.
        
        return True

    def validate_input_data(self,  Dict[str, Any]) -> bool:
        """
        Valida los datos de entrada específicos para generación de GeoJSON.

        Args:
            data (Dict[str, Any]): Datos para validar.

        Returns:
            bool: True si los datos son válidos, False en caso contrario.
        """
        # Llamar al método de validación base
        if not super().validate_input_data(data):
            return False
        
        # Validación específica para GeoJSON: verificar estructura de 'features'
        features = data.get('features')
        if features is not None:
            if not isinstance(features, list):
                self.logger.error("GeoJSON generator expects 'features' to be a list.")
                return False
            
            for i, feature in enumerate(features):
                if not isinstance(feature, dict):
                    self.logger.error(f"Feature at index {i} must be a dictionary.")
                    return False
                
                geometry = feature.get('geometry')
                if not geometry or not isinstance(geometry, dict):
                    self.logger.error(f"Feature at index {i} must have a 'geometry' dictionary.")
                    return False
                
                properties = feature.get('properties')
                if properties is not None and not isinstance(properties, dict):
                    self.logger.error(f"Properties for feature at index {i} must be a dictionary.")
                    return False
        
        return True
