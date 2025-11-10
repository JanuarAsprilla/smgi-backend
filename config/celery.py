"""
Celery configuration for SMGI project.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('smgi')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    # Geodata tasks
    'auto-sync-data-sources': {
        'task': 'apps.geodata.tasks.auto_sync_data_sources',
        'schedule': crontab(minute='*/5'),
    },
    'cleanup-old-sync-logs': {
        'task': 'apps.geodata.tasks.cleanup_old_sync_logs',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Agents tasks
    'process-scheduled-agents': {
        'task': 'apps.agents.tasks.process_scheduled_agents',
        'schedule': crontab(minute='*'),
    },
    'cleanup-old-executions': {
        'task': 'apps.agents.tasks.cleanup_old_executions',
        'schedule': crontab(hour=3, minute=0),
    },
    'update-agent-statistics': {
        'task': 'apps.agents.tasks.update_agent_statistics',
        'schedule': crontab(hour=1, minute=0),
    },
    'calculate-agent-ratings': {
        'task': 'apps.agents.tasks.calculate_agent_ratings',
        'schedule': crontab(minute=0),
    },
    
    # Monitoring tasks
    'process-scheduled-monitors': {
        'task': 'apps.monitoring.tasks.process_scheduled_monitors',
        'schedule': crontab(minute='*'),
    },
    'cleanup-old-detections': {
        'task': 'apps.monitoring.tasks.cleanup_old_detections',
        'schedule': crontab(hour=4, minute=0),
    },
    'update-monitor-statistics': {
        'task': 'apps.monitoring.tasks.update_monitor_statistics',
        'schedule': crontab(hour=5, minute=0),
    },
    'check-critical-detections': {
        'task': 'apps.monitoring.tasks.check_critical_detections',
        'schedule': crontab(minute='*/5'),
    },
    
    # Alerts tasks
    'process-pending-alerts': {
        'task': 'apps.alerts.tasks.process_pending_alerts',
        'schedule': crontab(minute='*'),
    },
    'cleanup-old-alerts': {
        'task': 'apps.alerts.tasks.cleanup_old_alerts',
        'schedule': crontab(hour=6, minute=0),
    },
    
    # Automation tasks
    'process-scheduled-workflows': {
        'task': 'apps.automation.tasks.process_scheduled_workflows',
        'schedule': crontab(minute='*'),
    },
    'cleanup-old-workflow-executions': {
        'task': 'apps.automation.tasks.cleanup_old_executions',
        'schedule': crontab(hour=7, minute=0),
    },
    'update-workflow-statistics': {
        'task': 'apps.automation.tasks.update_workflow_statistics',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Users tasks
    'cleanup-unverified-users': {
        'task': 'apps.users.tasks.cleanup_unverified_users',
        'schedule': crontab(hour=9, minute=0),
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
