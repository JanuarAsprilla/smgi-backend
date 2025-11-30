"""
Utility functions for Geodata app.
"""
from typing import Dict, Any, Optional, List
from django.contrib.gis.geos import GEOSGeometry, Point, LineString, Polygon
from django.contrib.gis.gdal import DataSource as GDALDataSource
import json
import logging

logger = logging.getLogger(__name__)


def validate_geometry(geom_data: Any) -> Optional[GEOSGeometry]:
    """
    Valida y convierte datos de geometría a GEOSGeometry.
    
    Args:
        geom_data: Datos de geometría (dict, str, GEOSGeometry)
    
    Returns:
        GEOSGeometry object o None si no es válido
    """
    try:
        if isinstance(geom_data, GEOSGeometry):
            return geom_data
        
        if isinstance(geom_data, dict):
            # GeoJSON
            return GEOSGeometry(json.dumps(geom_data))
        
        if isinstance(geom_data, str):
            # WKT o GeoJSON string
            try:
                return GEOSGeometry(geom_data)
            except:
                return GEOSGeometry(json.loads(geom_data))
        
        return None
    except Exception as e:
        logger.error(f"Error validating geometry: {e}")
        return None


def transform_geometry(geom: GEOSGeometry, target_srid: int) -> GEOSGeometry:
    """
    Transforma geometría a otro SRID.
    
    Args:
        geom: Geometría a transformar
        target_srid: SRID destino
    
    Returns:
        Geometría transformada
    """
    if geom.srid != target_srid:
        geom.transform(target_srid)
    return geom


def calculate_bounds(features) -> Optional[Dict[str, float]]:
    """
    Calcula los límites de un conjunto de features.
    
    Args:
        features: QuerySet de Feature
    
    Returns:
        Dict con bounds {minx, miny, maxx, maxy}
    """
    from django.contrib.gis.db.models.functions import Extent
    
    extent = features.aggregate(extent=Extent('geometry'))['extent']
    if extent:
        return {
            'minx': extent[0],
            'miny': extent[1],
            'maxx': extent[2],
            'maxy': extent[3]
        }
    return None


def simplify_geometry(geom: GEOSGeometry, tolerance: float = 0.0001) -> GEOSGeometry:
    """
    Simplifica geometría usando algoritmo Douglas-Peucker.
    
    Args:
        geom: Geometría a simplificar
        tolerance: Tolerancia de simplificación
    
    Returns:
        Geometría simplificada
    """
    return geom.simplify(tolerance=tolerance, preserve_topology=True)


def geometry_to_geojson(geom: GEOSGeometry) -> Dict[str, Any]:
    """
    Convierte GEOSGeometry a GeoJSON dict.
    
    Args:
        geom: Geometría a convertir
    
    Returns:
        Dict GeoJSON
    """
    return json.loads(geom.geojson)


def geojson_to_geometry(geojson: Dict[str, Any], srid: int = 4326) -> GEOSGeometry:
    """
    Convierte GeoJSON dict a GEOSGeometry.
    
    Args:
        geojson: Dict GeoJSON
        srid: SRID a asignar
    
    Returns:
        GEOSGeometry
    """
    geom = GEOSGeometry(json.dumps(geojson))
    geom.srid = srid
    return geom


def validate_srid(srid: int) -> bool:
    """
    Valida que un SRID sea válido.
    
    Args:
        srid: SRID a validar
    
    Returns:
        True si es válido
    """
    try:
        from django.contrib.gis.gdal import SpatialReference
        sr = SpatialReference(srid)
        return True
    except Exception as e:
        logger.error(f"Invalid SRID {srid}: {e}")
        return False


def get_geometry_type(geom: GEOSGeometry) -> str:
    """
    Obtiene el tipo de geometría normalizado.
    
    Args:
        geom: Geometría
    
    Returns:
        Tipo de geometría en mayúsculas
    """
    geom_type_map = {
        'Point': 'POINT',
        'LineString': 'LINESTRING',
        'Polygon': 'POLYGON',
        'MultiPoint': 'MULTIPOINT',
        'MultiLineString': 'MULTILINESTRING',
        'MultiPolygon': 'MULTIPOLYGON',
        'GeometryCollection': 'GEOMETRYCOLLECTION'
    }
    return geom_type_map.get(geom.geom_type, 'GEOMETRY')


def parse_wfs_capabilities(xml_content: str) -> Dict[str, Any]:
    """
    Parsea XML de WFS GetCapabilities.
    
    Args:
        xml_content: Contenido XML
    
    Returns:
        Dict con información de capas disponibles
    """
    # TODO: Implementar parser completo de WFS Capabilities
    return {
        'layers': [],
        'version': None,
        'service': 'WFS'
    }


def parse_wms_capabilities(xml_content: str) -> Dict[str, Any]:
    """
    Parsea XML de WMS GetCapabilities.
    
    Args:
        xml_content: Contenido XML
    
    Returns:
        Dict con información de capas disponibles
    """
    # TODO: Implementar parser completo de WMS Capabilities
    return {
        'layers': [],
        'version': None,
        'service': 'WMS'
    }


def calculate_feature_statistics(features) -> Dict[str, Any]:
    """
    Calcula estadísticas de un conjunto de features.
    
    Args:
        features: QuerySet de Feature
    
    Returns:
        Dict con estadísticas
    """
    from django.contrib.gis.db.models.functions import Area, Length
    from django.db.models import Count, Sum
    
    stats = {
        'total_count': features.count(),
        'geometry_types': {}
    }
    
    # Contar por tipo de geometría
    geom_types = features.values('geometry').distinct()
    for geom_type in geom_types:
        count = features.filter(geometry=geom_type['geometry']).count()
        stats['geometry_types'][str(geom_type)] = count
    
    return stats


def batch_create_features(layer, features_data: List[Dict[str, Any]], 
                         batch_size: int = 1000, user=None) -> int:
    """
    Crea features en lotes para mejor rendimiento.
    
    Args:
        layer: Layer al que pertenecen los features
        features_data: Lista de dicts con datos de features
        batch_size: Tamaño del lote
        user: Usuario que crea los features
    
    Returns:
        Cantidad de features creados
    """
    from .models import Feature
    
    features = []
    created_count = 0
    
    for data in features_data:
        try:
            geom = validate_geometry(data.get('geometry'))
            if geom:
                features.append(Feature(
                    layer=layer,
                    geometry=geom,
                    properties=data.get('properties', {}),
                    feature_id=data.get('feature_id'),
                    created_by=user
                ))
                
                if len(features) >= batch_size:
                    Feature.objects.bulk_create(features)
                    created_count += len(features)
                    features = []
        except Exception as e:
            logger.warning(f"Error creating feature: {e}")
            continue
    
    if features:
        Feature.objects.bulk_create(features)
        created_count += len(features)
    
    return created_count


def cleanup_expired_exports(days: int = 7):
    """
    Limpia archivos de exportación antiguos.
    
    Args:
        days: Días de antigüedad para considerar expirado
    """
    import os
    from datetime import datetime, timedelta
    from pathlib import Path
    
    export_dirs = [
        'data/exports/shapefiles',
        'data/exports/geojson'
    ]
    
    threshold = datetime.now() - timedelta(days=days)
    deleted_count = 0
    
    for export_dir in export_dirs:
        if os.path.exists(export_dir):
            for file_path in Path(export_dir).glob('*'):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < threshold:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"Error deleting {file_path}: {e}")
    
    logger.info(f"Cleaned up {deleted_count} expired export files")
    return deleted_count
