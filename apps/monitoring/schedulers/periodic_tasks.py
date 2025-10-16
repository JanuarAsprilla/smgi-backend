"""
SMGI Backend - Periodic Tasks Configuration for Celery Beat
Sistema de Monitoreo Geoespacial Inteligente
Configuración de tareas programadas para monitoreo y mantenimiento
"""

# NOTA: Este archivo define la configuración de tareas periódicas para Celery Beat.
# La forma estándar de cargar esta configuración es a través de la configuración de Celery en settings.py
# o usando un sender (signal) para cargarla dinámicamente.
# Este archivo define un diccionario que puede ser referenciado desde settings.py.

from celery.schedules import crontab, timedelta

# Definir el diccionario de tareas periódicas
PERIODIC_TASKS = {
    # Tarea principal de monitoreo
    'monitor-all-active-layers': {
        'task': 'apps.monitoring.tasks.monitor_all_active_layers', # Ruta completa a la tarea
        'schedule': timedelta(minutes=15), # Ejecutar cada 15 minutos
        # 'schedule': crontab(minute='*/15'), # Alternativa con cron
        'options': {
            'expires': 900, # Expira la tarea si no se ejecuta en 15 minutos (900 seg)
            'queue': 'monitoring', # Cola específica para tareas de monitoreo (opcional)
        }
    },

    # Verificación de salud del sistema
    'system-health-check': {
        'task': 'apps.monitoring.tasks.system_health_check',
        'schedule': timedelta(minutes=5), # Ejecutar cada 5 minutos
        # 'schedule': crontab(minute='*/5'),
        'options': {
            'expires': 300, # Expira en 5 minutos
            'queue': 'health', # Cola específica para tareas de salud (opcional)
        }
    },

    # Ejecución de verificaciones de calidad de datos
    'run-data-quality-checks': {
        'task': 'apps.monitoring.tasks.run_data_quality_checks',
        'schedule': timedelta(hours=24), # Ejecutar una vez al día
        # 'schedule': crontab(hour=2, minute=0), # Alternativa: a las 2 AM
        'options': {
            'expires': 86400, # Expira en 24 horas
            'queue': 'quality', # Cola específica para tareas de calidad (opcional)
        }
    },

    # Limpieza de snapshots antiguos
    'cleanup-old-snapshots': {
        'task': 'apps.monitoring.tasks.cleanup_old_snapshots',
        'schedule': crontab(hour=3, minute=0), # Ejecutar a las 3 AM
        'options': {
            'expires': 86400, # Expira en 24 horas
            'queue': 'maintenance', # Cola específica para tareas de mantenimiento (opcional)
        }
    },

    # Tarea de ejemplo para procesar un job específico si es necesario
    # 'process-specific-job': {
    #     'task': 'apps.monitoring.tasks.process_monitoring_job',
    #     'schedule': timedelta(hours=1), # Ejecutar cada hora
    #     # Se necesita pasar argumentos específicos, lo cual es más complejo con BEAT
    #     # Se podría usar un wrapper o una tarea intermedia que obtenga los jobs pendientes
    #     # 'args': (job_id,), # No es directo con múltiples jobs
    #     'options': {
    #         'expires': 3600, # Expira en 1 hora
    #     }
    # },
}

# Opcional: Función para cargar las tareas si se usa un sender
# def load_periodic_tasks(sender, **kwargs):
#     """
#     Función para cargar tareas periódicas dinámicamente en Celery Beat.
#     Debe ser conectada a la señal 'beat_init' o 'celery_app' en settings o app config.
#     """
#     from kombu import Queue
#     sender.add_defaults(PERIODIC_TASKS)
#     # Opcional: Definir colas personalizadas aquí también si no están en settings
#     # sender.conf.task_routes = {...} # Para enrutar tareas a colas específicas
#     # sender.conf.task_default_queue = 'default' # Cola por defecto
#     print("Periodic tasks loaded from schedulers.periodic_tasks")