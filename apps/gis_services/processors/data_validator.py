# apps/gis_services/processors/data_validator.py
import logging
from typing import Dict, Any, List
from django.contrib.gis.geos import GEOSGeometry, Point, LineString, Polygon
from django.core.exceptions import ValidationError
from apps.gis_services.models import SpatialLayer, LayerField

logger = logging.getLogger('apps.gis_services')

class DataValidator:
    """
    Clase para validar datos geoespaciales y atributos antes de procesarlos o guardarlos.
    """

    @staticmethod
    def validate_geometry(geom_data: Dict[str, Any], expected_type: str = None) -> bool:
        """
        Valida una geometría GeoJSON.
        Args:
            geom_data: Diccionario con la geometría en formato GeoJSON.
            expected_type: Tipo esperado (e.g., 'Point', 'Polygon'). Puede ser None.
        Returns:
            True si es válida, False en caso contrario.
        """
        try:
            geom = GEOSGeometry(str(geom_data))
            if expected_type and geom.geom_type.upper() != expected_type.upper():
                logger.error(f"Geometry type mismatch. Expected {expected_type}, got {geom.geom_type}")
                return False
            if not geom.valid:
                logger.error(f"Invalid geometry: {geom.valid_reason}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating geometry: {e}")
            return False

    @staticmethod
    def validate_attributes(attributes: Dict[str, Any], layer: SpatialLayer) -> Dict[str, List[str]]:
        """
        Valida los atributos de una característica contra la definición de campos de la capa.
        Args:
            attributes: Diccionario con los atributos.
            layer: Instancia de SpatialLayer para obtener la definición de campos.
        Returns:
            Diccionario con errores encontrados {field_name: [list_of_errors]}.
        """
        errors = {}
        layer_fields = layer.layer_fields.all() # Obtener campos desde LayerField

        for field in layer_fields:
            attr_name = field.name
            attr_value = attributes.get(attr_name)

            # 1. Verificar nulabilidad
            if not field.is_nullable and attr_value is None:
                errors.setdefault(attr_name, []).append("Value cannot be null.")

            # 2. Verificar tipo de campo (básico)
            if attr_value is not None:
                expected_type = field.field_type.lower()
                actual_type = type(attr_value).__name__.lower()

                # Mapeo simplificado de tipos GIS a tipos Python
                type_mapping = {
                    'esriFieldTypeString': 'str',
                    'esriFieldTypeInteger': 'int',
                    'esriFieldTypeDouble': 'float',
                    'esriFieldTypeDate': 'str', # Asumiendo formato ISO
                    'esriFieldTypeGeometry': 'dict', # GeoJSON es un dict
                    # Añadir más mapeos según sea necesario
                }
                expected_python_type = type_mapping.get(expected_type, expected_type)

                if actual_type != expected_python_type:
                    # Permitir int para double como conversión válida
                    if not (expected_python_type == 'float' and actual_type == 'int'):
                         errors.setdefault(attr_name, []).append(f"Expected type {expected_python_type}, got {actual_type}.")

                # 3. Verificar longitud (para cadenas)
                if expected_type == 'esriFieldTypeString' and field.length:
                    if len(str(attr_value)) > field.length:
                        errors.setdefault(attr_name, []).append(f"Value exceeds maximum length of {field.length}.")

        return errors

    @staticmethod
    def validate_feature(feature: Dict[str, Any], layer: SpatialLayer) -> Dict[str, Any]:
        """
        Valida una característica completa (geometría + atributos).
        Args:
            feature: Diccionario con la característica en formato GeoJSON Feature.
            layer: Instancia de SpatialLayer.
        Returns:
            Diccionario con errores {'geometry': [...], 'attributes': {field: [...]}, 'general': [...]}.
        """
        validation_errors = {'geometry': [], 'attributes': {}, 'general': []}

        # Validar geometría
        geometry = feature.get('geometry')
        if geometry:
            geom_type = layer.geometry_type # Usar el tipo de la capa como referencia
            # Mapeo inverso para comparar con GEOS
             geos_type_map = {
                 'POINT': 'Point', 'MULTIPOINT': 'MultiPoint',
                 'POLYLINE': 'LineString', 'POLYGON': 'Polygon',
                 'ENVELOPE': 'Polygon' # Un envelope es un polígono
             }
             expected_geom_type = geos_type_map.get(geom_type.upper())
             if not DataValidator.validate_geometry(geometry, expected_geom_type):
                 validation_errors['geometry'].append("Invalid geometry.")
        else:
            validation_errors['geometry'].append("Geometry is missing.")

        # Validar atributos
        attributes = feature.get('properties', {})
        attr_errors = DataValidator.validate_attributes(attributes, layer)
        validation_errors['attributes'] = attr_errors

        # Validar ID único si aplica (esto puede ser más complejo)
        # feature_id = feature.get('id')
        # if feature_id is not None:
        #     # Lógica para verificar unicidad de ID si es necesario
        #     pass

        return validation_errors
