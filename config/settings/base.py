"""
Django settings for SMGI project.
Base settings shared across all environments.
"""
from pathlib import Path
from datetime import timedelta
import os

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================
# DETECTAR ENTORNO (PRODUCCIÓN O DESARROLLO)
# =============================================
IS_PRODUCTION = os.environ.get('RAILWAY_ENVIRONMENT') is not None

# =============================================
# CONFIGURACIÓN SEGÚN ENTORNO
# =============================================
if IS_PRODUCTION:
    # === PRODUCCIÓN (Railway) ===
    import dj_database_url
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key-change-me')
    DEBUG = False
    
    ALLOWED_HOSTS = [
        '.railway.app',
        '.up.railway.app',
        'localhost',
        '127.0.0.1',
    ]
    
    # Base de datos desde DATABASE_URL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        DATABASES = {
            'default': dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=600,
                engine='django.db.backends.postgresql',  # Usar PostgreSQL normal primero
            )
        }
    else:
        # Fallback si no hay DATABASE_URL
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'railway',
            }
        }
    
    print("✅ Configuración de PRODUCCIÓN (Railway) cargada")
    
else:
    # === DESARROLLO (Local) ===
    from decouple import config, Csv
    
    SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-not-for-production')
    DEBUG = config('DEBUG', default=True, cast=bool)
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
    
    # Base de datos local con PostGIS
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': config('DB_NAME', default='smgi_db'),
            'USER': config('DB_USER', default='smgi_user'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
    
    print("🔧 Configuración de DESARROLLO cargada")

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Solo agregar GIS si no estamos en producción (Railway no tiene PostGIS)
if not IS_PRODUCTION:
    DJANGO_APPS.append('django.contrib.gis')

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    'django_extensions',
]

LOCAL_APPS = [
    'apps.users',
    'apps.geodata',
    'apps.agents',
    'apps.monitoring',
    'apps.alerts',
    'apps.automation',
    'apps.notifications',
    'apps.core',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # WhiteNoise para archivos estáticos
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Crear directorio static si no existe
STATICFILES_DIRS = []
static_dir = BASE_DIR / 'static'
if static_dir.exists():
    STATICFILES_DIRS.append(static_dir)

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# CORS Settings
if IS_PRODUCTION:
    cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
    CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()
else:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
    ]
CORS_ALLOW_CREDENTIALS = True

# Spectacular Settings (API Documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'SMGI API',
    'DESCRIPTION': 'Sistema de Monitoreo Geoespacial Inteligente - API Documentation',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# Celery Configuration
if IS_PRODUCTION:
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
else:
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@smgi.com')

# SMS/Twilio Configuration (for notifications)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# Frontend URL (for emails and notifications)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# File Management Settings
FILE_STORAGE_TTL = {
    'export': 72,
    'report': 168,
    'analysis': 48,
    'monitoring': 720,
    'temp': 24,
    'backup': None,
}

FILE_LOCK_TIMEOUT = 60

# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-files': {
        'task': 'apps.core.tasks.cleanup_expired_files',
        'schedule': crontab(minute=0),
    },
    'cleanup-orphaned-locks': {
        'task': 'apps.core.tasks.cleanup_orphaned_locks',
        'schedule': crontab(minute=30),
    },
    'generate-storage-report': {
        'task': 'apps.core.tasks.generate_storage_report',
        'schedule': crontab(hour=6, minute=0),
    },
    'process-scheduled-agents': {
        'task': 'apps.agents.tasks.process_scheduled_agents',
        'schedule': crontab(minute='*/1'),
    },
    'update-agent-statistics': {
        'task': 'apps.agents.tasks.update_agent_statistics',
        'schedule': crontab(hour=0, minute=0),
    },
    'calculate-agent-ratings': {
        'task': 'apps.agents.tasks.calculate_agent_ratings',
        'schedule': crontab(minute=0),
    },
    'cleanup-old-executions': {
        'task': 'apps.agents.tasks.cleanup_old_executions',
        'schedule': crontab(hour=2, minute=0),
    },
}

# File upload settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 2  # 2GB
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 2  # 2GB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Celery task limits
CELERY_TASK_TIME_LIMIT = 60 * 60  # 1 hora
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 30  # 30 min soft limit
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Geodata settings
GEODATA_ASYNC_THRESHOLD = 50 * 1024 * 1024  # 50MB
GEODATA_UPLOAD_DIR = BASE_DIR / 'data' / 'uploads'

# Security settings for production
if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True