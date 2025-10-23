# config/wsgi.py
"""
SMGI Backend - WSGI Configuration
Sistema de Monitoreo Geoespacial Inteligente
Configuración WSGI para servir la aplicación Django con servidores como Gunicorn
"""
import os
from django.core.wsgi import get_wsgi_application

# --- MEJORA: Establecer DJANGO_SETTINGS_MODULE ---
# Esto le dice a Django qué archivo de configuración usar.
# Es esencial para que la aplicación WSGI funcione correctamente.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# --- MEJORA: Obtener la aplicación WSGI de Django ---
# Esta es la aplicación WSGI que servirá todas las solicitudes HTTP tradicionales.
# Se usa con servidores como Gunicorn o uWSGI.
application = get_wsgi_application()
