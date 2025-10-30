# config/settings/development.py
"""
SMGI Backend - Development Settings
Sistema de Monitoreo Geoespacial Inteligente
Configuración específica para el entorno de desarrollo local
"""
import os
from pathlib import Path
from decouple import config # Para compatibilidad con base.py

# --- MEJORA: Importar todas las configuraciones de base.py ---
# Esto evita duplicación de código y asegura consistencia.
from .base import *

# --- MEJORA: Sobrescribir configuraciones específicas de desarrollo ---

# SECURITY WARNING: keep the secret key used in production secret!
# Generar una clave secreta aleatoria si no está en .env
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-development-key-change-me-in-production-!!!'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# --- MEJORA: Configurar base de datos para desarrollo con PostgreSQL ---
# Asumir que se usa PostgreSQL local en desarrollo.
# En base.py, DATABASES['default']['ENGINE'] ya está configurado para postgis.
# Solo necesitamos sobrescribir NAME, USER, PASSWORD si no están en .env.
DATABASES['default'].update({
    'NAME': config('DB_NAME', default='smgi_dev_db'),
    'USER': config('DB_USER', default='smgi_dev_user'),
    'PASSWORD': config('DB_PASSWORD', default='smgi_dev_password'),
    'HOST': config('DB_HOST', default='localhost'),
    'PORT': config('DB_PORT', default='5432'),
})

# --- MEJORA: Configurar directorios para archivos estáticos y de medios en desarrollo ---
# En base.py ya están definidos STATIC_URL, STATIC_ROOT, STATICFILES_DIRS, MEDIA_URL, MEDIA_ROOT.
# Pero en desarrollo, podemos sobrescribirlos si es necesario.
# Por ejemplo, si se quiere servir archivos estáticos desde un directorio diferente.
# STATICFILES_DIRS = [BASE_DIR / 'static_dev'] # Opcional

# --- MEJORA: Configurar email para desarrollo ---
# Enviar emails a la consola en lugar de un servidor SMTP real.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Opcional: Usar file backend para guardar emails en archivos
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = BASE_DIR / 'emails' # Directorio para guardar emails

# --- MEJORA: Configurar logging para desarrollo ---
# En base.py ya está definido LOGGING.
# Pero en desarrollo, podemos añadir más handlers o cambiar niveles.
# Por ejemplo, añadir un handler para mostrar logs en la consola con más detalle.
# O simplemente asegurarnos de que el logging base funcione.

# --- MEJORA: Configurar cache para desarrollo ---
# En base.py ya está configurado CACHES con Redis.
# En desarrollo, se puede usar un cache locmem para simplicidad si Redis no está disponible.
# Pero es mejor tener Redis en desarrollo también para simular producción.
# Si se quiere usar locmem:
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#         'LOCATION': 'smgi-dev-cache',
#     },
#     'session': {
#         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#         'LOCATION': 'smgi-dev-session-cache',
#     }
# }
# Pero mantener el de base.py es preferible si Redis está disponible.

# --- MEJORA: Configurar Celery para desarrollo ---
# En base.py ya están definidos CELERY_BROKER_URL y CELERY_RESULT_BACKEND.
# En desarrollo, se puede usar Redis local.
# CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
# CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# --- MEJORA: Configurar CORS para desarrollo ---
# En base.py ya está definido CORS_ALLOWED_ORIGINS.
# En desarrollo, se puede ampliar con más orígenes comunes.
# CORS_ALLOWED_ORIGINS = config(
#     'CORS_ALLOWED_ORIGINS',
#     default='http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080',
#     cast=Csv()
# )

# --- MEJORA: Configuraciones específicas de desarrollo adicionales ---
# Por ejemplo, desactivar SSL en desarrollo
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Mostrar toolbar de Django Debug en desarrollo (si está instalado)
# if DEBUG:
#     INSTALLED_APPS += ['debug_toolbar']
#     MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
#     INTERNAL_IPS = ['127.0.0.1']
