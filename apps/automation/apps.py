"""
Automation app configuration.
"""
from django.apps import AppConfig


class AutomationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.automation'
    verbose_name = 'Automatización'
    
    def ready(self):
        import apps.automation.signals
