"""Services for geodata app."""
from .url_loader import URLLayerLoader
from .arcgis_loader import ArcGISLoader
from .database_loader import DatabaseLoader

__all__ = ['URLLayerLoader', 'ArcGISLoader', 'DatabaseLoader']