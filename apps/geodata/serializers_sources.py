"""
Serializers para diferentes fuentes de datos geoespaciales
"""
from rest_framework import serializers
from .models import Layer


class URLLayerSerializer(serializers.Serializer):
    """Subir capa desde URL (WMS, WFS, ArcGIS REST, etc)"""
    
    SERVICE_TYPES = [
        ('wms', 'WMS - Web Map Service'),
        ('wfs', 'WFS - Web Feature Service'),
        ('wmts', 'WMTS - Web Map Tile Service'),
        ('arcgis', 'ArcGIS REST Service'),
        ('geojson', 'GeoJSON URL'),
        ('xyz', 'XYZ Tiles'),
    ]
    
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    service_type = serializers.ChoiceField(choices=SERVICE_TYPES)
    url = serializers.URLField()
    
    # Opcionales
    layers = serializers.CharField(required=False, help_text="Capas a cargar (separadas por coma)")
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    # Parámetros adicionales (JSON)
    parameters = serializers.JSONField(required=False, default=dict)
    
    def validate_url(self, value):
        """Validar que la URL sea accesible"""
        import requests
        try:
            response = requests.head(value, timeout=5)
            if response.status_code >= 400:
                raise serializers.ValidationError("URL no accesible")
        except requests.RequestException:
            raise serializers.ValidationError("No se puede conectar a la URL")
        return value


class ArcGISLayerSerializer(serializers.Serializer):
    """Subir capa desde ArcGIS Online/Enterprise"""
    
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    
    # URL del servicio de ArcGIS
    service_url = serializers.URLField(help_text="URL del Feature Service o Map Service")
    
    # Item ID (alternativa a service_url)
    item_id = serializers.CharField(required=False, help_text="ArcGIS Item ID")
    
    # Layer index dentro del servicio
    layer_index = serializers.IntegerField(default=0)
    
    # Autenticación (si es privado)
    token = serializers.CharField(required=False, allow_blank=True, write_only=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    # Opciones de sincronización
    sync_enabled = serializers.BooleanField(default=False)
    sync_interval = serializers.IntegerField(default=3600, help_text="Intervalo en segundos")
    
    def validate(self, data):
        if not data.get('service_url') and not data.get('item_id'):
            raise serializers.ValidationError(
                "Debes proporcionar service_url o item_id"
            )
        return data


class DatabaseLayerSerializer(serializers.Serializer):
    """Subir capa desde base de datos PostGIS"""
    
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    
    # Conexión a DB
    host = serializers.CharField(max_length=255)
    port = serializers.IntegerField(default=5432)
    database = serializers.CharField(max_length=100)
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=100, write_only=True)
    
    # Schema y tabla
    schema = serializers.CharField(default='public')
    table = serializers.CharField(max_length=100)
    geometry_column = serializers.CharField(default='geom')
    
    # Opciones
    srid = serializers.IntegerField(default=4326)
    query = serializers.CharField(
        required=False, 
        help_text="SQL query opcional para filtrar datos"
    )
    
    def validate(self, data):
        """Validar conexión a base de datos"""
        import psycopg2
        
        try:
            conn = psycopg2.connect(
                host=data['host'],
                port=data['port'],
                database=data['database'],
                user=data['username'],
                password=data['password']
            )
            conn.close()
        except psycopg2.Error as e:
            raise serializers.ValidationError(f"Error de conexión: {str(e)}")
        
        return data


class FileLayerSerializer(serializers.Serializer):
    """Upload de archivo (GeoJSON, Shapefile, KML, GeoPackage)"""
    
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField()
    
    # Opciones de procesamiento
    simplify = serializers.BooleanField(default=False)
    simplify_tolerance = serializers.FloatField(default=0.0001)
    reproject_to = serializers.IntegerField(required=False, help_text="SRID destino")
    
    def validate_file(self, value):
        """Validar tipo de archivo"""
        allowed_extensions = ['.geojson', '.json', '.shp', '.zip', '.kml', '.gpkg']
        filename = value.name.lower()
        
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"Tipo de archivo no soportado. Usa: {', '.join(allowed_extensions)}"
            )
        
        return value
