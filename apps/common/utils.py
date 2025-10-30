# apps/common/utils.py
"""
SMGI Backend - Common Utilities
Sistema de Monitoreo Geoespacial Inteligente
Funciones utilitarias genéricas y reutilizables para todo el backend
"""
import logging
import uuid
import hashlib
import base64
import json
import re
import os
import sys
import time
import datetime
import math
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.cache import cache
from django.contrib.gis.geos import Point, Polygon, LineString, GeometryCollection
from django.contrib.gis.measure import Distance, Area
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q, F, Count, Avg, Sum, Min, Max
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.encoding import smart_str
from django.core.serializers.json import DjangoJSONEncoder

# Importar modelos relacionados (solo si se necesitan en utils)
# from apps.authentication.models import User
# from apps.gis_services.models import ArcGISService, SpatialLayer
# from apps.monitoring.models import MonitoringJob
# from apps.alerts.models import Alert
# from apps.notifications.models import Notification
# from apps.reports.models import Report
# from apps.audit.models import AuditLog

logger = logging.getLogger('apps.common.utils')
User = get_user_model()


# --- MEJORA: Funciones Utilitarias Genéricas ---

def generate_unique_id(prefix: str = "", suffix: str = "") -> str:
    """
    Genera un ID único usando uuid.uuid4().
    
    Args:
        prefix (str): Prefijo para el ID generado.
        suffix (str): Sufijo para el ID generado.
        
    Returns:
        str: ID único generado.
    """
    unique_id = str(uuid.uuid4())
    return f"{prefix}{unique_id}{suffix}"


def calculate_hash(data: Union[str, bytes], algorithm: str = 'sha256') -> str:
    """
    Calcula un hash de un string o bytes usando el algoritmo especificado.
    
    Args:
        data (Union[str, bytes]): Datos a hashear.
        algorithm (str): Algoritmo de hash a usar (sha256, md5, sha1, etc.).
        
    Returns:
        str: Hash calculado en formato hexadecimal.
    """
    try:
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_func = getattr(hashlib, algorithm)
        return hash_func(data).hexdigest()
    except AttributeError:
        logger.error(f"Unsupported hash algorithm: {algorithm}")
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    except Exception as e:
        logger.error(f"Error calculating hash: {e}")
        raise


def calculate_checksum(data: Union[str, bytes]) -> str:
    """
    Calcula un checksum CRC32 de un string o bytes.
    
    Args:
        data (Union[str, bytes]): Datos para calcular el checksum.
        
    Returns:
        str: Checksum calculado en formato hexadecimal.
    """
    try:
        import zlib
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        checksum = zlib.crc32(data) & 0xffffffff # Asegurar valor positivo
        return format(checksum, '08x') # Formato hexadecimal de 8 dígitos
    except Exception as e:
        logger.error(f"Error calculating checksum: {e}")
        raise


def compress_data(data: Union[str, bytes], method: str = 'gzip') -> bytes:
    """
    Comprime datos usando gzip o bz2.
    
    Args:
        data (Union[str, bytes]): Datos a comprimir.
        method (str): Método de compresión (gzip, bz2).
        
    Returns:
        bytes: Datos comprimidos.
    """
    try:
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if method == 'gzip':
            import gzip
            return gzip.compress(data)
        elif method == 'bz2':
            import bz2
            return bz2.compress(data)
        else:
            logger.error(f"Unsupported compression method: {method}")
            raise ValueError(f"Unsupported compression method: {method}")
    except Exception as e:
        logger.error(f"Error compressing data: {e}")
        raise


def decompress_data(data: bytes, method: str = 'gzip') -> bytes:
    """
    Descomprime datos usando gzip o bz2.
    
    Args:
        data (bytes): Datos comprimidos.
        method (str): Método de descompresión (gzip, bz2).
        
    Returns:
        bytes: Datos descomprimidos.
    """
    try:
        if method == 'gzip':
            import gzip
            return gzip.decompress(data)
        elif method == 'bz2':
            import bz2
            return bz2.decompress(data)
        else:
            logger.error(f"Unsupported decompression method: {method}")
            raise ValueError(f"Unsupported decompression method: {method}")
    except Exception as e:
        logger.error(f"Error decompressing data: {e}")
        raise


def encrypt_data(data: Union[str, bytes], key: bytes, method: str = 'aes') -> bytes:
    """
    Encripta datos usando AES (cryptography) o RSA (pycrypto).
    Esta es una implementación básica. Para producción, usar bibliotecas seguras.
    
    Args:
        data (Union[str, bytes]): Datos a encriptar.
        key (bytes): Clave de encriptación.
        method (str): Método de encriptación (aes, rsa).
        
    Returns:
        bytes: Datos encriptados.
    """
    try:
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if method == 'aes':
            # Usar cryptography para AES
            from cryptography.fernet import Fernet
            f = Fernet(key)
            return f.encrypt(data)
        elif method == 'rsa':
            # Usar pycrypto para RSA
            # from Crypto.PublicKey import RSA
            # from Crypto.Cipher import PKCS1_OAEP
            # key = RSA.import_key(key)
            # cipher = PKCS1_OAEP.new(key)
            # return cipher.encrypt(data)
            logger.warning("RSA encryption not implemented in this utility function.")
            raise NotImplementedError("RSA encryption not implemented.")
        else:
            logger.error(f"Unsupported encryption method: {method}")
            raise ValueError(f"Unsupported encryption method: {method}")
    except Exception as e:
        logger.error(f"Error encrypting data: {e}")
        raise


def decrypt_data(data: bytes, key: bytes, method: str = 'aes') -> bytes:
    """
    Desencripta datos usando AES (cryptography) o RSA (pycrypto).
    Esta es una implementación básica. Para producción, usar bibliotecas seguras.
    
    Args:
        data (bytes): Datos encriptados.
        key (bytes): Clave de desencriptación.
        method (str): Método de desencriptación (aes, rsa).
        
    Returns:
        bytes: Datos desencriptados.
    """
    try:
        if method == 'aes':
            # Usar cryptography para AES
            from cryptography.fernet import Fernet
            f = Fernet(key)
            return f.decrypt(data)
        elif method == 'rsa':
            # Usar pycrypto para RSA
            # from Crypto.PublicKey import RSA
            # from Crypto.Cipher import PKCS1_OAEP
            # key = RSA.import_key(key)
            # cipher = PKCS1_OAEP.new(key)
            # return cipher.decrypt(data)
            logger.warning("RSA decryption not implemented in this utility function.")
            raise NotImplementedError("RSA decryption not implemented.")
        else:
            logger.error(f"Unsupported decryption method: {method}")
            raise ValueError(f"Unsupported decryption method: {method}")
    except Exception as e:
        logger.error(f"Error decrypting data: {e}")
        raise


def format_datetime(dt: timezone.datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Formatea una fecha/hora en un formato legible.
    
    Args:
        dt (timezone.datetime): Fecha/hora a formatear.
        format_str (str): Formato de fecha/hora.
        
    Returns:
        str: Fecha/hora formateada.
    """
    if not dt:
        return ""
    return dt.strftime(format_str)


def format_duration(seconds: float, show_ms: bool = False) -> str:
    """
    Formatea una duración en segundos a un formato legible (HH:MM:SS).
    
    Args:
        seconds (float): Duración en segundos.
        show_ms (bool): Mostrar milisegundos.
        
    Returns:
        str: Duración formateada.
    """
    if seconds < 0:
        return "00:00:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000) if show_ms else 0
    
    if show_ms:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """
    Formatea un tamaño de archivo en bytes a un formato legible (KB, MB, GB).
    
    Args:
        size_bytes (int): Tamaño del archivo en bytes.
        
    Returns:
        str: Tamaño del archivo formateado.
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Formatea un porcentaje a un formato legible (XX.XX%).
    
    Args:
        value (float): Valor del porcentaje (0.0 a 1.0).
        decimals (int): Número de decimales a mostrar.
        
    Returns:
        str: Porcentaje formateado.
    """
    return f"{value * 100:.{decimals}f}%"


def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """
    Formatea una cantidad monetaria a un formato legible ($XX.XX).
    
    Args:
        amount (float): Cantidad monetaria.
        currency (str): Código de moneda (USD, EUR, PEN, etc.).
        decimals (int): Número de decimales a mostrar.
        
    Returns:
        str: Cantidad monetaria formateada.
    """
    # Usar locale para formateo de moneda si es necesario
    # import locale
    # locale.setlocale(locale.LC_ALL, '')
    # return locale.currency(amount, symbol=True, grouping=True)
    return f"{currency} {amount:.{decimals}f}"


def format_coordinates(lat: float, lon: float, format_type: str = "dms") -> str:
    """
    Formatea coordenadas geográficas a un formato legible (DD° MM' SS").
    
    Args:
        lat (float): Latitud.
        lon (float): Longitud.
        format_type (str): Tipo de formato (dms, dd, dm).
        
    Returns:
        str: Coordenadas formateadas.
    """
    def decimal_to_dms(decimal_degrees):
        degrees = int(decimal_degrees)
        minutes_float = abs((decimal_degrees - degrees) * 60)
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        return degrees, minutes, seconds

    if format_type == "dms":
        lat_d, lat_m, lat_s = decimal_to_dms(lat)
        lon_d, lon_m, lon_s = decimal_to_dms(lon)
        return f"{lat_d}°{lat_m}'{lat_s:.2f}\"N, {lon_d}°{lon_m}'{lon_s:.2f}\"E"
    elif format_type == "dd":
        return f"{lat:.6f}, {lon:.6f}"
    elif format_type == "dm":
        lat_d, lat_m, _ = decimal_to_dms(lat)
        lon_d, lon_m, _ = decimal_to_dms(lon)
        return f"{lat_d}°{lat_m:.4f}', {lon_d}°{lon_m:.4f}'"
    else:
        logger.warning(f"Unsupported coordinate format: {format_type}")
        return f"{lat}, {lon}"


def format_geometry(geom: Union[Point, Polygon, LineString, GeometryCollection], format_type: str = "wkt") -> str:
    """
    Formatea una geometría a un formato legible (WKT, GeoJSON).
    
    Args:
        geom (Union[Point, Polygon, LineString, GeometryCollection]): Geometría a formatear.
        format_type (str): Tipo de formato (wkt, geojson).
        
    Returns:
        str: Geometría formateada.
    """
    if not geom:
        return ""
    
    if format_type == "wkt":
        return geom.wkt
    elif format_type == "geojson":
        return geom.json
    else:
        logger.warning(f"Unsupported geometry format: {format_type}")
        return geom.wkt # Default to WKT


def format_feature(feature: Dict[str, Any], format_type: str = "simple") -> str:
    """
    Formatea una feature a un formato legible (ID, geometría, atributos).
    
    Args:
        feature (Dict[str, Any]): Feature a formatear.
        format_type (str): Tipo de formato (simple, detailed).
        
    Returns:
        str: Feature formateada.
    """
    if not feature:
        return ""
    
    if format_type == "simple":
        return f"Feature ID: {feature.get('id', 'N/A')}, Geometry: {feature.get('geometry', {}).get('type', 'N/A')}"
    elif format_type == "detailed":
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        return f"Feature ID: {feature.get('id', 'N/A')}\nGeometry: {geom.get('type', 'N/A')}\nProperties: {props}"
    else:
        logger.warning(f"Unsupported feature format: {format_type}")
        return f"Feature ID: {feature.get('id', 'N/A')}"


def format_layer(layer: SpatialLayer, format_type: str = "name") -> str:
    """
    Formatea una capa a un formato legible (nombre, tipo, servicio).
    
    Args:
        layer (SpatialLayer): Capa a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Capa formateada.
    """
    if not layer:
        return ""
    
    if format_type == "name":
        return layer.name
    elif format_type == "full":
        service_name = layer.service.name if layer.service else "N/A"
        return f"{layer.name} ({layer.get_geometry_type_display()}) - Service: {service_name}"
    else:
        logger.warning(f"Unsupported layer format: {format_type}")
        return layer.name


def format_service(service: ArcGISService, format_type: str = "name") -> str:
    """
    Formatea un servicio a un formato legible (nombre, tipo, URL).
    
    Args:
        service (ArcGISService): Servicio a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Servicio formateado.
    """
    if not service:
        return ""
    
    if format_type == "name":
        return service.name
    elif format_type == "full":
        return f"{service.name} ({service.get_service_type_display()}) - URL: {service.base_url}"
    else:
        logger.warning(f"Unsupported service format: {format_type}")
        return service.name


def format_alert(alert: Alert, format_type: str = "title") -> str:
    """
    Formatea una alerta a un formato legible (ID, título, severidad, estado).
    
    Args:
        alert (Alert): Alerta a formatear.
        format_type (str): Tipo de formato (title, full).
        
    Returns:
        str: Alerta formateada.
    """
    if not alert:
        return ""
    
    if format_type == "title":
        return alert.title
    elif format_type == "full":
        return f"[{alert.get_severity_display()}] {alert.title} - Status: {alert.get_status_display()}"
    else:
        logger.warning(f"Unsupported alert format: {format_type}")
        return alert.title


def format_notification(notification: Notification, format_type: str = "title") -> str:
    """
    Formatea una notificación a un formato legible (ID, título, tipo, estado).
    
    Args:
        notification (Notification): Notificación a formatear.
        format_type (str): Tipo de formato (title, full).
        
    Returns:
        str: Notificación formateada.
    """
    if not notification:
        return ""
    
    if format_type == "title":
        return notification.title
    elif format_type == "full":
        return f"{notification.title} - Type: {notification.get_notification_type_display()}, Status: {'Read' if notification.is_read else 'Unread'}"
    else:
        logger.warning(f"Unsupported notification format: {format_type}")
        return notification.title


def format_report(report: Report, format_type: str = "name") -> str:
    """
    Formatea un informe a un formato legible (ID, título, tipo, estado).
    
    Args:
        report (Report): Informe a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Informe formateado.
    """
    if not report:
        return ""
    
    if format_type == "name":
        return report.name
    elif format_type == "full":
        return f"{report.name} ({report.get_report_type_display()}) - Status: {report.get_status_display()}"
    else:
        logger.warning(f"Unsupported report format: {format_type}")
        return report.name


def format_user(user: User, format_type: str = "email") -> str:
    """
    Formatea un usuario a un formato legible (email, nombre, rol).
    
    Args:
        user (User): Usuario a formatear.
        format_type (str): Tipo de formato (email, full).
        
    Returns:
        str: Usuario formateado.
    """
    if not user:
        return ""
    
    if format_type == "email":
        return user.email
    elif format_type == "full":
        full_name = user.get_full_name()
        role = user.get_role_display() if hasattr(user, 'get_role_display') else 'N/A'
        return f"{full_name} ({user.email}) - Role: {role}"
    else:
        logger.warning(f"Unsupported user format: {format_type}")
        return user.email


def format_permission(permission: str, format_type: str = "name") -> str:
    """
    Formatea un permiso a un formato legible (nombre, descripción).
    
    Args:
        permission (str): Permiso a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Permiso formateado.
    """
    # permission es un string, no un objeto Permission
    # Se podría usar django.contrib.auth.models.Permission para obtener descripción
    # pero para simplicidad, solo devolvemos el string
    if not permission:
        return ""
    
    if format_type == "name":
        return permission
    elif format_type == "full":
        # from django.contrib.auth.models import Permission
        # try:
        #     perm_obj = Permission.objects.get(codename=permission.split('.')[-1])
        #     return f"{permission} - {perm_obj.name}"
        # except Permission.DoesNotExist:
        #     return permission
        return permission # Placeholder
    else:
        logger.warning(f"Unsupported permission format: {format_type}")
        return permission


def format_role(role: str, format_type: str = "name") -> str:
    """
    Formatea un rol a un formato legible (nombre, descripción).
    
    Args:
        role (str): Rol a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Rol formateado.
    """
    # role es un string, no un objeto Role
    # Se podría usar apps.authentication.models.UserRole para obtener descripción
    # pero para simplicidad, solo devolvemos el string
    if not role:
        return ""
    
    if format_type == "name":
        return role
    elif format_type == "full":
        # from apps.authentication.models import UserRole
        # try:
        #     role_obj = UserRole.objects.get(name=role)
        #     return f"{role} - {role_obj.description}"
        # except UserRole.DoesNotExist:
        #     return role
        return role # Placeholder
    else:
        logger.warning(f"Unsupported role format: {format_type}")
        return role


def format_group(group: str, format_type: str = "name") -> str:
    """
    Formatea un grupo a un formato legible (nombre, descripción).
    
    Args:
        group (str): Grupo a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Grupo formateado.
    """
    # group es un string, no un objeto Group
    # Se podría usar django.contrib.auth.models.Group para obtener descripción
    # pero para simplicidad, solo devolvemos el string
    if not group:
        return ""
    
    if format_type == "name":
        return group
    elif format_type == "full":
        # from django.contrib.auth.models import Group
        # try:
        #     group_obj = Group.objects.get(name=group)
        #     return f"{group} - {group_obj.name}"
        # except Group.DoesNotExist:
        #     return group
        return group # Placeholder
    else:
        logger.warning(f"Unsupported group format: {format_type}")
        return group


def format_policy(policy: Dict[str, Any], format_type: str = "name") -> str:
    """
    Formatea una política a un formato legible (nombre, descripción, estado).
    
    Args:
        policy (Dict[str, Any]): Política a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Política formateada.
    """
    if not policy:
        return ""
    
    if format_type == "name":
        return policy.get('name', 'N/A')
    elif format_type == "full":
        is_active = policy.get('is_active', False)
        status = "Active" if is_active else "Inactive"
        return f"{policy.get('name', 'N/A')} - Status: {status}"
    else:
        logger.warning(f"Unsupported policy format: {format_type}")
        return policy.get('name', 'N/A')


def format_configuration(config: Dict[str, Any], format_type: str = "name") -> str:
    """
    Formatea una configuración a un formato legible (nombre, descripción, estado).
    
    Args:
        config (Dict[str, Any]): Configuración a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Configuración formateada.
    """
    if not config:
        return ""
    
    if format_type == "name":
        return config.get('name', 'N/A')
    elif format_type == "full":
        is_active = config.get('is_active', False)
        status = "Active" if is_active else "Inactive"
        return f"{config.get('name', 'N/A')} - Status: {status}"
    else:
        logger.warning(f"Unsupported configuration format: {format_type}")
        return config.get('name', 'N/A')


def format_preference(preference: Dict[str, Any], format_type: str = "user") -> str:
    """
    Formatea una preferencia a un formato legible (usuario, canal, estado).
    
    Args:
        preference (Dict[str, Any]): Preferencia a formatear.
        format_type (str): Tipo de formato (user, full).
        
    Returns:
        str: Preferencia formateada.
    """
    if not preference:
        return ""
    
    if format_type == "user":
        return preference.get('user_email', 'N/A')
    elif format_type == "full":
        email_enabled = preference.get('email_enabled', False)
        sms_enabled = preference.get('sms_enabled', False)
        push_enabled = preference.get('push_enabled', False)
        in_app_enabled = preference.get('in_app_enabled', False)
        channels = []
        if email_enabled:
            channels.append("Email")
        if sms_enabled:
            channels.append("SMS")
        if push_enabled:
            channels.append("Push")
        if in_app_enabled:
            channels.append("In-App")
        return f"{preference.get('user_email', 'N/A')} - Channels: {', '.join(channels)}"
    else:
        logger.warning(f"Unsupported preference format: {format_type}")
        return preference.get('user_email', 'N/A')


def format_statistic(statistic: Dict[str, Any], format_type: str = "name") -> str:
    """
    Formatea una estadística a un formato legible (nombre, valor, tipo).
    
    Args:
        statistic (Dict[str, Any]): Estadística a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Estadística formateada.
    """
    if not statistic:
        return ""
    
    if format_type == "name":
        return statistic.get('name', 'N/A')
    elif format_type == "full":
        value = statistic.get('value', 'N/A')
        stat_type = statistic.get('type', 'N/A')
        return f"{statistic.get('name', 'N/A')} - Value: {value}, Type: {stat_type}"
    else:
        logger.warning(f"Unsupported statistic format: {format_type}")
        return statistic.get('name', 'N/A')


def format_metric(metric: Dict[str, Any], format_type: str = "name") -> str:
    """
    Formatea una métrica a un formato legible (nombre, valor, tipo).
    
    Args:
        metric (Dict[str, Any]): Métrica a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Métrica formateada.
    """
    if not metric:
        return ""
    
    if format_type == "name":
        return metric.get('name', 'N/A')
    elif format_type == "full":
        value = metric.get('value', 'N/A')
        metric_type = metric.get('type', 'N/A')
        return f"{metric.get('name', 'N/A')} - Value: {value}, Type: {metric_type}"
    else:
        logger.warning(f"Unsupported metric format: {format_type}")
        return metric.get('name', 'N/A')


def format_trend(trend: Dict[str, Any], format_type: str = "name") -> str:
    """
    Formatea una tendencia a un formato legible (nombre, valor, tipo).
    
    Args:
        trend (Dict[str, Any]): Tendencia a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Tendencia formateada.
    """
    if not trend:
        return ""
    
    if format_type == "name":
        return trend.get('name', 'N/A')
    elif format_type == "full":
        value = trend.get('value', 'N/A')
        trend_type = trend.get('type', 'N/A')
        return f"{trend.get('name', 'N/A')} - Value: {value}, Type: {trend_type}"
    else:
        logger.warning(f"Unsupported trend format: {format_type}")
        return trend.get('name', 'N/A')


def format_analysis(analysis: Dict[str, Any], format_type: str = "name") -> str:
    """
    Formatea un análisis a un formato legible (nombre, valor, tipo).
    
    Args:
        analysis (Dict[str, Any]): Análisis a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Análisis formateado.
    """
    if not analysis:
        return ""
    
    if format_type == "name":
        return analysis.get('name', 'N/A')
    elif format_type == "full":
        value = analysis.get('value', 'N/A')
        analysis_type = analysis.get('type', 'N/A')
        return f"{analysis.get('name', 'N/A')} - Value: {value}, Type: {analysis_type}"
    else:
        logger.warning(f"Unsupported analysis format: {format_type}")
        return analysis.get('name', 'N/A')


def format_prediction(prediction: Dict[str, Any], format_type: str = "name") -> str:
    """
    Formatea una predicción a un formato legible (nombre, valor, tipo).
    
    Args:
        prediction (Dict[str, Any]): Predicción a formatear.
        format_type (str): Tipo de formato (name, full).
        
    Returns:
        str: Predicción formateada.
    """
    if not prediction:
        return ""
    
    if format_type == "name":
        return prediction.get('name', 'N/A')
    elif format_type == "full":
        value = prediction.get('value', 'N/A')
        prediction_type = prediction.get('type', 'N/A')
        return f"{prediction.get('name', 'N/A')} - Value: {value}, Type: {prediction_type}"
    else:
        logger.warning(f"Unsupported prediction format: {format_type}")
        return prediction.get('name', 'N/A')
