"""
Agents app configuration.
"""
from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agents'
    verbose_name = 'Agentes'
    
    def ready(self):
        import apps.agents.signals
