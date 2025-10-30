# apps/common/validators.py
"""
SMGI Backend - Common Validators
Sistema de Monitoreo Geoespacial Inteligente
Validadores personalizados reutilizables para el backend
"""
import re
import uuid
from typing import Optional, Dict, Any, Union
from django.core.validators import RegexValidator, ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError


def validate_email_format(email: str) -> None:
    """
    Valida el formato de una dirección de correo electrónico.
    
    Args:
        email (str): Dirección de correo electrónico a validar.
        
    Raises:
        ValidationError: Si el formato del correo electrónico es inválido.
    """
    try:
        from django.core.validators import validate_email
        validate_email(email)
    except DjangoValidationError as e:
        raise ValidationError(_('Invalid email format')) from e


def validate_phone_number(phone_number: str) -> None:
    """
    Valida el formato de un número de teléfono.
    
    Args:
        phone_number (str): Número de teléfono a validar.
        
    Raises:
        ValidationError: Si el formato del número de teléfono es inválido.
    """
    # Expresión regular para números de teléfono internacionales
    phone_regex = re.compile(r'^\+?[1-9]\d{1,14}$') # E.164 format
    
    if not phone_regex.match(phone_number):
        raise ValidationError(_('Invalid phone number format'))


def validate_uuid(uuid_string: str) -> None:
    """
    Valida el formato de un UUID.
    
    Args:
        uuid_string (str): UUID a validar.
        
    Raises:
        ValidationError: Si el formato del UUID es inválido.
    """
    try:
        uuid.UUID(uuid_string)
    except ValueError as e:
        raise ValidationError(_('Invalid UUID format')) from e


def validate_slug(slug: str) -> None:
    """
    Valida el formato de un slug.
    
    Args:
        slug (str): Slug a validar.
        
    Raises:
        ValidationError: Si el formato del slug es inválido.
    """
    slug_regex = re.compile(r'^[a-z0-9_-]+$')
    
    if not slug_regex.match(slug):
        raise ValidationError(_('Invalid slug format'))


def validate_hex_color(hex_color: str) -> None:
    """
    Valida el formato de un color hexadecimal.
    
    Args:
        hex_color (str): Color hexadecimal a validar.
        
    Raises:
        ValidationError: Si el formato del color hexadecimal es inválido.
    """
    hex_color_regex = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
    
    if not hex_color_regex.match(hex_color):
        raise ValidationError(_('Invalid hex color format'))


def validate_latitude(latitude: float) -> None:
    """
    Valida el rango de una latitud (-90 a 90).
    
    Args:
        latitude (float): Latitud a validar.
        
    Raises:
        ValidationError: Si el valor de la latitud está fuera del rango.
    """
    if not -90 <= latitude <= 90:
        raise ValidationError(_('Latitude must be between -90 and 90'))


def validate_longitude(longitude: float) -> None:
    """
    Valida el rango de una longitud (-180 a 180).
    
    Args:
        longitude (float): Longitud a validar.
        
    Raises:
        ValidationError: Si el valor de la longitud está fuera del rango.
    """
    if not -180 <= longitude <= 180:
        raise ValidationError(_('Longitude must be between -180 and 180'))


def validate_coordinates(coordinates: Tuple[float, float]) -> None:
    """
    Valida un par de coordenadas (lat, lon).
    
    Args:
        coordinates (Tuple[float, float]): Coordenadas a validar.
        
    Raises:
        ValidationError: Si el formato o valores de las coordenadas son inválidos.
    """
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
        raise ValidationError(_('Coordinates must be a list or tuple of two floats (lat, lon)'))
    
    lat, lon = coordinates
    validate_latitude(lat)
    validate_longitude(lon)


def validate_geometry_type(geometry_type: str) -> None:
    """
    Valida el tipo de geometría (Point, LineString, Polygon, etc.).
    
    Args:
        geometry_type (str): Tipo de geometría a validar.
        
    Raises:
        ValidationError: Si el tipo de geometría es inválido.
    """
    valid_geometry_types = [
        'Point', 'MultiPoint', 'LineString', 'MultiLineString',
        'Polygon', 'MultiPolygon', 'GeometryCollection'
    ]
    
    if geometry_type not in valid_geometry_types:
        raise ValidationError(_('Invalid geometry type'))


def validate_feature_count(feature_count: int) -> None:
    """
    Valida el conteo de features (números positivos).
    
    Args:
        feature_count (int): Conteo de features a validar.
        
    Raises:
        ValidationError: Si el conteo de features es negativo.
    """
    if feature_count < 0:
        raise ValidationError(_('Feature count cannot be negative'))


def validate_area(area: float) -> None:
    """
    Valida el área (números positivos).
    
    Args:
        area (float): Área a validar.
        
    Raises:
        ValidationError: Si el área es negativa.
    """
    if area < 0:
        raise ValidationError(_('Area cannot be negative'))


def validate_length(length: float) -> None:
    """
    Valida la longitud (números positivos).
    
    Args:
        length (float): Longitud a validar.
        
    Raises:
        ValidationError: Si la longitud es negativa.
    """
    if length < 0:
        raise ValidationError(_('Length cannot be negative'))


def validate_percentage(percentage: float) -> None:
    """
    Valida un porcentaje (0.0 a 100.0).
    
    Args:
        percentage (float): Porcentaje a validar.
        
    Raises:
        ValidationError: Si el porcentaje está fuera del rango.
    """
    if not 0.0 <= percentage <= 100.0:
        raise ValidationError(_('Percentage must be between 0.0 and 100.0'))


def validate_positive_integer(value: int) -> None:
    """
    Valida un número entero positivo.
    
    Args:
        value (int): Número entero a validar.
        
    Raises:
        ValidationError: Si el número entero no es positivo.
    """
    if value <= 0:
        raise ValidationError(_('Value must be positive'))


def validate_positive_float(value: float) -> None:
    """
    Valida un número flotante positivo.
    
    Args:
        value (float): Número flotante a validar.
        
    Raises:
        ValidationError: Si el número flotante no es positivo.
    """
    if value <= 0.0:
        raise ValidationError(_('Value must be positive'))


def validate_non_negative_integer(value: int) -> None:
    """
    Valida un número entero no negativo.
    
    Args:
        value (int): Número entero a validar.
        
    Raises:
        ValidationError: Si el número entero es negativo.
    """
    if value < 0:
        raise ValidationError(_('Value cannot be negative'))


def validate_non_negative_float(value: float) -> None:
    """
    Valida un número flotante no negativo.
    
    Args:
        value (float): Número flotante a validar.
        
    Raises:
        ValidationError: Si el número flotante es negativo.
    """
    if value < 0.0:
        raise ValidationError(_('Value cannot be negative'))


def validate_json(json_string: str) -> None:
    """
    Valida que un string sea JSON válido.
    
    Args:
        json_string (str): String a validar como JSON.
        
    Raises:
        ValidationError: Si el string no es JSON válido.
    """
    try:
        import json
        json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValidationError(_('Invalid JSON string')) from e


def validate_cron_expression(cron_expr: str) -> None:
    """
    Valida una expresión cron.
    
    Args:
        cron_expr (str): Expresión cron a validar.
        
    Raises:
        ValidationError: Si la expresión cron es inválida.
    """
    # Expresión regular básica para una expresión cron válida
    # (no cubre todos los casos, pero es un buen comienzo)
    cron_regex = re.compile(
        r'^(\*|[0-9]+|\*\/[0-9]+|[0-9]+\-?[0-9]*)'
        r'\s+(\*|[0-9]+|\*\/[0-9]+|[0-9]+\-?[0-9]*)'
        r'\s+(\*|[0-9]+|\*\/[0-9]+|[0-9]+\-?[0-9]*)'
        r'\s+(\*|[0-9]+|\*\/[0-9]+|[0-9]+\-?[0-9]*|[A-Za-z]+)'
        r'\s+(\*|[0-9]+|\*\/[0-9]+|[0-9]+\-?[0-9]*|[A-Za-z]+)$'
    )
    
    if not cron_regex.match(cron_expr):
        raise ValidationError(_('Invalid cron expression'))


def validate_url(url: str) -> None:
    """
    Valida una URL.
    
    Args:
        url (str): URL a validar.
        
    Raises:
        ValidationError: Si la URL es inválida.
    """
    try:
        from django.core.validators import URLValidator
        URLValidator()(url)
    except DjangoValidationError as e:
        raise ValidationError(_('Invalid URL')) from e


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> None:
    """
    Valida la extensión de un archivo.
    
    Args:
        filename (str): Nombre del archivo a validar.
        allowed_extensions (List[str]): Lista de extensiones permitidas.
        
    Raises:
        ValidationError: Si la extensión del archivo no está permitida.
    """
    if not filename:
        raise ValidationError(_('Filename is empty'))
    
    ext = filename.split('.')[-1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(_('File extension not allowed'))


def validate_file_size(file_size_bytes: int, max_size_bytes: int) -> None:
    """
    Valida el tamaño de un archivo.
    
    Args:
        file_size_bytes (int): Tamaño del archivo en bytes.
        max_size_bytes (int): Tamaño máximo permitido en bytes.
        
    Raises:
        ValidationError: Si el tamaño del archivo excede el máximo permitido.
    """
    if file_size_bytes > max_size_bytes:
        raise ValidationError(_('File size exceeds limit'))
