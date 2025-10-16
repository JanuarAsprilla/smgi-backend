# apps/gis_services/clients/geoserver_client.py
import requests
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from django.core.cache import cache
from .base_client import BaseGISClient
from apps.gis_services.models import ArcGISService # Reutiliza el modelo genérico si aplica

logger = logging.getLogger('apps.gis_services')

class GeoServerClient(BaseGISClient):
    """
    Cliente para interactuar con servicios GeoServer WMS/WFS.
    Hereda de BaseGISClient.
    """
    
    def __init__(self, service: ArcGISService, timeout: Optional[int] = None):
        """
        Inicializa el cliente GeoServer.
        Asume que 'service' es un ArcGISService configurado para GeoServer.
        """
        super().__init__(service, timeout)
        # GeoServer usa autenticación básica (usuario/contraseña) o API keys
        # Se asume que están en service.credentials o service.metadata
        self.auth = None
        if self.service.requires_authentication:
            # Intentar obtener credenciales de ServiceCredential
            credentials = getattr(self.service, 'credentials', None)
            if credentials:
                 self.auth = (credentials.username, credentials.password)
            else:
                # O intentar desde metadata del servicio si no hay ServiceCredential
                username = self.service.metadata.get('geoserver_username')
                password = self.service.metadata.get('geoserver_password')
                if username and password:
                    self.auth = (username, password)

    def _make_request(self, method: str, url: str, params: Optional[Dict] = None, 
                      Optional[Dict] = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Realiza una solicitud HTTP específica para GeoServer.
        Maneja autenticación básica y errores comunes de GeoServer.
        """
        # Preparar parámetros
        params = params or {}
        params['f'] = 'json' # Intentar forzar JSON si la API lo soporta

        # Generar clave de caché
        cache_key = self._get_cache_key('request', method, url, str(sorted(params.items())))
        
        # Verificar caché para GET
        if method.upper() == 'GET' and use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"Returning cached response for: {url}")
                return cached_data

        try:
            logger.debug(f"Making {method} request to: {url}")
            response = requests.request(method, url, params=params, data=data, auth=self.auth, timeout=self.timeout)
            response.raise_for_status()

            # GeoServer puede devolver XML o JSON. Asumimos JSON aquí.
            try:
                response_data = response.json()
            except ValueError: # Si no es JSON, podría ser XML o texto plano
                logger.warning(f"Response from {url} is not JSON. Content-Type: {response.headers.get('Content-Type')}")
                # Opcional: manejar XML o texto plano aquí
                # Por ahora, devolvemos un diccionario vacío o un error
                # raise NotImplementedError("GeoServer response parsing for non-JSON formats not implemented yet.")
                # O simplemente devolver el texto
                return {'raw_response': response.text}

            # Cache response if applicable
            if method.upper() == 'GET' and use_cache:
                cache.set(cache_key, response_data, self._get_config_value('cache_duration', 300))

            return response_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during request: {e}")
            raise

    def get_service_info(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Obtiene información general del servicio GeoServer (WMS GetCapabilities).
        """
        # GeoServer WMS GetCapabilities
        wms_url = urljoin(self.base_url, 'wms')
        params = {
            'request': 'GetCapabilities',
            'service': 'WMS',
            'version': '1.3.0'
        }
        try:
            # Nota: GeoServer devuelve XML, no JSON. Este ejemplo asume un parseo posterior.
            # La implementación real necesitaría un parser XML (como xml.etree.ElementTree o lxml).
            response_xml = self._make_request('GET', wms_url, params=params, use_cache=use_cache)
            # Parsear XML aquí para extraer nombre, capas, etc.
            # Por ahora, simulamos una respuesta JSON
            logger.warning("Parsing WMS GetCapabilities XML is not implemented in this stub.")
            return {
                'name': f"GeoServer Service at {self.base_url}",
                'type': 'GeoServer WMS/WFS',
                'layers': [], # Extraído del XML
                'description': 'GeoServer instance',
                'currentVersion': '2.20.x' # O detectado del XML
            }
        except Exception as e:
            logger.error(f"Error getting GeoServer info: {e}")
            raise

    def get_layer_info(self, layer_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Obtiene información sobre una capa específica en GeoServer.
        layer_id aquí se interpreta como el nombre de la capa en GeoServer (e.g., workspace:layername).
        """
        # GeoServer no tiene un endpoint directo tipo /layer_id/info como ArcGIS
        # Se podría usar WFS DescribeFeatureType o WMS GetFeatureInfo para detalles.
        # Este es un ejemplo simplificado.
        wfs_url = urljoin(self.base_url, 'wfs')
        params = {
            'request': 'DescribeFeatureType',
            'service': 'WFS',
            'typeName': layer_id, # layer_id es el nombre de la capa
            'version': '2.0.0'
        }
        try:
            response = self._make_request('GET', wfs_url, params=params, use_cache=use_cache)
            # Parsear XML de DescribeFeatureType
            logger.warning("Parsing WFS DescribeFeatureType XML is not implemented in this stub.")
            return {
                'id': layer_id,
                'name': layer_id,
                'type': 'FeatureType',
                'fields': [], # Extraído del XML
                'geometryType': 'Unknown', # Extraído del XML
            }
        except Exception as e:
            logger.error(f"Error getting layer info for {layer_id}: {e}")
            raise

    def query_layer(self, layer_id: int, where: str = '1=1', out_fields: str = '*', 
                   return_geometry: bool = False, return_count_only: bool = False, 
                   result_offset: int = 0, result_record_count: Optional[int] = None) -> Dict[str, Any]:
        """
        Consulta características de una capa en GeoServer usando WFS GetFeature.
        """
        wfs_url = urljoin(self.base_url, 'wfs')
        params = {
            'request': 'GetFeature',
            'service': 'WFS',
            'typeName': layer_id,
            'version': '2.0.0',
            'outputFormat': 'application/json' # Intentar obtener JSON
        }
        if where != '1=1':
            # La cláusula CQL_FILTER puede ser específica de GeoServer
            params['cql_filter'] = where
        if result_offset > 0:
            params['startIndex'] = result_offset
        if result_record_count:
            params['count'] = result_record_count

        try:
            response = self._make_request('GET', wfs_url, params=params, use_cache=False)
            # Asumiendo respuesta en formato GeoJSON
            features = response.get('features', [])
            return {
                'features': features,
                'count': len(features),
                'exceededTransferLimit': False, # WFS no tiene un límite estándar como ArcGIS
                'geometryType': response.get('geometry_field_type', 'Mixed'), # O determinado del GeoJSON
                'spatialReference': response.get('crs', {}).get('properties', {}).get('name', 'EPSG:4326'), # O del GeoJSON
            }
        except Exception as e:
            logger.error(f"Error querying layer {layer_id}: {e}")
            raise

    def get_feature_count(self, layer_id: int, where: str = '1=1') -> int:
        """
        Obtiene el conteo de características usando WFS GetFeature con resultType=hits.
        """
        wfs_url = urljoin(self.base_url, 'wfs')
        params = {
            'request': 'GetFeature',
            'service': 'WFS',
            'typeName': layer_id,
            'version': '2.0.0',
            'resultType': 'hits', # Solicitar solo el conteo
            'outputFormat': 'application/json'
        }
        if where != '1=1':
            params['cql_filter'] = where

        try:
            response = self._make_request('GET', wfs_url, params=params, use_cache=False)
            # La respuesta debería tener un campo 'numberMatched' o similar
            return response.get('numberMatched', 0) # Ajustar según el formato real de la respuesta
        except Exception as e:
            logger.error(f"Error getting feature count for layer {layer_id}: {e}")
            return 0

    def get_all_features(self, layer_id: int, where: str = '1=1', out_fields: str = '*', 
                        batch_size: Optional[int] = None):
        """
        Obtiene todas las características de una capa, manejando paginación con startIndex/count.
        """
        offset = 0
        batch_size = batch_size or 1000 # Valor por defecto si no se especifica

        while True:
            result = self.query_layer(
                layer_id,
                where=where,
                out_fields=out_fields,
                return_geometry=True,
                result_offset=offset,
                result_record_count=batch_size
            )

            features = result.get('features', [])
            if not features:
                break

            for feature in features:
                yield feature

            # Si el número de features devueltas es menor que batch_size,
            # probablemente llegamos al final.
            if len(features) < batch_size:
                break

            offset += batch_size
            logger.debug(f"Fetched {offset} features so far...")

    def test_connection(self) -> tuple[bool, str]:
        """
        Prueba la conexión a GeoServer obteniendo GetCapabilities.
        """
        try:
            info = self.get_service_info(use_cache=False)
            return (True, f"Successfully connected to GeoServer: {info.get('name', 'Unknown')}")
        except Exception as e:
            return (False, f"GeoServer connection failed: {e}")
