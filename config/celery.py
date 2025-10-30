# config/celery.py
"""
SMGI Backend - Celery Configuration
Sistema de Monitoreo Geoespacial Inteligente
Configuración de Celery para el sistema de tareas asíncronas
"""
import os
import logging
from celery import Celery
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# --- MEJORA: Configurar logger ---
logger = logging.getLogger('config.celery')

# --- MEJORA: Establecer DJANGO_SETTINGS_MODULE ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# --- MEJORA: Crear instancia de Celery ---
app = Celery('smgi_backend')

# --- MEJORA: Cargar configuración desde settings.py con namespace CELERY ---
app.config_from_object('django.conf:settings', namespace='CELERY')

# --- MEJORA: Autodescubrir tareas en apps registradas ---
app.autodiscover_tasks()

# --- MEJORA: Configuración adicional recomendada ---
# Estas configuraciones se pueden poner en settings.py también, pero es común
# tenerlas aquí para centralizar la configuración de Celery.

# --- MEJORA: Tarea de ejemplo para debugging ---
@app.task(bind=True)
def debug_task(self):
    """
    Tarea de ejemplo para verificar la conexión y mostrar información de la tarea.
    Útil para debugging.
    """
    logger.info(f'Request: {self.request!r}')
    print(f'Request: {self.request!r}') # También imprimir en stdout
    return {'task_id': self.request.id, 'hostname': self.request.hostname}

# --- MEJORA: Configurar rutas de tareas (task routes) ---
# Esto permite enrutar tareas específicas a colas específicas.
# Se puede hacer aquí o en settings.py. Aquí se muestra cómo hacerlo.
# app.conf.task_routes = {
#     'apps.monitoring.tasks.monitor_layer': {'queue': 'monitoring'},
#     'apps.monitoring.tasks.perform_change_detection': {'queue': 'monitoring'},
#     'apps.monitoring.tasks.check_and_auto_resolve_alerts': {'queue': 'alerts'},
#     'apps.monitoring.tasks.check_and_expire_alerts': {'queue': 'alerts'},
#     'apps.notifications.tasks.send_email_notification': {'queue': 'notifications'},
#     'apps.notifications.tasks.send_alert_notification': {'queue': 'notifications'},
#     'apps.notifications.tasks.send_webhook_notification': {'queue': 'notifications'},
#     'apps.reports.tasks.generate_report': {'queue': 'reports'},
#     'apps.reports.tasks.cleanup_old_reports': {'queue': 'cleanup'},
#     'apps.reports.tasks.system_health_check': {'queue': 'health'},
#     # ... más rutas ...
# }

# --- MEJORA: Configurar serializadores ---
# app.conf.task_serializer = 'json'
# app.conf.result_serializer = 'json'
# app.conf.accept_content = ['json']

# --- MEJORA: Configurar zona horaria ---
# app.conf.timezone = settings.TIME_ZONE
# app.conf.enable_utc = True

# --- MEJORA: Configurar worker prefetch multiplier ---
# app.conf.worker_prefetch_multiplier = 1 # Más seguro, menos memoria
# app.conf.worker_prefetch_multiplier = 4 # Más rápido, más memoria

# --- MEJORA: Configurar task acks late ---
# app.conf.task_acks_late = True # Confirmar tareas después de ejecutarlas

# --- MEJORA: Configurar worker max tasks per child ---
# app.conf.worker_max_tasks_per_child = 1000 # Reiniciar worker después de 1000 tareas

# --- MEJORA: Configurar worker max memory per child ---
# app.conf.worker_max_memory_per_child = 100000 # Reiniciar worker después de 100 MB

# --- MEJORA: Configurar broker connection retry on startup ---
# app.conf.broker_connection_retry_on_startup = True

# --- MEJORA: Configurar result backend ---
# app.conf.result_backend = 'redis://localhost:6379/0' # Ejemplo con Redis
# app.conf.result_backend = 'db+postgresql://user:pass@localhost/dbname' # Ejemplo con PostgreSQL

# --- MEJORA: Configurar beat scheduler ---
# app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler' # Si se usa django-celery-beat

# --- MEJORA: Configurar periodic tasks ---
# Esta configuración se puede hacer aquí o en settings.py.
# Aquí se muestra cómo hacerlo, pero es más común hacerlo en settings.py.
# from celery.schedules import crontab, timedelta
# app.conf.beat_schedule = {
#     'monitor-all-active-layers': {
#         'task': 'apps.monitoring.tasks.monitor_all_active_layers',
#         'schedule': timedelta(minutes=15), # Cada 15 minutos
#     },
#     'check-and-auto-resolve-alerts': {
#         'task': 'apps.alerts.tasks.check_and_auto_resolve_alerts',
#         'schedule': timedelta(minutes=30), # Cada 30 minutos
#     },
#     'check-and-expire-alerts': {
#         'task': 'apps.alerts.tasks.check_and_expire_alerts',
#         'schedule': timedelta(hours=1), # Cada hora
#     },
#     'cleanup-old-snapshots': {
#         'task': 'apps.monitoring.tasks.cleanup_old_snapshots',
#         'schedule': crontab(hour=2, minute=0), # Todos los días a las 2 AM
#     },
#     'system-health-check': {
#         'task': 'apps.monitoring.tasks.system_health_check',
#         'schedule': timedelta(minutes=5), # Cada 5 minutos
#     },
#     'run-data-quality-checks': {
#         'task': 'apps.monitoring.tasks.run_data_quality_checks',
#         'schedule': timedelta(hours=24), # Cada 24 horas
#     },
#     # ... más tareas periódicas ...
# }
