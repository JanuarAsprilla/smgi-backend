"""
Serializers for export functionality.
"""
from rest_framework import serializers


class ExportRequestSerializer(serializers.Serializer):
    """Serializer para solicitudes de exportación."""
    format = serializers.ChoiceField(
        choices=['shapefile', 'geojson', 'both'],
        default='shapefile',
        help_text="Formato de exportación"
    )
    filename = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Nombre personalizado para el archivo"
    )
    crs = serializers.CharField(
        default='EPSG:4326',
        help_text="Sistema de referencia de coordenadas"
    )


class ExportResponseSerializer(serializers.Serializer):
    """Serializer para respuestas de exportación."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    files = serializers.ListField(
        child=serializers.DictField(),
        help_text="Lista de archivos generados"
    )
    download_urls = serializers.ListField(
        child=serializers.URLField(),
        required=False
    )
