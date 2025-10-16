# apps/gis_services/processors/spatial_processor.py
import logging
from typing import Dict, Any, List, Optional
from django.contrib.gis.geos import GEOSGeometry, Point, LineString, Polygon
from django.contrib.gis.measure import Area, Distance
from apps.gis_services.models import SpatialLayer

logger = logging.getLogger('apps.gis_services')

class SpatialProcessor:
    """
    Clase para realizar operaciones espaciales sobre datos geoespaciales.
    """

    @staticmethod
    def calculate_area(geom_data: Dict[str, Any]) -> Optional[Area]:
        """
        Calcula el área de una geometría tipo Polygon o MultiPolygon.
        Args:
            geom_data: Diccionario con la geometría en formato GeoJSON.
        Returns:
            Área en unidades del SRID, o None si no es un polígono.
        """
        try:
            geom = GEOSGeometry(str(geom_data))
            if geom.geom_type in ['Polygon', 'MultiPolygon']:
                # Asegurar que la geometría esté en un SRID que permita cálculo de área (e.g., metros)
                # Si está en WGS84 (4326), se debe transformar a un SRID proyectado para área precisa
                if geom.srid == 4326: # WGS84
                    geom.transform(3857) # Transformar a Web Mercator (m aprox)
                return Area(sq_m=geom.area)
            else:
                logger.warning(f"Cannot calculate area for geometry type: {geom.geom_type}")
                return None
        except Exception as e:
            logger.error(f"Error calculating area: {e}")
            return None

    @staticmethod
    def calculate_length(geom_data: Dict[str, Any]) -> Optional[Distance]:
        """
        Calcula la longitud de una geometría tipo LineString o MultiLineString.
        Args:
            geom_data: Diccionario con la geometría en formato GeoJSON.
        Returns:
            Longitud en unidades del SRID, o None si no es una línea.
        """
        try:
            geom = GEOSGeometry(str(geom_data))
            if geom.geom_type in ['LineString', 'MultiLineString']:
                # Similar a área, transformar si es necesario
                 if geom.srid == 4326: # WGS84
                    geom.transform(3857) # Transformar a Web Mercator (m aprox)
                return Distance(m=geom.length)
            else:
                logger.warning(f"Cannot calculate length for geometry type: {geom.geom_type}")
                return None
        except Exception as e:
            logger.error(f"Error calculating length: {e}")
            return None

    @staticmethod
    def check_intersection(geom1_data: Dict[str, Any], geom2_data: Dict[str, Any]) -> bool:
        """
        Verifica si dos geometrías se intersectan.
        Args:
            geom1_data: Primera geometría.
            geom2_data: Segunda geometría.
        Returns:
            True si se intersectan, False en caso contrario.
        """
        try:
            geom1 = GEOSGeometry(str(geom1_data))
            geom2 = GEOSGeometry(str(geom2_data))
            # Asegurar que estén en el mismo SRID para la operación
            if geom1.srid != geom2.srid:
                geom2.transform(geom1.srid)
            return geom1.intersects(geom2)
        except Exception as e:
            logger.error(f"Error checking intersection: {e}")
            return False

    @staticmethod
    def calculate_centroid(geom_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Calcula el centroide de una geometría.
        Args:
            geom_data: Diccionario con la geometría en formato GeoJSON.
        Returns:
            Diccionario con coordenadas del centroide {'x': ..., 'y': ...}, o None.
        """
        try:
            geom = GEOSGeometry(str(geom_data))
            centroid = geom.centroid
            # Asegurar que esté en WGS84 para coordenadas geográficas
            if centroid.srid != 4326:
                centroid.transform(4326)
            return {'x': centroid.x, 'y': centroid.y}
        except Exception as e:
            logger.error(f"Error calculating centroid: {e}")
            return None

    @staticmethod
    def buffer_geometry(geom_data: Dict[str, Any], distance_meters: float) -> Optional[Dict[str, Any]]:
        """
        Crea un buffer alrededor de una geometría.
        Args:
            geom_data: Diccionario con la geometría en formato GeoJSON.
            distance_meters: Distancia del buffer en metros.
        Returns:
            Nueva geometría con buffer en formato GeoJSON, o None.
        """
        try:
            geom = GEOSGeometry(str(geom_data))
            # Transformar a un SRID proyectado donde la unidad es el metro
            original_srid = geom.srid
            if original_srid == 4326: # WGS84
                geom.transform(3857) # Web Mercator
            buffered_geom = geom.buffer(distance_meters)
            # Transformar de vuelta al SRID original
            if original_srid != 4326:
                 buffered_geom.transform(original_srid)
            return buffered_geom.json # Devuelve como string JSON, puede parsearse a dict si es necesario
        except Exception as e:
            logger.error(f"Error buffering geometry: {e}")
            return None

    @staticmethod
    def process_layer_features(layer: SpatialLayer, operation: str, **kwargs) -> Any:
        """
        Procesa todas las características de una capa con una operación específica.
        Esta es una función genérica que podría llamar a otras funciones de esta clase.
        Args:
            layer: Instancia de SpatialLayer.
            operation: Nombre de la operación (e.g., 'calculate_total_area').
            **kwargs: Argumentos específicos para la operación.
        Returns:
            Resultado de la operación.
        """
        # Este método requeriría integración con la app 'monitoring' o 'reports'
        # para obtener las características actuales de la capa (LayerSnapshot).
        # Por ahora, es un esqueleto.
        logger.info(f"Processing layer {layer.name} with operation {operation}")
        # Ejemplo: if operation == 'calculate_total_area':
        #    snapshot = layer.get_latest_snapshot()
        #    if snapshot:
        #        total_area = 0
        #        for feature_geom in snapshot.features_geoms: # Asumiendo que snapshot tiene geometrías
        #            area = SpatialProcessor.calculate_area(feature_geom)
        #            if area:
        #                total_area += area.sq_m
        #        return total_area
        # ...
        return f"Operation {operation} on layer {layer.name} is a stub."
