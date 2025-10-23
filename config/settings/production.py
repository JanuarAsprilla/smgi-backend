# config/settings/production.py
"""
SMGI Backend - Production Settings
Sistema de Monitoreo Geoespacial Inteligente
Configuración específica para el entorno de producción
"""
import os
from pathlib import Path
from decouple import config

# --- MEJORA: Heredar todas las configuraciones de base.py ---
from .base import *

# --- MEJORA: Sobrescribir configuraciones específicas de producción ---

# SECURITY WARNING: keep the secret key used in production secret!
# En producción, SECRET_KEY es OBLIGATORIO y debe cargarse desde una variable de entorno.
# NO debe tener un valor por defecto.
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# ALLOWED_HOSTS must be set in production
# Load from environment variable, comma-separated
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# Database
# Load production database credentials from environment variables
DATABASES['default'].update({
    'NAME': config('DB_NAME_PROD'),
    'USER': config('DB_USER_PROD'),
    'PASSWORD': config('DB_PASSWORD_PROD'),
    'HOST': config('DB_HOST_PROD'),
    'PORT': config('DB_PORT_PROD'),
})

# Cache
# Load production Redis URL from environment variable
CACHES['default']['LOCATION'] = config('REDIS_URL_PROD')
CACHES['session']['LOCATION'] = config('REDIS_URL_PROD_SESSION')

# Celery
# Load production broker and result backend URLs from environment variables
CELERY_BROKER_URL = config('CELERY_BROKER_URL_PROD')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND_PROD')

# Email
# Load production SMTP settings from environment variables
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST_PROD')
EMAIL_PORT = config('EMAIL_PORT_PROD', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS_PROD', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER_PROD')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD_PROD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL_PROD')

# Static and Media files
# Ensure absolute paths for serving with Nginx/Apache
STATIC_ROOT = BASE_DIR / 'staticfiles_prod'
MEDIA_ROOT = BASE_DIR / 'media_prod'

# Security
# Activate all security settings for production
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000 # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

# CORS
# Load production CORS origins from environment variable
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS_PROD', cast=Csv())

# Logging
# Configure logging to write to files in production
LOGGING['handlers']['file']['filename'] = BASE_DIR / 'logs_prod' / 'django.log'
LOGGING['handlers']['error_file']['filename'] = BASE_DIR / 'logs_prod' / 'errors.log'
LOGGING['handlers']['audit_file']['filename'] = BASE_DIR / 'logs_prod' / 'audit.log'

# Ensure log directory exists
LOG_DIR_PROD = BASE_DIR / 'logs_prod'
LOG_DIR_PROD.mkdir(exist_ok=True)

# REST Framework
# Ensure strict throttling and permissions in production
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour', # Stricter for anonymous users
    'user': '1000/hour', # Reasonable for authenticated users
    'login': '5/hour', # Stricter login attempts
    'password_reset': '3/hour', # Stricter password reset requests
}
