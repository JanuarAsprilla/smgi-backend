# apps/alerts/handlers/email_handler.py
import logging
from typing import Dict, Any, List, Optional
from django.core.mail import send_mail, get_connection
from django.conf import settings
from django.template.loader import render_to_string
from apps.alerts.models import Alert


logger = logging.getLogger('apps.alerts.handlers.email')


class EmailHandler:
    """
    Handler for sending alert notifications via email.
    """

    def __init__(self, smtp_connection_params: Optional[Dict[str, Any]] = None):
        """
        Initializes the EmailHandler.

        Args:
            smtp_connection_params (Optional[Dict[str, Any]]): Parameters for a specific SMTP connection,
                                                              e.g., {'host': 'smtp.example.com', 'port': 587}.
                                                              If None, uses default Django SMTP settings.
        """
        self.smtp_connection_params = smtp_connection_params or {}

    def send_alert_email(self, alert: Alert, recipients: List[str], subject_template: str = "Alerta SMGI: {title}", body_template: str = "email_alert_body.html") -> bool:
        """
        Sends an email notification for an alert.

        Args:
            alert (Alert): The alert instance triggering the notification.
            recipients (List[str]): List of email addresses to send the notification to.
            subject_template (str): Template string for the email subject.
            body_template (str): Template name for the email body (HTML).

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        try:
            subject = subject_template.format(title=alert.title)
            
            # Prepare context for the email template
            context = {
                'alert': alert,
                'service_name': alert.service.name if alert.service else 'N/A',
                'layer_name': alert.layer.name if alert.layer else 'N/A',
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI')
            }
            
            # Render the HTML body using a template
            html_message = render_to_string(f'alerts/{body_template}', context)
            
            # Optionally, render a plain text version
            text_message = f"Alerta: {alert.title}\nDescripción: {alert.description}\nCategoría: {alert.category}\nSeveridad: {alert.get_severity_display()}\nDetectada: {alert.first_detected.strftime('%Y-%m-%d %H:%M:%S')}"

            # Get SMTP connection (default or custom)
            connection = get_connection(**self.smtp_connection_params)

            # Send the email
            send_mail(
                subject=subject,
                message=text_message, # Plain text fallback
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi-iiap.org'),
                recipient_list=recipients,
                html_message=html_message, # HTML content
                connection=connection,
                fail_silently=False # Raise exception on failure to be caught
            )

            logger.info(f"Email notification sent successfully for alert {alert.alert_id} to {recipients}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification for alert {alert.alert_id}: {e}")
            return False

    # Opcional: Método para enviar correo con adjuntos
    # def send_alert_email_with_attachments(self, alert: Alert, recipients: List[str], attachments: List[Dict[str, Any]]) -> bool:
    #     # Similar a send_alert_email, pero usando EmailMultiAlternatives y attach()
    #     # para adjuntar archivos.
    #     pass
