# config/cors.py
"""
SMGI Backend - CORS Configuration
Sistema de Monitoreo Geoespacial Inteligente
Configuración de Cross-Origin Resource Sharing (CORS) para el backend
"""
import os
from django.utils.translation import gettext_lazy as _

# --- MEJORA: Definir configuración de CORS centralizada ---
# Esta configuración puede ser importada en settings.py o usada directamente.

# --- CONFIGURACIÓN BÁSICA ---
# Orígenes permitidos para solicitudes CORS
# En producción, reemplazar con los dominios reales del frontend
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",      # React dev server
    "http://127.0.0.1:3000",      # React dev server (IP)
    "http://localhost:8080",       # Vue dev server
    "http://127.0.0.1:8080",      # Vue dev server (IP)
    "https://smgi-frontend.vercel.app", # Ejemplo de frontend en Vercel
    "https://smgi.iiap.edu.pe",    # Ejemplo de frontend en producción
    # Añadir más orígenes según sea necesario
    # "https://yourdomain.com",
]

# --- CONFIGURACIÓN AVANZADA ---
# Permitir credenciales (cookies, Authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Permitir todos los orígenes (SOLO PARA DESARROLLO, NUNCA EN PRODUCCIÓN)
# CORS_ALLOW_ALL_ORIGINS = True # Comentado por seguridad

# Headers personalizados permitidos en solicitudes CORS
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    # Añadir headers personalizados si se usan en el frontend
    # 'x-custom-header',
]

# Métodos HTTP permitidos en solicitudes CORS
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Headers que se exponen al navegador
CORS_EXPOSE_HEADERS = [
    # 'X-Custom-Header',
]

# Tiempo máximo de cacheo de respuestas preflight (en segundos)
CORS_PREFLIGHT_MAX_AGE = 86400 # 24 horas

# Expresión regular para URLs a las que se aplica CORS
# Por ejemplo, solo aplicar CORS a endpoints de API
CORS_URLS_REGEX = r'^/api/.*$'

# --- CONFIGURACIÓN DINÁMICA (Opcional) ---
# Cargar orígenes desde variables de entorno
# Ejemplo: CORS_ALLOWED_ORIGINS_ENV = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
# CORS_ALLOWED_ORIGINS.extend(CORS_ALLOWED_ORIGINS_ENV)

# --- CONFIGURACIÓN PARA ENTORNOS ESPECÍFICOS ---
# Se puede usar settings.DEBUG para cambiar la configuración
# if settings.DEBUG:
#     CORS_ALLOW_ALL_ORIGINS = True
# else:
#     CORS_ALLOW_ALL_ORIGINS = False

# --- CONFIGURACIÓN COMPLETA EN UN DICCIONARIO ---
# Útil para importar toda la configuración a la vez en settings.py
CORS_CONFIG = {
    'CORS_ALLOWED_ORIGINS': CORS_ALLOWED_ORIGINS,
    'CORS_ALLOWED_ORIGIN_REGEXES': [], # Opcional
    'CORS_ALLOW_CREDENTIALS': CORS_ALLOW_CREDENTIALS,
    'CORS_ALLOW_ALL_ORIGINS': False, # Siempre False por seguridad, se maneja en settings.py
    'CORS_ALLOW_HEADERS': CORS_ALLOW_HEADERS,
    'CORS_ALLOW_METHODS': CORS_ALLOW_METHODS,
    'CORS_EXPOSE_HEADERS': CORS_EXPOSE_HEADERS,
    'CORS_PREFLIGHT_MAX_AGE': CORS_PREFLIGHT_MAX_AGE,
    'CORS_URLS_REGEX': CORS_URLS_REGEX,
}

# --- FUNCIONES DE CONFIGURACIÓN (Opcionales) ---

def get_cors_config() -> dict:
    """
    Devuelve la configuración de CORS.
    Permite lógica dinámica si es necesario.
    
    Returns:
        dict: Diccionario con la configuración de CORS.
    """
    # Aquí se podría añadir lógica para cargar configuración desde
    # variables de entorno, base de datos, o un archivo de configuración externo.
    # Por ahora, devuelve la configuración estática.
    return CORS_CONFIG

def is_cors_origin_allowed(origin: str) -> bool:
    """
    Verifica si un origen específico está permitido según la configuración de CORS.
    
    Args:
        origin (str): El origen a verificar (ej: 'https://smgi.iiap.edu.pe').
        
    Returns:
        bool: True si el origen está permitido, False en caso contrario.
    """
    # Verificar contra la lista de orígenes permitidos
    if origin in CORS_ALLOWED_ORIGINS:
        return True
    
    # Verificar contra expresiones regulares permitidas (si existen)
    import re
    for regex in CORS_CONFIG.get('CORS_ALLOWED_ORIGIN_REGEXES', []):
        if re.match(regex, origin):
            return True
   
    
    return False


