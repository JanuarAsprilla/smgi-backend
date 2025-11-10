"""
Geodata app configuration.
"""
from django.apps import AppConfig


class GeodataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.geodata'
    verbose_name = 'Geodata'
    
    def ready(self):
        import apps.geodata.signals
