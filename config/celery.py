"""
SMGI Backend - Celery Configuration
Sistema de Monitoreo Geoespacial Inteligente
Configuración profesional para tareas asíncronas
"""
import os
import logging
from celery import Celery
from celery.signals import setup_logging, task_failure, task_success, worker_ready
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Create Celery app
app = Celery('smgi')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule (Tareas Programadas)
app.conf.beat_schedule = {
    # Monitoreo automático cada 15 minutos
    'monitor-spatial-layers': {
        'task': 'apps.monitoring.tasks.monitor_all_active_layers',
        'schedule': 15.0 * 60,  # 15 minutes
        'options': {
            'queue': 'monitoring',
            'routing_key': 'monitoring.layers',
        }
    },
    
    # Limpieza de snapshots antiguos cada día a las 2:00 AM
    'cleanup-old-snapshots': {
        'task': 'apps.monitoring.tasks.cleanup_old_snapshots',
        'schedule': crontab(hour=2, minute=0),
        'options': {
            'queue': 'maintenance',
            'routing_key': 'maintenance.cleanup',
        }
    },
    
    # Generación de reportes diarios a las 6:00 AM
    'generate-daily-reports': {
        'task': 'apps.reports.tasks.generate_daily_summary_report',
        'schedule': crontab(hour=6, minute=0),
        'options': {
            'queue': 'reports',
            'routing_key': 'reports.daily',
        }
    },
    
    # Verificación de salud del sistema cada 5 minutos
    'system-health-check': {
        'task': 'apps.monitoring.tasks.system_health_check',
        'schedule': 5.0 * 60,  # 5 minutes
        'options': {
            'queue': 'health',
            'routing_key': 'health.check',
        }
    },
    
    # Procesamiento de alertas pendientes cada minuto
    'process-pending-alerts': {
        'task': 'apps.alerts.tasks.process_pending_alerts',
        'schedule': 60.0,  # 1 minute
        'options': {
            'queue': 'alerts',
            'routing_key': 'alerts.process',
        }
    },
    
    # Limpieza de tokens JWT blacklisteados cada 24 horas
    'cleanup-blacklisted-tokens': {
        'task': 'apps.authentication.tasks.cleanup_blacklisted_tokens',
        'schedule': crontab(hour=3, minute=0),
        'options': {
            'queue': 'maintenance',
            'routing_key': 'maintenance.tokens',
        }
    },
}

# Task Routes - Definir qué tareas van a qué colas
app.conf.task_routes = {
    # Monitoring tasks
    'apps.monitoring.tasks.*': {'queue': 'monitoring'},
    
    # Alert tasks - Alta prioridad
    'apps.alerts.tasks.*': {'queue': 'alerts'},
    
    # Notification tasks - Alta prioridad
    'apps.notifications.tasks.*': {'queue': 'notifications'},
    
    # Report generation - Baja prioridad
    'apps.reports.tasks.*': {'queue': 'reports'},
    
    # Maintenance tasks - Muy baja prioridad
    'apps.*.tasks.cleanup_*': {'queue': 'maintenance'},
    
    # Authentication tasks
    'apps.authentication.tasks.*': {'queue': 'auth'},
    
    # Health check tasks
    'apps.monitoring.tasks.system_health_check': {'queue': 'health'},
}

# Worker Configuration
app.conf.update(
    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Bogota',
    enable_utc=True,
    
    # Task routing
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'smgi-redis',
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    
    # Retry settings
    task_annotations={
        '*': {
            'rate_limit': '100/m',
            'time_limit': 30 * 60,  # 30 minutes
            'soft_time_limit': 25 * 60,  # 25 minutes
        },
        'apps.monitoring.tasks.monitor_layer': {
            'rate_limit': '10/m',
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        },
        'apps.alerts.tasks.send_alert_notification': {
            'rate_limit': '50/m',
            'retry_policy': {
                'max_retries': 5,
                'interval_start': 1,
                'interval_step': 1,
                'interval_max': 10,
            }
        },
        'apps.notifications.tasks.send_email': {
            'rate_limit': '30/m',
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 5,
                'interval_step': 5,
                'interval_max': 30,
            }
        }
    },
)

# Import crontab for scheduling
from celery.schedules import crontab

# Setup custom logging for Celery
@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery workers"""
    from logging.config import dictConfig
    
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} - {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
            'celery_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(settings.BASE_DIR, 'logs', 'celery.log'),
                'maxBytes': 1024 * 1024 * 50,  # 50 MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
            'celery_error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(settings.BASE_DIR, 'logs', 'celery_errors.log'),
                'maxBytes': 1024 * 1024 * 50,  # 50 MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'celery': {
                'handlers': ['console', 'celery_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'celery.task': {
                'handlers': ['console', 'celery_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'apps': {
                'handlers': ['console', 'celery_file'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    })

# Task success/failure handlers
@task_success.connect
def task_success_handler(sender=None, task_id=None, result=None, **kwargs):
    """Handle successful task completion"""
    logger = logging.getLogger('celery.task')
    logger.info(f'Task {task_id} [{sender}] succeeded: {result}')

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwargs):
    """Handle failed task"""
    logger = logging.getLogger('celery.task')
    logger.error(f'Task {task_id} [{sender}] failed: {exception}', exc_info=einfo)
    
    # Opcional: Enviar notificación de error crítico
    if hasattr(exception, '__class__') and 'Critical' in exception.__class__.__name__:
        from apps.notifications.tasks import send_admin_notification
        send_admin_notification.delay(
            subject=f'Critical Task Failure: {sender}',
            message=f'Task {task_id} failed with critical error: {exception}'
        )

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready event"""
    logger = logging.getLogger('celery')
    logger.info(f'Celery worker {sender.hostname} is ready')

# Custom task base class for common functionality
class SMGITask(app.Task):
    """Base task class with common functionality"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Task failure handler"""
        logger = logging.getLogger('celery.task')
        logger.error(f'Task {self.name} [{task_id}] failed', exc_info=exc)
        
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Task retry handler"""
        logger = logging.getLogger('celery.task')
        logger.warning(f'Task {self.name} [{task_id}] retrying due to: {exc}')
        
    def on_success(self, retval, task_id, args, kwargs):
        """Task success handler"""
        logger = logging.getLogger('celery.task')
        logger.info(f'Task {self.name} [{task_id}] completed successfully')

# Set the custom base task class
app.Task = SMGITask

# Debug task for testing
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
    return 'Celery is working correctly!'