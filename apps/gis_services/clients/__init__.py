# apps/gis_services/clients/__init__.py
# Inicialización del paquete de clientes GIS

from .base_client import BaseGISClient
from .arcgis_client import ArcGISClient
# Si se crea geoserver_client, se importaría aquí también
# from .geoserver_client import GeoServerClient

# Opcional: Definir qué se exporta por defecto si se usa 'from .clients import *'
# __all__ = ['BaseGISClient', 'ArcGISClient', 'GeoServerClient']