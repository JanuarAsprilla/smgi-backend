"""
SMGI Backend - Base GIS Client
Sistema de Monitoreo Geoespacial Inteligente
Clase base abstracta para clientes GIS
"""
import abc
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from django.conf import settings


logger = logging.getLogger('apps.gis_services')


class BaseGISClient(abc.ABC):
    """
    Clase base abstracta para clientes de servicios GIS.
    Define la interfaz común que deben implementar los clientes específicos
    como ArcGISClient, GeoServerClient, etc.
    """
    
    def __init__(self, service, timeout: Optional[int] = None):
        """
        Inicializa el cliente base.

        Args:
            service: Instancia del modelo ArcGISService (o similar) que representa el servicio.
            timeout: Tiempo de espera para las solicitudes. Si no se proporciona,
                     se usa el valor del servicio o un predeterminado.
        """
        self.service = service
        self.base_url = service.base_url
        self.timeout = timeout or getattr(service, 'timeout_seconds', 30)
        # Se puede inicializar la sesión aquí si es común, o delegarla a las subclases
        self.session = None # Inicializado por subclases específicas

        # Obtener configuración del servicio si aplica
        self.service_config = None
        if hasattr(service, 'configuration'):
            self.service_config = service.configuration

        logger.debug(f"Initialized BaseGIS client for: {self.base_url}")

    def _get_config_value(self, key: str, default: Any) -> Any:
        """
        Obtiene un valor de configuración del ServiceConfiguration o usa un valor predeterminado.
        """
        if self.service_config:
            return getattr(self.service_config, key, default)
        return default

    def _get_cache_key(self, key_type: str, *args) -> str:
        """
        Genera una clave de caché genérica.
        """
        service_id = self.service.id if self.service else 'generic'
        return f"gis_{service_id}_{key_type}_{'_'.join(str(arg) for arg in args)}"

    # --- Métodos Abstractos ---
    # Estos métodos *deben* ser implementados por las subclases
    
    @abc.abstractmethod
    def get_service_info(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Obtiene información general del servicio.
        Debe ser implementado por la subclase específica.
        """
        pass

    @abc.abstractmethod
    def get_layer_info(self, layer_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Obtiene información sobre una capa específica.
        Debe ser implementado por la subclase específica.
        """
        pass

    @abc.abstractmethod
    def query_layer(self, layer_id: int, where: str = '1=1', out_fields: str = '*', 
                   return_geometry: bool = False, return_count_only: bool = False, 
                   result_offset: int = 0, result_record_count: Optional[int] = None) -> Dict[str, Any]:
        """
        Consulta características de una capa.
        Debe ser implementado por la subclase específica.
        """
        pass

    @abc.abstractmethod
    def get_feature_count(self, layer_id: int, where: str = '1=1') -> int:
        """
        Obtiene el conteo de características de una capa.
        Debe ser implementado por la subclase específica.
        """
        pass

    @abc.abstractmethod
    def get_all_features(self, layer_id: int, where: str = '1=1', out_fields: str = '*', 
                        batch_size: Optional[int] = None):
        """
        Obtiene *todas* las características de una capa, manejando paginación.
        Debe ser implementado por la subclase específica.
        """
        pass

    @abc.abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """
        Prueba la conexión con el servicio.
        Debe ser implementado por la subclase específica.
        """
        pass

    # --- Métodos Comunes Opcionales ---
    # Estos pueden ser sobreescritos o usados directamente por las subclases
    
    def _make_request(self, method: str, url: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Método base para realizar solicitudes HTTP.
        Este método debe ser implementado o sobrescrito por las subclases
        para manejar la lógica específica de cada API (autenticación, errores, etc.).
        """
        # Este método en la base es un placeholder o puede contener lógica común
        # si se configura la sesión aquí.
        # Por ahora, lo dejamos como abstracto también, ya que la lógica
        # de manejo de solicitudes es muy específica de cada cliente.
        raise NotImplementedError("Subclasses must implement _make_request")

    def close(self):
        """
        Cierra la sesión del cliente.
        Las subclases deben implementar la lógica específica si es necesario.
        """
        if self.session:
            self.session.close()
            logger.debug(f"{self.__class__.__name__} session closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
