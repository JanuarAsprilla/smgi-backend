# config/settings/testing.py
"""
SMGI Backend - Testing Settings
Sistema de Monitoreo Geoespacial Inteligente
Configuración específica para el entorno de pruebas
"""
import os
import tempfile
from pathlib import Path

# --- MEJORA: Heredar todas las configuraciones de base.py ---
from .base import *

# --- MEJORA: Sobrescribir configuraciones específicas de pruebas ---

# SECURITY WARNING: keep the secret key used in production secret!
# Use a fixed secret key for testing
SECRET_KEY = 'django-insecure-testing-key-do-not-use-in-production-!!!'

# SECURITY WARNING: don't run with debug turned on in production!
# Disable debug in testing
DEBUG = False

# Allow all hosts in testing
ALLOWED_HOSTS = ['*']

# Database
# Use an in-memory SQLite database for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite', # SQLite with SpatiaLite
        'NAME': ':memory:',
    }
}

# Cache
# Use local memory cache for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'smgi-test-cache',
    },
    'session': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'smgi-test-session-cache',
    }
}

# Celery
# Execute tasks eagerly in testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# Use a dummy broker/result backend for testing
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Email
# Use locmem email backend to capture emails in memory
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Password hashers
# Use a fast hasher for testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher', # Fast hasher for tests
]

# Logging
# Reduce logging verbosity in testing
LOGGING['handlers']['console']['level'] = 'WARNING'
LOGGING['handlers']['file']['level'] = 'WARNING'
LOGGING['handlers']['error_file']['level'] = 'ERROR'
LOGGING['handlers']['audit_file']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['django.request']['level'] = 'ERROR'
LOGGING['loggers']['apps']['level'] = 'WARNING'
LOGGING['loggers']['audit']['level'] = 'WARNING'
LOGGING['loggers']['celery']['level'] = 'WARNING'

# Static files
# Use default static files storage for testing
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files
# Use a temporary directory for media files in testing
MEDIA_ROOT = tempfile.mkdtemp()

# Session engine
# Use cache-based sessions for testing
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Disable migrations in testing for speed (optional, use with caution)
# MIGRATION_MODULES = {
#     'auth': None,
#     'contenttypes': None,
#     'sessions': None,
#     'gis_services': None,
#     'monitoring': None,
#     'alerts': None,
#     'notifications': None,
#     'reports': None,
#     'audit': None,
#     'authentication': None,
#     'common': None,
# }

# Disable SSL redirects in testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Disable HSTS in testing
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Disable content type sniffing in testing
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False

# Disable X-Frame-Options in testing
X_FRAME_OPTIONS = 'SAMEORIGIN' # Less restrictive for testing

# Disable CORS in testing (handled by test client)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = False

# Disable throttling in testing
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# Use a fast renderer for testing
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]

# Use a fast parser for testing
REST_FRAMEWORK['DEFAULT_PARSER_CLASSES'] = [
    'rest_framework.parsers.JSONParser',
]

# Disable pagination in testing for simpler assertions
REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS'] = None
REST_FRAMEWORK['PAGE_SIZE'] = None

# Disable authentication classes in testing (handled by test client)
# REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = []

# Disable permission classes in testing (handled by test client)
# REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = []

# Disable schema generation in testing
SPECTACULAR_SETTINGS['SERVE_INCLUDE_SCHEMA'] = False

# Disable health checks in testing
HEALTH_CHECK = {
    'DISABLED': True,
}

# Disable system health metrics in testing
SYSTEM_HEALTH_METRICS_ENABLED = False

# Disable notification sending in testing
SEND_NOTIFICATIONS = False

# Disable email sending in testing
SEND_EMAILS = False

# Disable SMS sending in testing
SEND_SMS = False

# Disable push notifications in testing
SEND_PUSH_NOTIFICATIONS = False

# Disable webhook notifications in testing
SEND_WEBHOOK_NOTIFICATIONS = False

# Disable report generation in testing
GENERATE_REPORTS = False

# Disable alert creation in testing
CREATE_ALERTS = False

# Disable monitoring job execution in testing
EXECUTE_MONITORING_JOBS = False

# Disable data quality checks in testing
RUN_DATA_QUALITY_CHECKS = False

# Disable change detection in testing
RUN_CHANGE_DETECTION = False

# Disable spatial analysis in testing
RUN_SPATIAL_ANALYSIS = False

# Disable audit logging in testing
AUDIT_LOGGING_ENABLED = False

# Disable performance logging in testing
PERFORMANCE_LOGGING_ENABLED = False

# Disable security logging in testing
SECURITY_LOGGING_ENABLED = False

# Disable debug logging in testing
DEBUG_LOGGING_ENABLED = False

# Disable info logging in testing
INFO_LOGGING_ENABLED = False

# Disable warning logging in testing
WARNING_LOGGING_ENABLED = False

# Disable error logging in testing
ERROR_LOGGING_ENABLED = False

# Disable critical logging in testing
CRITICAL_LOGGING_ENABLED = False

# Disable all logging in testing
# LOGGING_CONFIG = None

# --- MEJORA: Configuraciones adicionales para pruebas más rápidas y aisladas ---
# Estas configuraciones pueden ayudar a acelerar las pruebas y aislarlas mejor.

# Usar un runner de pruebas paralelo (si se tiene configurado)
# TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Número de workers para pruebas paralelas
# TEST_RUNNER_PARALLEL = 4

# Usar una base de datos temporal en disco en lugar de en memoria (opcional)
# DATABASES['default']['NAME'] = '/tmp/smgi_test_db.sqlite3'

# Usar un directorio temporal para archivos estáticos en pruebas
# STATIC_ROOT = tempfile.mkdtemp()

# Usar un directorio temporal para logs en pruebas
# LOG_DIR = Path(tempfile.mkdtemp()) / 'logs'

# --- FIN MEJORA ---
