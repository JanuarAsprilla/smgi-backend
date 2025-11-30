"""
Celery tasks for Alerts app.
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from .models import Alert, AlertLog, AlertChannel, AlertRule
import logging
import requests

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_alert(self, alert_id, resend=False):
    """
    Send an alert through configured channels.
    
    Args:
        alert_id: ID of the Alert
        resend: Whether this is a resend
    """
    try:
        alert = Alert.objects.select_related('rule').prefetch_related(
            'rule__channels', 'rule__recipients'
        ).get(id=alert_id)
        
        logger.info(f"Sending alert: {alert.title}")
        
        if not resend:
            alert.status = 'sent'
        alert.sent_at = timezone.now()
        
        channels = alert.rule.channels.filter(is_enabled=True)
        recipients = alert.rule.recipients.all()
        
        if not channels.exists():
            logger.warning(f"No enabled channels for alert {alert_id}")
            alert.status = 'failed'
            alert.save()
            return {'status': 'failed', 'error': 'No channels configured'}
        
        success_count = 0
        failed_count = 0
        delivery_details = {}
        
        for channel in channels:
            for recipient in recipients:
                try:
                    if channel.channel_type == 'email':
                        result = send_email_alert(alert, channel, recipient)
                    elif channel.channel_type == 'webhook':
                        result = send_webhook_alert(alert, channel, recipient)
                    elif channel.channel_type == 'slack':
                        result = send_slack_alert(alert, channel, recipient)
                    elif channel.channel_type == 'in_app':
                        result = send_in_app_alert(alert, channel, recipient)
                    else:
                        result = {'status': 'failed', 'error': f'Channel type {channel.channel_type} not implemented'}
                    
                    # Create log
                    log_status = 'success' if result['status'] == 'success' else 'failed'
                    AlertLog.objects.create(
                        alert=alert,
                        channel=channel,
                        recipient=recipient,
                        status=log_status,
                        response=result.get('response', ''),
                        error_message=result.get('error', '')
                    )
                    
                    if result['status'] == 'success':
                        success_count += 1
                    else:
                        failed_count += 1
                    
                    delivery_details[f'{channel.name}_{recipient.username}'] = result
                    
                    # Update channel statistics
                    channel.increment_stats(success=(result['status'] == 'success'))
                    
                except Exception as e:
                    logger.error(f"Error sending alert via {channel.name}: {str(e)}")
                    failed_count += 1
                    
                    AlertLog.objects.create(
                        alert=alert,
                        channel=channel,
                        recipient=recipient,
                        status='failed',
                        error_message=str(e)
                    )
        
        # Update alert status
        if success_count > 0 and failed_count == 0:
            alert.status = 'sent'
        elif failed_count > 0 and success_count == 0:
            alert.status = 'failed'
        elif success_count > 0 and failed_count > 0:
            alert.status = 'sent'  # Partially sent
        
        alert.delivery_details = delivery_details
        alert.save()
        
        logger.info(f"Alert {alert_id} sent: {success_count} success, {failed_count} failed")
        return {
            'status': 'success',
            'alert_id': alert_id,
            'success_count': success_count,
            'failed_count': failed_count
        }
        
    except Alert.DoesNotExist:
        logger.error(f"Alert {alert_id} not found")
        return {'status': 'failed', 'error': 'Alert not found'}
    except Exception as e:
        logger.error(f"Error sending alert: {str(e)}")
        # Retry the task if not at max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying alert {alert_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        return {'status': 'failed', 'error': str(e)}


def send_email_alert(alert, channel, recipient):
    """Send alert via email."""
    try:
        subject = f"[{alert.get_severity_display()}] {alert.title}"
        message = alert.message
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient.email],
            fail_silently=False,
        )
        
        return {'status': 'success', 'response': 'Email sent'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


def send_webhook_alert(alert, channel, recipient):
    """Send alert via webhook."""
    try:
        webhook_url = channel.configuration.get('url')
        if not webhook_url:
            return {'status': 'failed', 'error': 'Webhook URL not configured'}
        
        payload = {
            'alert_id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity,
            'status': alert.status,
            'created_at': alert.created_at.isoformat(),
            'recipient': recipient.username,
            'alert_data': alert.alert_data
        }
        
        headers = channel.configuration.get('headers', {})
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        return {'status': 'success', 'response': f'Status code: {response.status_code}'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


def send_slack_alert(alert, channel, recipient):
    """Send alert via Slack."""
    try:
        webhook_url = channel.configuration.get('webhook_url')
        if not webhook_url:
            return {'status': 'failed', 'error': 'Slack webhook URL not configured'}
        
        # Severity colors
        colors = {
            'low': '#36a64f',
            'medium': '#ff9900',
            'high': '#ff6600',
            'critical': '#ff0000'
        }
        
        payload = {
            'text': f'Nueva Alerta: {alert.title}',
            'attachments': [{
                'color': colors.get(alert.severity, '#808080'),
                'fields': [
                    {'title': 'Severidad', 'value': alert.get_severity_display(), 'short': True},
                    {'title': 'Estado', 'value': alert.get_status_display(), 'short': True},
                    {'title': 'Mensaje', 'value': alert.message, 'short': False},
                ],
                'footer': 'SMGI',
                'ts': int(alert.created_at.timestamp())
            }]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        return {'status': 'success', 'response': 'Slack message sent'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


def send_in_app_alert(alert, channel, recipient):
    """Send in-app notification."""
    # This would integrate with a notification system
    # For now, just log it
    logger.info(f"In-app alert for {recipient.username}: {alert.title}")
    return {'status': 'success', 'response': 'In-app notification created'}


@shared_task(bind=True, max_retries=2)
def test_alert_channel(self, channel_id, user_id):
    """
    Test an alert channel.
    
    Args:
        channel_id: ID of the AlertChannel
        user_id: ID of the User
    """
    try:
        from apps.users.models import User
        
        channel = AlertChannel.objects.get(id=channel_id)
        user = User.objects.get(id=user_id)
        
        logger.info(f"Testing channel: {channel.name}")
        
        # Create a test alert (not saved to DB)
        test_alert = Alert(
            title='Prueba de Canal',
            message='Este es un mensaje de prueba del sistema de alertas.',
            severity='low'
        )
        
        if channel.channel_type == 'email':
            result = send_email_alert(test_alert, channel, user)
        elif channel.channel_type == 'webhook':
            result = send_webhook_alert(test_alert, channel, user)
        elif channel.channel_type == 'slack':
            result = send_slack_alert(test_alert, channel, user)
        elif channel.channel_type == 'in_app':
            result = send_in_app_alert(test_alert, channel, user)
        else:
            result = {'status': 'failed', 'error': f'Channel type {channel.channel_type} not implemented'}
        
        logger.info(f"Channel test result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error testing channel: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def create_alert_for_detection(detection_id):
    """
    Create alerts for a detection based on alert rules.
    
    Args:
        detection_id: ID of the Detection
    """
    try:
        from apps.monitoring.models import Detection
        
        detection = Detection.objects.select_related('monitor').get(id=detection_id)
        
        logger.info(f"Creating alerts for detection: {detection.title}")
        
        # Find matching alert rules
        rules = AlertRule.objects.filter(
            is_enabled=True,
            is_active=True
        ).filter(
            models.Q(monitors=detection.monitor) |
            models.Q(projects=detection.monitor.project)
        )
        
        # Filter by severity
        severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        detection_severity_level = severity_order.get(detection.severity, 0)
        
        alerts_created = 0
        for rule in rules:
            rule_severity_level = severity_order.get(rule.severity, 0)
            
            # Only trigger if detection severity >= rule severity
            if detection_severity_level >= rule_severity_level:
                # Check throttling
                if rule.throttle_minutes > 0 and rule.last_triggered:
                    time_since_last = timezone.now() - rule.last_triggered
                    if time_since_last.total_seconds() < rule.throttle_minutes * 60:
                        logger.info(f"Rule {rule.name} throttled")
                        continue
                
                # Create alert
                alert = Alert.objects.create(
                    rule=rule,
                    title=detection.title,
                    message=detection.description or f'Nueva detección: {detection.title}',
                    severity=detection.severity,
                    detection=detection,
                    monitor=detection.monitor,
                    alert_data={
                        'detection_id': detection.id,
                        'confidence_score': detection.confidence_score,
                        'analysis_data': detection.analysis_data
                    },
                    created_by=detection.created_by
                )
                
                # Send alert
                send_alert.delay(alert.id)
                
                # Update rule
                rule.increment_trigger()
                
                alerts_created += 1
        
        logger.info(f"Created {alerts_created} alerts for detection {detection_id}")
        return {'status': 'success', 'alerts_created': alerts_created}
        
    except Exception as e:
        logger.error(f"Error creating alerts for detection: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def cleanup_old_alerts(days=90):
    """
    Archive old resolved alerts.
    
    Args:
        days: Number of days to keep alerts
    """
    from datetime import timedelta
    
    threshold_date = timezone.now() - timedelta(days=days)
    
    updated = Alert.objects.filter(
        created_at__lt=threshold_date,
        status__in=['resolved', 'acknowledged']
    ).update(is_active=False)
    
    logger.info(f"Archived {updated} old alerts")
    return f"Archived {updated} alerts"


@shared_task
def process_pending_alerts():
    """
    Process pending alerts that haven't been sent.
    This task should run periodically.
    """
    logger.info("Processing pending alerts")
    
    pending_alerts = Alert.objects.filter(
        status='pending',
        is_active=True
    )
    
    processed = 0
    for alert in pending_alerts:
        send_alert.delay(alert.id)
        processed += 1
    
    logger.info(f"Processed {processed} pending alerts")
    return f"Processed {processed} alerts"
