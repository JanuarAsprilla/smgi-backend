"""
Extensiones personalizadas para drf-spectacular para manejar campos GIS.
"""
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import build_basic_type
from drf_spectacular.types import OpenApiTypes
from rest_framework_gis.fields import GeometryField


class GeometryFieldExtension(OpenApiSerializerFieldExtension):
    """Extensión para campos de geometría de GeoDjango."""
    
    target_class = 'rest_framework_gis.fields.GeometryField'
    
    def map_serializer_field(self, auto_schema, direction):
        """Mapea GeometryField a un schema GeoJSON."""
        return {
            'type': 'object',
            'description': 'GeoJSON geometry object',
            'properties': {
                'type': {
                    'type': 'string',
                    'enum': ['Point', 'LineString', 'Polygon', 'MultiPoint', 
                             'MultiLineString', 'MultiPolygon', 'GeometryCollection'],
                    'description': 'The geometry type'
                },
                'coordinates': {
                    'description': 'Array of coordinates',
                    'oneOf': [
                        {'type': 'array', 'items': {'type': 'number'}},
                        {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}},
                        {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}}},
                    ]
                }
            },
            'required': ['type', 'coordinates'],
            'example': {
                'type': 'Point',
                'coordinates': [-74.0060, 40.7128]
            }
        }


class PostGISGeometryFieldExtension(OpenApiSerializerFieldExtension):
    """Extensión para campos GeometryField de Django."""
    
    target_class = 'django.contrib.gis.db.models.fields.GeometryField'
    
    def map_serializer_field(self, auto_schema, direction):
        """Mapea a GeoJSON."""
        return {
            'type': 'object',
            'description': 'GeoJSON geometry',
            'example': {
                'type': 'Polygon',
                'coordinates': [[[-74.0, 40.7], [-74.0, 40.8], [-73.9, 40.8], [-73.9, 40.7], [-74.0, 40.7]]]
            }
        }


class PointFieldExtension(OpenApiSerializerFieldExtension):
    """Extensión para campos PointField."""
    
    target_class = 'django.contrib.gis.db.models.fields.PointField'
    
    def map_serializer_field(self, auto_schema, direction):
        return {
            'type': 'object',
            'description': 'GeoJSON Point',
            'properties': {
                'type': {'type': 'string', 'enum': ['Point']},
                'coordinates': {
                    'type': 'array',
                    'items': {'type': 'number'},
                    'minItems': 2,
                    'maxItems': 3,
                    'description': '[longitude, latitude, altitude(optional)]'
                }
            },
            'example': {'type': 'Point', 'coordinates': [-74.0060, 40.7128]}
        }


class PolygonFieldExtension(OpenApiSerializerFieldExtension):
    """Extensión para campos PolygonField."""
    
    target_class = 'django.contrib.gis.db.models.fields.PolygonField'
    
    def map_serializer_field(self, auto_schema, direction):
        return {
            'type': 'object',
            'description': 'GeoJSON Polygon',
            'properties': {
                'type': {'type': 'string', 'enum': ['Polygon']},
                'coordinates': {
                    'type': 'array',
                    'items': {
                        'type': 'array',
                        'items': {
                            'type': 'array',
                            'items': {'type': 'number'}
                        }
                    }
                }
            },
            'example': {
                'type': 'Polygon',
                'coordinates': [[[-74.0, 40.7], [-74.0, 40.8], [-73.9, 40.8], [-73.9, 40.7], [-74.0, 40.7]]]
            }
        }


class MultiPolygonFieldExtension(OpenApiSerializerFieldExtension):
    """Extensión para campos MultiPolygonField."""
    
    target_class = 'django.contrib.gis.db.models.fields.MultiPolygonField'
    
    def map_serializer_field(self, auto_schema, direction):
        return {
            'type': 'object',
            'description': 'GeoJSON MultiPolygon',
            'properties': {
                'type': {'type': 'string', 'enum': ['MultiPolygon']},
                'coordinates': {
                    'type': 'array',
                    'items': {
                        'type': 'array',
                        'items': {
                            'type': 'array',
                            'items': {
                                'type': 'array',
                                'items': {'type': 'number'}
                            }
                        }
                    }
                }
            }
        }
