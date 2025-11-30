"""
Core app configuration.
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core System'
    
    def ready(self):
        """
        Inicialización cuando la app está lista.
        Se ejecuta una sola vez cuando Django inicia.
        """
        # Importar signals si existen en el futuro
        # try:
        #     import apps.core.signals
        # except ImportError:
        #     pass
        
        # Verificar directorios necesarios
        self._ensure_directories()
        
        logger.info("Core app initialized")
    
    def _ensure_directories(self):
        """Asegura que los directorios necesarios existan."""
        import os
        from django.conf import settings
        
        directories = [
            os.path.join(settings.BASE_DIR, 'data', 'exports'),
            os.path.join(settings.BASE_DIR, 'data', 'analysis'),
            os.path.join(settings.BASE_DIR, 'media', 'temp'),
            os.path.join(settings.BASE_DIR, 'media', 'uploads'),
            os.path.join(settings.BASE_DIR, 'media', 'processed'),
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
