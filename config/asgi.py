# config/asgi.py
"""
SMGI Backend - ASGI Configuration
Sistema de Monitoreo Geoespacial Inteligente
Configuración ASGI para servir aplicaciones Django y WebSockets
"""
import os
from django.core.asgi import get_asgi_application

# --- MEJORA: Importar routing de Channels ---
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# --- MEJORA: Importar rutas de WebSockets de la app notifications ---
# Asumimos que se creará apps/notifications/routing.py
from apps.notifications import routing as notifications_routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# --- MEJORA: Obtener la aplicación Django ASGI estándar ---
django_asgi_app = get_asgi_application()

# --- MEJORA: Definir el ProtocolTypeRouter ---
application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": django_asgi_app,

    # WebSocket handler
    "websocket": AllowedHostsOriginValidator(
        SessionMiddlewareStack(
            AuthMiddlewareStack(
                URLRouter(
                    notifications_routing.websocket_urlpatterns
                )
            )
        )
    ),
})
