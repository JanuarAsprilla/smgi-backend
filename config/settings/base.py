# config/settings/base.py
"""
SMGI Backend - Base Settings
Sistema de Monitoreo Geoespacial Inteligente
Configuración base para todos los ambientes
"""

import os
from pathlib import Path
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from decouple import config, Csv

# ==========================================================
# PATHS Y VARIABLES BASE
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ==========================================================
# SEGURIDAD
# ==========================================================
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-change-this-in-production-!!!'
)

DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ==========================================================
# APLICACIONES
# ==========================================================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
]

THIRD_PARTY_APPS = [
    # REST Framework
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    # API Documentation
    'drf_spectacular',

    # CORS
    'corsheaders',

    # Celery
    'django_celery_beat',
    'django_celery_results',

    # Health Checks
    'health_check',
    'health_check.db',
    'health_check.cache',
    'health_check.storage',

    # Two Factor Auth
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',

    # Extensions
    'django_extensions',
]

LOCAL_APPS = [
    'apps.common',
    'apps.authentication',
    'apps.gis_services',
    'apps.monitoring',
    'apps.alerts',
    'apps.notifications',
    'apps.reports',
    'apps.audit',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ==========================================================
# MIDDLEWARE
# ==========================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',  # 2FA Support
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditMiddleware',  # Custom audit middleware
]

ROOT_URLCONF = 'config.urls'

# ==========================================================
# TEMPLATES
# ==========================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ==========================================================
# BASE DE DATOS
# ==========================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('DB_NAME', default='smgi_db'),
        'USER': config('DB_USER', default='smgi_user'),
        'PASSWORD': config('DB_PASSWORD', default='smgi_password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        # --- MEJORA: Eliminar opciones específicas de MySQL para PostgreSQL ---
        # Las siguientes opciones son específicas de MySQL y no son necesarias para PostgreSQL.
        # Se eliminan para evitar confusiones y posibles errores.
        # 'OPTIONS': {
        #     'charset': 'utf8',
        #     'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        # },
        # --- FIN MEJORA ---
        # Opcional: Añadir opciones específicas de PostgreSQL si se requiere configuración avanzada
        # 'OPTIONS': {
        #     'connect_timeout': 10,
        #     'sslmode': 'require', # Si se usa SSL
        # }
    }
}

# ==========================================================
# CACHE Y SESIONES
# ==========================================================
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            # --- MEJORA: Manejar hiredis de forma segura ---
            # 'PARSER_CLASS': 'redis.connection.HiredisParser', # Requiere 'hiredis' instalado
            # Si se usa hiredis, descomentar la línea anterior.
            # Si no se usa o no está seguro, omitir esta línea.
            # Opcional: Usar try/except para cargarlo condicionalmente
            # try:
            #     import hiredis
            #     'PARSER_CLASS': 'redis.connection.HiredisParser',
            # except ImportError:
            #     pass # No usar hiredis
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'smgi',
        'TIMEOUT': 300,
    },
    'session': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/2'),
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
        'KEY_PREFIX': 'smgi_session',
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'

# ==========================================================
# VALIDACIÓN DE CONTRASEÑAS
# ==========================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'authentication.User'

# ==========================================================
# INTERNACIONALIZACIÓN
# ==========================================================
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('es', _('Spanish')),
    ('en', _('English')),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

# ==========================================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# ==========================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================================
# REST FRAMEWORK
# ==========================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FileUploadParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '10/hour',
        'password_reset': '5/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
}

# ==========================================================
# JWT
# ==========================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'ISSUER': 'smgi-backend',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# ==========================================================
# DOCUMENTACIÓN API (Swagger)
# ==========================================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'SMGI - Sistema de Monitoreo Geoespacial Inteligente',
    'DESCRIPTION': 'API para monitoreo de servicios geoespaciales y detección de cambios',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'name': 'IIAP - Equipo de Desarrollo', 'email': 'desarrollo@iiap.org.co'},
    'LICENSE': {'name': 'Propietario - IIAP'},
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
}

# ==========================================================
# CELERY
# ==========================================================
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 1800
CELERY_TASK_SOFT_TIME_LIMIT = 1500
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ==========================================================
# EMAIL
# ==========================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@iiap.org.co')

# ==========================================================
# LOGGING
# ==========================================================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}', 'style': '{'},
        'simple': {'format': '{levelname} {message}', 'style': '{'},
        'json': {'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}'},
    },
    'handlers': {
        'file': {'level': 'INFO', 'class': 'logging.FileHandler', 'filename': LOG_DIR / 'django.log', 'formatter': 'verbose'},
        'error_file': {'level': 'ERROR', 'class': 'logging.FileHandler', 'filename': LOG_DIR / 'errors.log', 'formatter': 'verbose'},
        'console': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'simple'},
        'audit_file': {'level': 'INFO', 'class': 'logging.FileHandler', 'filename': LOG_DIR / 'audit.log', 'formatter': 'json'},
    },
    'loggers': {
        'django': {'handlers': ['file', 'console'], 'level': 'INFO', 'propagate': True},
        'django.request': {'handlers': ['error_file'], 'level': 'ERROR', 'propagate': False},
        'apps': {'handlers': ['file', 'console'], 'level': 'DEBUG', 'propagate': True},
        'audit': {'handlers': ['audit_file'], 'level': 'INFO', 'propagate': False},
        'celery': {'handlers': ['file', 'console'], 'level': 'INFO', 'propagate': True},
    },
}

# ==========================================================
# SEGURIDAD
# ==========================================================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ==========================================================
# CORS
# ==========================================================
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=Csv()
)

# ==========================================================
# CONFIGURACIONES PERSONALIZADAS
# ==========================================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o644

SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600

CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_USE_SESSIONS = True

# ==========================================================
# SMGI CUSTOM SETTINGS
# ==========================================================
SMGI_SETTINGS = {
    'MAX_MONITORING_LAYERS': config('MAX_MONITORING_LAYERS', default=100, cast=int),
    'MONITORING_INTERVAL_MINUTES': config('MONITORING_INTERVAL_MINUTES', default=15, cast=int),
    'ALERT_RETENTION_DAYS': config('ALERT_RETENTION_DAYS', default=90, cast=int),
    'REPORT_RETENTION_DAYS': config('REPORT_RETENTION_DAYS', default=365, cast=int),
    'MAX_CONCURRENT_MONITORS': config('MAX_CONCURRENT_MONITORS', default=10, cast=int),
    'ARCGIS_REQUEST_TIMEOUT': config('ARCGIS_REQUEST_TIMEOUT', default=30, cast=int),
    'CHANGE_DETECTION_THRESHOLD': config('CHANGE_DETECTION_THRESHOLD', default=0.05, cast=float),
}

ARCGIS_SETTINGS = {
    'DEFAULT_TIMEOUT': SMGI_SETTINGS['ARCGIS_REQUEST_TIMEOUT'],
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 1,
    'USER_AGENT': 'SMGI-Backend/1.0',
    # --- MEJORA: Revisar formatos soportados ---
    # 'SUPPORTED_FORMATS': ['json', 'geojson', 'kml'], # KML no es estándar en ArcGIS REST
    'SUPPORTED_FORMATS': ['json', 'geojson', 'csv', 'shapefile'], # Formatos más comunes
    # --- FIN MEJORA ---
}

HEALTH_CHECK = {
    'DATABASE_TIMEOUT': 10,
    'CACHE_TIMEOUT': 5,
    'REDIS_TIMEOUT': 5,
}

PROMETHEUS_METRICS_PATH = '/metrics/'
OTP_TOTP_ISSUER = 'SMGI - IIAP'
OTP_LOGIN_URL = '/auth/2fa/login/'
