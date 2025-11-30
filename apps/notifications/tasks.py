"""
Celery tasks for Notifications app.
"""
from celery import shared_task
from django.contrib.auth import get_user_model
from .services import notification_service
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def send_notification_email(user_id, subject, message):
    """
    Send email notification.
    
    Args:
        user_id: User ID
        subject: Email subject
        message: Email message
    """
    try:
        user = User.objects.get(id=user_id)
        
        from .services import EmailService
        success = EmailService.send_email(
            subject=subject,
            message=message,
            recipient_list=[user.email]
        )
        
        if success:
            logger.info(f"Email sent to user {user.username}")
            return {'status': 'success', 'user_id': user_id}
        else:
            logger.error(f"Failed to send email to user {user.username}")
            return {'status': 'failed', 'user_id': user_id}
            
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'status': 'failed', 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def send_notification_sms(user_id, message):
    """
    Send SMS notification.
    
    Args:
        user_id: User ID
        message: SMS message
    """
    try:
        user = User.objects.get(id=user_id)
        
        if not user.profile.phone:
            logger.warning(f"User {user.username} has no phone number")
            return {'status': 'skipped', 'reason': 'No phone number'}
        
        from .services import SMSService
        sms_service = SMSService()
        success = sms_service.send_sms(user.profile.phone, message)
        
        if success:
            logger.info(f"SMS sent to user {user.username}")
            return {'status': 'success', 'user_id': user_id}
        else:
            logger.error(f"Failed to send SMS to user {user.username}")
            return {'status': 'failed', 'user_id': user_id}
            
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'status': 'failed', 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def notify_analysis_complete(user_id, analysis_id):
    """Notify user that analysis is complete."""
    try:
        user = User.objects.get(id=user_id)
        from apps.agents.models import AgentExecution
        analysis = AgentExecution.objects.get(id=analysis_id)
        
        results = notification_service.notify_analysis_complete(user, analysis)
        
        logger.info(f"Analysis complete notification sent to user {user.username}: {results}")
        return {'status': 'success', 'results': results}
        
    except Exception as e:
        logger.error(f"Error notifying analysis complete: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def notify_analysis_failed(user_id, analysis_id, error_message):
    """Notify user that analysis failed."""
    try:
        user = User.objects.get(id=user_id)
        from apps.agents.models import AgentExecution
        analysis = AgentExecution.objects.get(id=analysis_id)
        
        results = notification_service.notify_analysis_failed(user, analysis, error_message)
        
        logger.info(f"Analysis failed notification sent to user {user.username}: {results}")
        return {'status': 'success', 'results': results}
        
    except Exception as e:
        logger.error(f"Error notifying analysis failed: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def notify_alert(user_id, alert_id):
    """Notify user about an alert."""
    try:
        user = User.objects.get(id=user_id)
        from apps.alerts.models import Alert
        alert = Alert.objects.get(id=alert_id)
        
        results = notification_service.notify_alert(user, alert)
        
        logger.info(f"Alert notification sent to user {user.username}: {results}")
        return {'status': 'success', 'results': results}
        
    except Exception as e:
        logger.error(f"Error notifying alert: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def cleanup_old_notifications(days=30):
    """
    Delete old read notifications.
    
    Args:
        days: Days to keep notifications
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Notification
    
    threshold = timezone.now() - timedelta(days=days)
    
    deleted_count = Notification.objects.filter(
        is_read=True,
        read_at__lt=threshold
    ).delete()[0]
    
    logger.info(f"Deleted {deleted_count} old notifications")
    return f"Deleted {deleted_count} notifications"
