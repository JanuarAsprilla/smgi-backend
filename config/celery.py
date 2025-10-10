import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('smgi')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Celery Beat schedule configuration
app.conf.beat_schedule = {
    # Monitoreo automático de capas cada 15 minutos
    'monitor-all-active-layers': {
        'task': 'monitoring.tasks.monitor_all_active_layers',
        'schedule': crontab(minute='*/15'),
    },
    # Limpieza diaria de snapshots antiguos
    'cleanup-old-snapshots': {
        'task': 'monitoring.tasks.cleanup_old_snapshots',
        'schedule': crontab(hour=2, minute=0),
    },
    # Health check cada 5 minutos
    'system-health-check': {
        'task': 'monitoring.tasks.system_health_check',
        'schedule': crontab(minute='*/5'),
    },
    # Data quality checks cada hora
    'run-data-quality-checks': {
        'task': 'monitoring.tasks.run_data_quality_checks',
        'schedule': crontab(minute=0),
    },
}

app.conf.timezone = 'UTC'
