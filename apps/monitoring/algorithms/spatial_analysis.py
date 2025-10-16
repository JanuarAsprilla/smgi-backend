"""
SMGI Backend - Spatial Analysis Algorithms
Sistema de Monitoreo Geoespacial Inteligente
Funciones y algoritmos para realizar análisis espacial sobre datos geoespaciales.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from django.contrib.gis.geos import Point, Polygon, LineString, MultiPolygon, fromstr, GeometryCollection
from django.contrib.gis.measure import Area, Distance
from apps.gis_services.clients.arcgis_client import ArcGISClient

logger = logging.getLogger('apps.monitoring.algorithms.spatial_analysis')


def calculate_feature_area(geom_data: Dict[str, Any], srid: int = 4326) -> Optional[Area]:
    """
    Calcula el área de una geometría tipo Polygon o MultiPolygon.
    Transforma a un SRID proyectado para cálculos precisos.

    Args:
        geom_data: Diccionario con la geometría en formato GeoJSON.
        srid: SRID original de la geometría (por defecto WGS84 4326).

    Returns:
        Área en metros cuadrados como objeto Area de Django GIS, o None si no aplica.
    """
    try:
        geom_str = str(geom_data) # Asegurar string para fromstr
        geom = fromstr(geom_str)
        if geom.srid != srid:
             geom.srid = srid

        if geom.geom_type not in ['Polygon', 'MultiPolygon']:
            logger.warning(f"Cannot calculate area for geometry type: {geom.geom_type}")
            return None

        # Transformar a un SRID proyectado para área precisa (e.g., Web Mercator 3857 o un UTM local)
        # Web Mercator tiene distorsiones, pero puede ser suficiente para comparaciones relativas
        # Para alta precisión, usar un UTM específico de la zona.
        projected_srid = 3857 # Web Mercator
        if geom.srid != projected_srid:
            geom.transform(projected_srid)

        area_sq_m = geom.area
        return Area(sq_m=area_sq_m)

    except Exception as e:
        logger.error(f"Error calculating area from geom_data: {e}")
        return None


def calculate_feature_length(geom_data: Dict[str, Any], srid: int = 4326) -> Optional[Distance]:
    """
    Calcula la longitud de una geometría tipo LineString o MultiLineString.
    Transforma a un SRID proyectado para cálculos precisos.

    Args:
        geom_data: Diccionario con la geometría en formato GeoJSON.
        srid: SRID original de la geometría.

    Returns:
        Longitud en metros como objeto Distance de Django GIS, o None si no aplica.
    """
    try:
        geom_str = str(geom_data)
        geom = fromstr(geom_str)
        if geom.srid != srid:
             geom.srid = srid

        if geom.geom_type not in ['LineString', 'MultiLineString']:
            logger.warning(f"Cannot calculate length for geometry type: {geom.geom_type}")
            return None

        projected_srid = 3857
        if geom.srid != projected_srid:
            geom.transform(projected_srid)

        length_m = geom.length
        return Distance(m=length_m)

    except Exception as e:
        logger.error(f"Error calculating length from geom_data: {e}")
        return None


def calculate_centroid(geom_data: Dict[str, Any], output_srid: int = 4326) -> Optional[Dict[str, float]]:
    """
    Calcula el centroide de una geometría.
    Transforma a un SRID de salida (por defecto WGS84 para lat/lon).

    Args:
        geom_data: Diccionario con la geometría en formato GeoJSON.
        output_srid: SRID para las coordenadas de salida (por defecto WGS84 4326).

    Returns:
        Diccionario con coordenadas del centroide {'x': ..., 'y': ...}, o None.
    """
    try:
        geom_str = str(geom_data)
        geom = fromstr(geom_str)

        # Asumir SRID de entrada como el del geom_str o 4326 por defecto si no está especificado
        # Si se pasa geom_str directamente, fromstr intenta inferirlo o usar 4326
        # Si se necesita un SRID específico de entrada, debería pasarse como parámetro

        centroid = geom.centroid
        if centroid.srid != output_srid:
            centroid.transform(output_srid)

        return {'x': centroid.x, 'y': centroid.y}

    except Exception as e:
        logger.error(f"Error calculating centroid from geom_data: {e}")
        return None


def check_intersection(geom1_data: Dict[str, Any], geom2_data: Dict[str, Any], srid: int = 4326) -> bool:
    """
    Verifica si dos geometrías se intersectan.
    Asegura que ambas estén en el mismo SRID antes de la operación.

    Args:
        geom1_data: Primera geometría en formato GeoJSON.
        geom2_data: Segunda geometría en formato GeoJSON.
        srid: SRID para asegurar consistencia.

    Returns:
        True si se intersectan, False en caso contrario.
    """
    try:
        geom1_str = str(geom1_data)
        geom2_str = str(geom2_data)
        geom1 = fromstr(geom1_str)
        geom2 = fromstr(geom2_str)

        if geom1.srid != srid:
             geom1.srid = srid
        if geom2.srid != srid:
             geom2.srid = srid

        # Asegurar que estén en el mismo SRID para la operación
        if geom1.srid != geom2.srid:
            geom2.transform(geom1.srid)

        return geom1.intersects(geom2)

    except Exception as e:
        logger.error(f"Error checking intersection: {e}")
        return False


def calculate_centroid_displacement(centroid1: Dict[str, float], centroid2: Dict[str, float], srid: int = 4326) -> Optional[Distance]:
    """
    Calcula la distancia entre dos centroides representados como {'x': ..., 'y': ...}.
    Asume que las coordenadas están en el SRID especificado (e.g., WGS84).
    Para cálculos precisos en metros, transformar a un SRID proyectado.

    Args:
        centroid1: Diccionario con coordenadas del primer centroide.
        centroid2: Diccionario con coordenadas del segundo centroide.
        srid: SRID de las coordenadas (por defecto WGS84 4326).

    Returns:
        Distancia en metros como objeto Distance, o None si falla.
    """
    try:
        p1 = Point(centroid1['x'], centroid1['y'], srid=srid)
        p2 = Point(centroid2['x'], centroid2['y'], srid=srid)

        # Transformar a un SRID proyectado para cálculo de distancia preciso
        projected_srid = 3857
        if p1.srid != projected_srid:
            p1.transform(projected_srid)
        if p2.srid != projected_srid:
            p2.transform(projected_srid)

        distance_m = p1.distance(p2)
        return Distance(m=distance_m)

    except Exception as e:
        logger.error(f"Error calculating centroid displacement: {e}")
        return None


def buffer_geometry(geom_data: Dict[str, Any], distance_meters: float, srid: int = 4326) -> Optional[Dict[str, Any]]:
    """
    Crea un buffer alrededor de una geometría.
    Transforma a un SRID proyectado donde la unidad es el metro.

    Args:
        geom_data: Diccionario con la geometría en formato GeoJSON.
        distance_meters: Distancia del buffer en metros.
        srid: SRID original de la geometría.

    Returns:
        Nueva geometría con buffer en formato GeoJSON (como string, debe parsearse si es necesario), o None.
    """
    try:
        geom_str = str(geom_data)
        geom = fromstr(geom_str)
        if geom.srid != srid:
             geom.srid = srid

        # Transformar a un SRID proyectado donde la unidad es el metro
        projected_srid = 3857 # Web Mercator
        original_srid = geom.srid
        if original_srid != projected_srid:
            geom.transform(projected_srid)

        buffered_geom = geom.buffer(distance_meters)

        # Transformar de vuelta al SRID original
        if original_srid != projected_srid:
             buffered_geom.transform(original_srid)

        return buffered_geom.json # Devuelve como string JSON
    except Exception as e:
        logger.error(f"Error buffering geometry: {e}")
        return None


def analyze_spatial_pattern(features: List[Dict[str, Any]], analysis_type: str = 'clustering', srid: int = 4326) -> Optional[Dict[str, Any]]:
    """
    Analiza el patrón espacial de un conjunto de features.
    Este es un ejemplo básico. Análisis más complejos (índices de Moran, G de Getis-Ord, etc.)
    requerirían bibliotecas especializadas como PySAL.

    Args:
        features: Lista de features en formato GeoJSON.
        analysis_type: Tipo de análisis ('clustering', 'dispersion', etc.).
        srid: SRID de las geometrías.

    Returns:
        Diccionario con resultados del análisis, o None si falla o no está implementado.
    """
    # NOTA: Esta función es un esqueleto para análisis más avanzados.
    # Requiere bibliotecas externas o implementación compleja.
    if analysis_type == 'clustering':
        # Ejemplo: Calcular distancia promedio entre centroides
        try:
            centroids = []
            for f in features:
                geom = f.get('geometry')
                if geom:
                    centroid = calculate_centroid(geom, output_srid=srid)
                    if centroid:
                         centroids.append(Point(centroid['x'], centroid['y'], srid=srid))

            if len(centroids) < 2:
                logger.info("Not enough features to analyze clustering.")
                return {'analysis_type': analysis_type, 'result': 'insufficient_data'}

            # Calcular distancia promedio entre pares de centroides (muy costoso O(n^2))
            # Solo como ejemplo, no es un análisis robusto de clustering.
            total_distance = 0
            count = 0
            for i in range(len(centroids)):
                for j in range(i + 1, len(centroids)):
                    p1 = centroids[i]
                    p2 = centroids[j]
                    if p1.srid != p2.srid:
                        p2.transform(p1.srid)
                    dist = p1.distance(p2)
                    total_distance += dist
                    count += 1

            avg_distance = total_distance / count if count > 0 else 0
            # Interpretar avg_distance como indicador de agrupamiento (bajo = agrupado, alto = disperso)
            # Esta es una simplificación extrema.
            clustering_score = 1 / (avg_distance + 1) if avg_distance > 0 else float('inf') # Ejemplo burdo

            return {
                'analysis_type': analysis_type,
                'average_centroid_distance': avg_distance,
                'clustering_score_approx': clustering_score,
                'feature_count': len(centroids)
            }
        except Exception as e:
            logger.error(f"Error in basic clustering analysis: {e}")
            return None

    elif analysis_type == 'dispersion':
        # Similar a clustering, pero interpretando la métrica opuesta
        # o usando métricas como el radio de enclaving mínimo.
        pass # Implementación pendiente

    else:
        logger.warning(f"Spatial analysis type '{analysis_type}' not implemented.")
        return None

# --- Opcional: Funciones para operaciones espaciales entre capas ---
# Estas funciones requerirían obtener geometrías completas de las capas, lo cual puede ser costoso.

def overlay_analysis(layer1_features: List[Dict[str, Any]], layer2_features: List[Dict[str, Any]], operation: str = 'intersection', srid: int = 4326) -> List[Dict[str, Any]]:
    """
    Realiza un análisis de superposición (overlay) entre dos conjuntos de features.
    Ej: intersection, union, difference.
    NOTA: Esta operación es costosa y puede requerir bibliotecas como GeoPandas o PostGIS en producción.
    """
    # NOTA: Esta función es un esqueleto conceptual.
    # Operaciones espaciales complejas entre grandes conjuntos de datos
    # normalmente se realizan en la base de datos (PostGIS) o con herramientas especializadas.
    results = []
    operation_map = {
        'intersection': lambda g1, g2: g1.intersection(g2) if g1.intersects(g2) else None,
        'union': lambda g1, g2: g1.union(g2),
        'difference': lambda g1, g2: g1.difference(g2),
    }

    op_func = operation_map.get(operation)
    if not op_func:
        logger.warning(f"Overlay operation '{operation}' not implemented.")
        return results

    try:
        for f1 in layer1_features:
            geom1_data = f1.get('geometry')
            if not geom1_data:
                continue
            geom1_str = str(geom1_data)
            geom1 = fromstr(geom1_str)
            if geom1.srid != srid:
                geom1.srid = srid

            for f2 in layer2_features:
                geom2_data = f2.get('geometry')
                if not geom2_data:
                    continue
                geom2_str = str(geom2_data)
                geom2 = fromstr(geom2_str)
                if geom2.srid != srid:
                    geom2.srid = srid

                result_geom = op_func(geom1, geom2)
                if result_geom and not result_geom.empty:
                    # Convertir resultado a GeoJSON
                    results.append({
                        "type": "Feature",
                        "geometry": result_geom.json,
                        "properties": {**f1.get('properties', {}), **f2.get('properties', {})} # Combinar propiedades
                    })

    except Exception as e:
        logger.error(f"Error in overlay analysis: {e}")
        # Devolver resultados parciales o vacíos dependiendo del manejo de errores deseado

    return results
