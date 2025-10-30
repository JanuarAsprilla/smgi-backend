# config/settings/local.py
"""
SMGI Backend - Local Development Settings
Sistema de Monitoreo Geoespacial Inteligente
Configuración específica para el entorno local de desarrollo individual
"""
import os
from pathlib import Path

# --- MEJORA: Importar todas las configuraciones de desarrollo ---
# Esto asegura que local.py herede todas las configuraciones de development.py
# y solo sobrescriba las que sean específicas del entorno local del desarrollador.
from .development import *

# --- MEJORA: Sobrescribir configuraciones específicas para entorno local ---

# SECURITY WARNING: keep the secret key used in production secret!
# En entorno local, se puede usar una clave fija o generar una aleatoria.
# Es recomendable usar un .env.local para esto.
# SECRET_KEY = 'tu-clave-secreta-local-muy-larga-y-aleatoria-aqui'

# SECURITY WARNING: don't run with debug turned on in production!
# Asegurar que DEBUG esté activo en local
DEBUG = True

# ALLOWED_HOSTS para entorno local
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]'] # IPv6 localhost

# --- MEJORA: Configurar base de datos para entorno local ---
# Sobrescribir DATABASES con credenciales locales
# Asegurarse de que estas credenciales estén en .env.local
# DATABASES['default'].update({
#     'NAME': config('DB_NAME_LOCAL', default='smgi_local_db'),
#     'USER': config('DB_USER_LOCAL', default='smgi_local_user'),
#     'PASSWORD': config('DB_PASSWORD_LOCAL', default='smgi_local_password'),
#     'HOST': config('DB_HOST_LOCAL', default='localhost'),
#     'PORT': config('DB_PORT_LOCAL', default='5432'),
# })

# --- MEJORA: Configurar Celery para entorno local ---
# Sobrescribir CELERY_BROKER_URL y CELERY_RESULT_BACKEND con Redis local
# Asegurarse de que Redis esté corriendo localmente
# CELERY_BROKER_URL = config('CELERY_BROKER_URL_LOCAL', default='redis://localhost:6379/0')
# CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND_LOCAL', default='redis://localhost:6379/0')

# --- MEJORA: Configurar caché para entorno local ---
# Sobrescribir CACHES con Redis local
# Asegurarse de que Redis esté corriendo localmente
# CACHES['default']['LOCATION'] = config('REDIS_URL_LOCAL', default='redis://localhost:6379/1')
# CACHES['session']['LOCATION'] = config('REDIS_URL_LOCAL', default='redis://localhost:6379/2')

# --- MEJORA: Configurar email para entorno local ---
# Opciones:
# 1. Enviar a consola (por defecto en development.py)
# 2. Enviar a archivos (útil para revisar contenido)
# 3. Usar servidor SMTP real (Gmail, etc.)

# Opción 2: Enviar emails a archivos
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = BASE_DIR / 'local_emails' # Directorio para guardar emails

# Opción 3: Usar servidor SMTP real (ej: Gmail)
# Asegurarse de que estas credenciales estén en .env.local
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = config('EMAIL_HOST_LOCAL', default='smtp.gmail.com')
# EMAIL_PORT = config('EMAIL_PORT_LOCAL', default=587, cast=int)
# EMAIL_USE_TLS = config('EMAIL_USE_TLS_LOCAL', default=True, cast=bool)
# EMAIL_HOST_USER = config('EMAIL_HOST_USER_LOCAL', default='')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD_LOCAL', default='')
# DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL_LOCAL', default='youremail@gmail.com')

# --- MEJORA: Configurar directorios para archivos estáticos y de medios en local ---
# Sobrescribir si se usan directorios diferentes en local
# STATICFILES_DIRS = [BASE_DIR / 'static_local']
# MEDIA_ROOT = BASE_DIR / 'media_local'

# --- MEJORA: Configurar logging para entorno local ---
# Sobrescribir LOGGING para mostrar más detalles o escribir en archivos locales
# LOGGING['handlers']['file']['filename'] = BASE_DIR / 'local_logs' / 'django.log'
# LOGGING['handlers']['error_file']['filename'] = BASE_DIR / 'local_logs' / 'errors.log'
# LOGGING['handlers']['audit_file']['filename'] = BASE_DIR / 'local_logs' / 'audit.log'

# --- MEJORA: Configurar CORS para entorno local ---
# Ampliar con más orígenes si es necesario
# CORS_ALLOWED_ORIGINS = config(
#     'CORS_ALLOWED_ORIGINS_LOCAL',
#     default='http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080',
#     cast=Csv()
# )

# --- MEJORA: Configuración adicional específica de local ---
# Por ejemplo, desactivar SSL completamente
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# --- MEJORA: Cargar configuraciones desde .env.local ---
# Es una buena práctica tener un archivo .env.local para sobrescribir configuraciones sensibles
# sin comprometerlas en el repositorio.
# from decouple import Config, RepositoryEnv
# local_env_path = BASE_DIR / '.env.local'
# if local_env_path.exists():
#     local_config = Config(RepositoryEnv(local_env_path))
#     
#     # Cargar SECRET_KEY desde .env.local
#     SECRET_KEY = local_config('SECRET_KEY', default=SECRET_KEY)
#     
#     # Cargar DATABASES desde .env.local
#     DATABASES['default'].update({
#         'NAME': local_config('DB_NAME_LOCAL', default=DATABASES['default']['NAME']),
#         'USER': local_config('DB_USER_LOCAL', default=DATABASES['default']['USER']),
#         'PASSWORD': local_config('DB_PASSWORD_LOCAL', default=DATABASES['default']['PASSWORD']),
#         'HOST': local_config('DB_HOST_LOCAL', default=DATABASES['default']['HOST']),
#         'PORT': local_config('DB_PORT_LOCAL', default=DATABASES['default']['PORT']),
#     })
#     
#     # Cargar CELERY desde .env.local
#     CELERY_BROKER_URL = local_config('CELERY_BROKER_URL_LOCAL', default=CELERY_BROKER_URL)
#     CELERY_RESULT_BACKEND = local_config('CELERY_RESULT_BACKEND_LOCAL', default=CELERY_RESULT_BACKEND)
#     
#     # Cargar CACHES desde .env.local
#     CACHES['default']['LOCATION'] = local_config('REDIS_URL_LOCAL', default=CACHES['default']['LOCATION'])
#     CACHES['session']['LOCATION'] = local_config('REDIS_URL_LOCAL', default=CACHES['session']['LOCATION'])
#     
#     # Cargar EMAIL desde .env.local
#     EMAIL_HOST = local_config('EMAIL_HOST_LOCAL', default=EMAIL_HOST)
#     EMAIL_PORT = local_config('EMAIL_PORT_LOCAL', default=EMAIL_PORT, cast=int)
#     EMAIL_USE_TLS = local_config('EMAIL_USE_TLS_LOCAL', default=EMAIL_USE_TLS, cast=bool)
#     EMAIL_HOST_USER = local_config('EMAIL_HOST_USER_LOCAL', default=EMAIL_HOST_USER)
#     EMAIL_HOST_PASSWORD = local_config('EMAIL_HOST_PASSWORD_LOCAL', default=EMAIL_HOST_PASSWORD)
#     DEFAULT_FROM_EMAIL = local_config('DEFAULT_FROM_EMAIL_LOCAL', default=DEFAULT_FROM_EMAIL)
#     
#     # Cargar CORS desde .env.local
#     CORS_ALLOWED_ORIGINS = local_config(
#         'CORS_ALLOWED_ORIGINS_LOCAL',
#         default=','.join(CORS_ALLOWED_ORIGINS),
#         cast=Csv()
#     )
