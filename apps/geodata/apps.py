"""
Geodata app configuration.
"""
from django.apps import AppConfig


class GeodataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.geodata'
    verbose_name = 'Geodatos'
    
    def ready(self):
        """Importar signals cuando la app está lista."""
        import apps.geodata.signals
        import logging
        logger = logging.getLogger(__name__)
        logger.info('Geodata app initialized')
