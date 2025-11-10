"""
Utility functions for Alerts app.
"""
from django.template import Template, Context
from django.utils import timezone
import re


def render_alert_message(template_string, context_data):
    """
    Render alert message from template.
    
    Args:
        template_string: Template string with variables
        context_data: Dictionary with context data
        
    Returns:
        str: Rendered message
    """
    try:
        template = Template(template_string)
        context = Context(context_data)
        return template.render(context)
    except Exception as e:
        return template_string


def format_alert_message(alert, template=None):
    """
    Format alert message using template or default format.
    
    Args:
        alert: Alert instance
        template: Optional template string
        
    Returns:
        str: Formatted message
    """
    context = {
        'alert': alert,
        'title': alert.title,
        'message': alert.message,
        'severity': alert.get_severity_display(),
        'status': alert.get_status_display(),
        'created_at': alert.created_at,
        'detection': alert.detection,
        'monitor': alert.monitor,
        'rule': alert.rule,
    }
    
    if template:
        return render_alert_message(template, context)
    
    # Default format
    return f"""
    Alerta: {alert.title}
    Severidad: {alert.get_severity_display()}
    
    {alert.message}
    
    Fecha: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
    """


def check_quiet_hours(subscription, current_time=None):
    """
    Check if current time is within quiet hours for a subscription.
    
    Args:
        subscription: AlertSubscription instance
        current_time: Optional datetime (defaults to now)
        
    Returns:
        bool: True if in quiet hours
    """
    if not subscription.quiet_hours_start or not subscription.quiet_hours_end:
        return False
    
    if current_time is None:
        current_time = timezone.localtime(timezone.now())
    
    current_time_only = current_time.time()
    start = subscription.quiet_hours_start
    end = subscription.quiet_hours_end
    
    # Handle cases where quiet hours span midnight
    if start <= end:
        return start <= current_time_only <= end
    else:
        return current_time_only >= start or current_time_only <= end


def should_send_alert(alert, recipient):
    """
    Determine if alert should be sent to recipient based on their subscription.
    
    Args:
        alert: Alert instance
        recipient: User instance
        
    Returns:
        bool: True if alert should be sent
    """
    from .models import AlertSubscription
    
    try:
        subscription = AlertSubscription.objects.get(user=recipient, is_enabled=True)
    except AlertSubscription.DoesNotExist:
        # No subscription means send all alerts
        return True
    
    # Check quiet hours
    if check_quiet_hours(subscription):
        return False
    
    # Check minimum severity
    severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
    alert_severity = severity_order.get(alert.severity, 0)
    min_severity = severity_order.get(subscription.min_severity, 0)
    
    if alert_severity < min_severity:
        return False
    
    # Check if subscribed to the monitor/project
    if subscription.monitors.exists():
        if alert.monitor and alert.monitor not in subscription.monitors.all():
            return False
    
    if subscription.projects.exists():
        if alert.monitor and alert.monitor.project not in subscription.projects.all():
            return False
    
    return True


def extract_variables_from_template(template_string):
    """
    Extract variable names from a template string.
    
    Args:
        template_string: Template string
        
    Returns:
        list: List of variable names
    """
    # Match Django template variables {{ variable }}
    pattern = r'\{\{\s*(\w+(?:\.\w+)*)\s*\}\}'
    matches = re.findall(pattern, template_string)
    return list(set(matches))


def validate_channel_configuration(channel_type, configuration):
    """
    Validate channel configuration.
    
    Args:
        channel_type: Type of channel
        configuration: Configuration dictionary
        
    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = {
        'email': [],
        'webhook': ['url'],
        'slack': ['webhook_url'],
        'telegram': ['bot_token', 'chat_id'],
        'sms': ['api_key', 'from_number'],
    }
    
    required = required_fields.get(channel_type, [])
    
    for field in required:
        if field not in configuration or not configuration[field]:
            return False, f"Campo requerido faltante: {field}"
    
    # Validate URLs
    if channel_type in ['webhook', 'slack'] and 'url' in configuration:
        url = configuration.get('url') or configuration.get('webhook_url')
        if not url.startswith(('http://', 'https://')):
            return False, "URL debe comenzar con http:// o https://"
    
    return True, None


def get_alert_priority(severity):
    """
    Get numeric priority from severity.
    
    Args:
        severity: Severity level
        
    Returns:
        int: Priority (higher = more urgent)
    """
    priorities = {
        'low': 1,
        'medium': 2,
        'high': 3,
        'critical': 4
    }
    return priorities.get(severity, 0)


def format_alert_for_channel(alert, channel_type):
    """
    Format alert message specific to channel type.
    
    Args:
        alert: Alert instance
        channel_type: Type of channel
        
    Returns:
        dict: Formatted message data
    """
    if channel_type == 'email':
        return {
            'subject': f"[{alert.get_severity_display()}] {alert.title}",
            'body': alert.message,
            'html': f"""
                <h2>{alert.title}</h2>
                <p><strong>Severidad:</strong> {alert.get_severity_display()}</p>
                <p>{alert.message}</p>
                <p><small>Generado el {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}</small></p>
            """
        }
    
    elif channel_type == 'slack':
        return {
            'text': alert.title,
            'blocks': [
                {
                    'type': 'header',
                    'text': {'type': 'plain_text', 'text': alert.title}
                },
                {
                    'type': 'section',
                    'fields': [
                        {'type': 'mrkdwn', 'text': f"*Severidad:*\n{alert.get_severity_display()}"},
                        {'type': 'mrkdwn', 'text': f"*Estado:*\n{alert.get_status_display()}"}
                    ]
                },
                {
                    'type': 'section',
                    'text': {'type': 'mrkdwn', 'text': alert.message}
                }
            ]
        }
    
    elif channel_type == 'webhook':
        return {
            'alert_id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity,
            'status': alert.status,
            'created_at': alert.created_at.isoformat()
        }
    
    else:
        return {
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity
        }
