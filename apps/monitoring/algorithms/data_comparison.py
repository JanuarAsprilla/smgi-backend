"""
SMGI Backend - Data Comparison Algorithms
Sistema de Monitoreo Geoespacial Inteligente
Funciones y algoritmos auxiliares para comparar datos de capas espaciales.
Esto puede incluir comparación de esquemas, integridad de datos, similitud,
y otras operaciones de análisis de datos.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from django.contrib.gis.geos import Point, Polygon, LineString, GeometryCollection
from apps.gis_services.clients.arcgis_client import ArcGISClient

logger = logging.getLogger('apps.monitoring.algorithms.data_comparison')


def compare_layer_schemas(schema1: Dict[str, Any], schema2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compara dos esquemas de capa (definiciones de campos) y reporta diferencias.

    Args:
        schema1: Definición de campos de la capa 1 (e.g., layer_info['fields']).
        schema2: Definición de campos de la capa 2 (e.g., layer_info['fields']).

    Returns:
        Diccionario con diferencias encontradas en los campos.
    """
    differences = {
        'added_fields': [],
        'removed_fields': [],
        'modified_fields': [],
        'unchanged_fields': []
    }

    fields1 = {f['name']: f for f in schema1.get('fields', [])}
    fields2 = {f['name']: f for f in schema2.get('fields', [])}

    all_field_names = set(fields1.keys()) | set(fields2.keys())

    for name in all_field_names:
        field1 = fields1.get(name)
        field2 = fields2.get(name)

        if field1 is None:
            differences['added_fields'].append(field2)
        elif field2 is None:
            differences['removed_fields'].append(field1)
        elif field1 != field2:
            differences['modified_fields'].append({
                'field_name': name,
                'previous': field1,
                'current': field2
            })
        else:
            differences['unchanged_fields'].append(name)

    return differences


def compare_feature_counts(count1: int, count2: int, threshold: float = 0.05) -> Tuple[bool, float]:
    """
    Compara conteos de features y determina si la diferencia supera un umbral.

    Args:
        count1: Conteo de features en la capa 1.
        count2: Conteo de features en la capa 2.
        threshold: Umbral de cambio (porcentaje) para considerar significativo.

    Returns:
        Tupla (cambio_significativo: bool, porcentaje_de_cambio: float).
    """
    if count1 == 0 and count2 == 0:
        return False, 0.0

    old_count = count1 or 1  # Evitar división por cero, asumiendo 1 si count1 es 0
    change_amount = count2 - count1
    change_percentage = (change_amount / old_count) * 100

    is_significant = abs(change_percentage) >= (threshold * 100)

    return is_significant, change_percentage


def calculate_geometric_similarity(geom1: Dict[str, Any], geom2: Dict[str, Any], method: str = 'area_overlap') -> Optional[float]:
    """
    Calcula una medida de similitud geométrica entre dos geometrías representadas como GeoJSON.
    Este es un ejemplo simple basado en el área de intersección sobre la unión (IoU).
    Otros métodos como distancia Hausdorff o distancia de Fréchet podrían ser más complejos.

    Args:
        geom1: Geometría 1 en formato GeoJSON.
        geom2: Geometría 2 en formato GeoJSON.
        method: Método de cálculo ('area_overlap' por ahora).

    Returns:
        Puntuación de similitud (0.0 a 1.0) o None si no se puede calcular.
    """
    if method != 'area_overlap':
        logger.warning(f"Method {method} not implemented in calculate_geometric_similarity.")
        return None

    try:
        g1 = GeometryCollection([geom1]) if geom1['type'] == 'GeometryCollection' else geom1
        g2 = GeometryCollection([geom2]) if geom2['type'] == 'GeometryCollection' else geom2

        geos_g1 = g1.ogr() # Convertir a objeto GEOS si es necesario
        geos_g2 = g2.ogr()

        if not geos_g1.valid or not geos_g2.valid:
            logger.warning("One or both geometries are invalid for area calculation.")
            return None

        intersection_area = geos_g1.intersection(geos_g2).area
        union_area = geos_g1.union(geos_g2).area

        if union_area == 0:
            return 1.0 if intersection_area == 0 else 0.0 # Ambas vacías o idénticas vacías

        similarity = intersection_area / union_area
        return similarity

    except Exception as e:
        logger.error(f"Error calculating geometric similarity: {e}")
        return None


def validate_data_integrity(features: List[Dict[str, Any]], rules: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Valida la integridad de un conjunto de features contra reglas definidas.
    Las reglas pueden ser simples (e.g., campos requeridos, tipos de datos)
    o más complejas (e.g., reglas de negocio).

    Args:
        features: Lista de features en formato GeoJSON.
        rules: Diccionario con reglas de validación.

    Returns:
        Diccionario con resultados de validación {'passed': [...], 'failed': [...]}.
    """
    results = {'passed': [], 'failed': []}
    validation_errors = []

    for i, feature in enumerate(features):
        feature_errors = []
        geometry = feature.get('geometry')
        properties = feature.get('properties', {})

        # Ejemplo de regla simple: campo requerido
        required_fields = rules.get('required_fields', [])
        for field in required_fields:
            if field not in properties or properties[field] is None:
                feature_errors.append(f"Required field '{field}' is missing or null.")

        # Ejemplo de regla simple: tipo de geometría
        expected_geom_type = rules.get('geometry_type')
        if expected_geom_type and geometry and geometry['type'] != expected_geom_type:
            feature_errors.append(f"Geometry type is '{geometry['type']}', expected '{expected_geom_type}'.")

        # Ejemplo de regla simple: rango numérico
        numeric_range_rules = rules.get('numeric_ranges', {})
        for field_name, range_def in numeric_range_rules.items():
            value = properties.get(field_name)
            if isinstance(value, (int, float)):
                min_val = range_def.get('min')
                max_val = range_def.get('max')
                if (min_val is not None and value < min_val) or (max_val is not None and value > max_val):
                    feature_errors.append(f"Value {value} for field '{field_name}' is out of range [{min_val}, {max_val}].")

        if feature_errors:
            results['failed'].append({
                'feature_index': i,
                'feature_id': feature.get('id', f'index_{i}'),
                'errors': feature_errors
            })
        else:
            results['passed'].append(feature.get('id', f'index_{i}'))

    return results


# --- Opcional: Funciones para comparar datos obtenidos directamente del servicio ---
# Estas funciones requerirían un cliente GIS (como ArcGISClient) para obtener los datos.

def compare_data_checksums(client1: ArcGISClient, layer_id1: int, client2: ArcGISClient, layer_id2: int) -> bool:
    """
    Compara checksums generales de dos capas obtenidas a través de clientes GIS.
    Esto es una forma rápida de ver si *algo* ha cambiado.
    """
    try:
        info1 = client1.get_layer_info(layer_id1)
        info2 = client2.get_layer_info(layer_id2)

        # Suponiendo que get_layer_info puede proporcionar un checksum o un hash del estado
        # Si no, se podría calcular uno basado en el resumen (e.g., count, extent, fields)
        checksum1 = info1.get('checksum') or generate_simple_checksum(info1)
        checksum2 = info2.get('checksum') or generate_simple_checksum(info2)

        return checksum1 == checksum2
    except Exception as e:
        logger.error(f"Error comparing data checksums: {e}")
        return False

def generate_simple_checksum(layer_info: Dict[str, Any]) -> str:
    """
    Genera un checksum simple basado en información clave del layer_info.
    """
    import hashlib
    import json
    data_for_hash = {
        'count': layer_info.get('count'),
        'extent': layer_info.get('extent'),
        'fields': layer_info.get('fields', []),
        'geometryType': layer_info.get('geometryType')
    }
    return hashlib.sha256(json.dumps(data_for_hash, sort_keys=True).encode()).hexdigest()

