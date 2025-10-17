"""
SMGI Backend - Alerts Tasks
Sistema de Monitoreo Geoespacial Inteligente
Tareas asíncronas para el sistema de alertas
"""
import logging
import time
from celery import shared_task
from celery.exceptions import Retry
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from apps.alerts.models import Alert, AlertStatus, AlertAction, AlertActionType
# Importar modelos de otras apps si es necesario
# Nota: Idealmente, las tareas de notificación se manejarían en la app 'notifications'
# pero si 'alerts' inicia el proceso, puede llamar a tareas de 'notifications'.
# from apps.notifications.tasks import send_alert_notification_task

logger = logging.getLogger('apps.alerts')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_alert_notification(self, alert_id):
    """
    Task to process and send notification for an alert.
    This is a placeholder that would typically call a task in the 'notifications' app.
    """
    try:
        logger.info(f"Processing notification for alert ID: {alert_id}")
        alert = Alert.objects.get(id=alert_id)

        # Check if notifications should be suppressed
        if alert.should_suppress_notifications():
            logger.info(f"Suppressing notification for similar alert: {alert.alert_id}")
            return {'suppressed': True, 'alert_id': alert_id}

        # Increment notification count
        alert.increment_notification_count()

        # --- DECISIÓN DE DISEÑO ---
        # Llamar a una tarea de la app 'notifications' para manejar el envío real
        # Esta es una dependencia cruzada. Asegúrate de que la app 'notifications' esté disponible.
        # Si no, esta lógica se movería a la app 'notifications'.
        try:
            from apps.notifications.tasks import send_alert_notification_task
            # Pasar datos relevantes de la alerta
            notification_data = {
                'alert_id': str(alert.id),
                'alert_title': alert.title,
                'alert_description': alert.description,
                'alert_severity': alert.severity,
                'alert_status': alert.status,
                'alert_category': alert.category,
                'service_name': alert.service.name if alert.service else None,
                'layer_name': alert.layer.name if alert.layer else None,
                'affected_features_count': alert.affected_features_count,
                'change_percentage': alert.change_percentage,
                'assigned_to_id': str(alert.assigned_to.id) if alert.assigned_to else None,
                'first_detected': alert.first_detected.isoformat(),
            }
            result = send_alert_notification_task.delay(notification_data)
            logger.info(f"Notification task for alert {alert.alert_id} sent to notifications app.")
            return {'notification_task_sent': True, 'task_id': result.id, 'alert_id': alert_id}

        except ImportError:
            logger.error("Could not import 'send_alert_notification_task' from 'notifications' app.")
            # Opcional: Crear una entrada en una cola de notificaciones pendientes o manejar localmente
            # Si se maneja localmente, aquí iría la lógica para enviar emails, SMS, etc.
            return {'error': 'notifications_app_not_found', 'alert_id': alert_id}
        except Exception as e:
            logger.error(f"Error calling notification task for alert {alert_id}: {e}")
            # Retry con exponential backoff
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    except Alert.DoesNotExist:
        logger.error(f"Alert with ID {alert_id} not found for notification processing.")
        return {'error': 'alert_not_found', 'alert_id': alert_id}
    except Exception as e:
        logger.error(f"Error processing notification for alert {alert_id}: {e}")
        # Retry con exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def check_and_auto_resolve_alerts():
    """
    Task to check for alerts that should be auto-resolved based on their configuration.
    This task should be scheduled periodically via Celery Beat.
    """
    try:
        logger.info("Starting auto-resolve check task")
        now = timezone.now()

        # Get alerts that are eligible for auto-resolve and have passed their auto_resolve_time
        alerts_to_auto_resolve = Alert.objects.filter(
            status__in=[AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED],
            auto_resolve=True,
            auto_resolve_duration__isnull=False,
            first_detected__lt=now - timezone.timedelta(hours=1) # Example filter to limit scope
        ).select_related('resolved_by') # Optimize DB query

        resolved_count = 0
        for alert in alerts_to_auto_resolve:
            if alert.should_auto_resolve:
                # Use the model's method to resolve, which handles status and creates AlertAction
                # Note: Need a user context for 'resolved_by'. Using a system user or the creator might be appropriate.
                # For now, we'll pass None and let the model handle it or use a default system user.
                # A better approach might be to have a 'system_user' defined in settings.
                system_user = getattr(settings, 'SYSTEM_USER_ID', None)
                if system_user:
                    try:
                        from apps.authentication.models import User
                        user = User.objects.get(id=system_user)
                    except (User.DoesNotExist, AttributeError):
                        user = None
                else:
                    user = None

                if alert.resolve(user=user, notes="Auto-resolved by system"):
                    resolved_count += 1
                    logger.info(f"Auto-resolved alert: {alert.alert_id}")

        logger.info(f"Auto-resolve check completed. Resolved {resolved_count} alerts.")
        return {'resolved_count': resolved_count}

    except Exception as e:
        logger.error(f"Error in auto-resolve check task: {e}")
        return {'error': str(e)}


@shared_task
def check_and_expire_alerts():
    """
    Task to check for alerts that have expired based on their 'expires_at' field.
    This task should be scheduled periodically via Celery Beat.
    """
    try:
        logger.info("Starting expire check task")
        now = timezone.now()

        # Get active alerts that have an expires_at in the past
        alerts_to_expire = Alert.objects.filter(
            status=AlertStatus.ACTIVE,
            expires_at__lt=now,
            expires_at__isnull=False
        )

        expired_count = 0
        for alert in alerts_to_expire:
            # Directly update status to expired
            alert.status = AlertStatus.EXPIRED
            alert.save(update_fields=['status'])
            # Create an action log entry
            AlertAction.objects.create(
                alert=alert,
                action_type=AlertActionType.RESOLVED, # Or create a new type 'EXPIRED'?
                notes="Alert expired automatically."
            )
            expired_count += 1
            logger.info(f"Expired alert: {alert.alert_id}")

        logger.info(f"Expire check completed. Expired {expired_count} alerts.")
        return {'expired_count': expired_count}

    except Exception as e:
        logger.error(f"Error in expire check task: {e}")
        return {'error': str(e)}


# --- Opcional: Tarea para evaluar reglas de alerta si se manejan aquí ---
# Si las reglas se evalúan en 'monitoring', esta tarea probablemente no sea necesaria en 'alerts'.
# Pero si se evalúan aquí basadas en otros criterios, podría existir.
# @shared_task
# def evaluate_alert_rules():
#     """
#     Task to evaluate defined alert rules against current data.
#     This might involve querying other models or services.
#     """
#     # Lógica para evaluar reglas y crear Alertas si se cumplen
#     pass
