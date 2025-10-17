# apps/notifications/channels/email_channel.py
"""
SMGI Backend - Email Notification Channel
Sistema de Monitoreo Geoespacial Inteligente

Concrete implementation for sending notifications via email.
"""
import logging
from typing import Dict, Any, Optional, List
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.notifications.channels.base_channel import BaseNotificationChannel, NotificationChannelSendError
from apps.notifications.models import EmailNotification # Para persistir el intento/envío

logger = logging.getLogger('apps.notifications.channels.email')


class EmailNotificationChannel(BaseNotificationChannel):
    """
    Notification channel for sending emails.
    """

    def __init__(self, name: str = "Email", description: str = "Sends notifications via email", is_active: bool = True):
        super().__init__(name, description, is_active)

    def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends an email notification.

        Expected data keys:
            - recipient (str): Recipient email address.
            - title (str): Subject of the email.
            - message (str): Plain text body.
            - html_message (Optional[str]): HTML body.
            - from_email (Optional[str]): Sender email. Defaults to DEFAULT_FROM_EMAIL.
            - cc (Optional[List[str]]): CC email addresses.
            - bcc (Optional[List[str]]): BCC email addresses.
            - attachments (Optional[List[Dict]]): List of attachments {'filename', 'content', 'mimetype'}.
            - context (Optional[Dict]): Context for templating (if templates are used).
            - template_name (Optional[str]): Name of the template to render.
            - user_id (Optional[Union[str, int]]): ID of the user (for persistence).
            - alert_id (Optional[Union[str, int]]): ID of the related alert (for persistence).

        Returns:
            Dict[str, Any]: Result of the send operation.
        """
        if not self.is_active:
            self.logger.info("Email channel is inactive. Skipping send.")
            return {'success': False, 'error': 'Channel_inactive'}

        try:
            self.validate_data(data)

            recipient_email = data['recipient']
            subject = data['title']
            text_body = data.get('message', '')
            html_body = data.get('html_message')
            from_email = data.get('from_email', getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'))
            cc_list = data.get('cc', [])
            bcc_list = data.get('bcc', [])
            attachments = data.get('attachments', [])
            context = data.get('context', {})
            template_name = data.get('template_name')
            user_id = data.get('user_id')
            alert_id = data.get('alert_id')

            # --- MEJORA: Usar plantillas si se proporciona template_name ---
            if template_name and context:
                 try:
                     html_body = render_to_string(f'notifications/email/{template_name}.html', context)
                     text_body = strip_tags(html_body)
                 except Exception as e:
                     self.logger.warning(f"Could not render template {template_name}: {e}. Using raw message.")

            # --- MEJORA: Formatear mensaje con contexto ---
            # Si no se usó plantilla, formatear el mensaje bruto
            if not html_body:
                 text_body = self.format_message(text_body, context)
                 subject = self.format_message(subject, context)

            # --- MEJORA: Persistir intento de envío ---
            email_notif_obj = None
            if user_id or alert_id:
                try:
                    email_notif_obj = EmailNotification.objects.create(
                        subject=subject,
                        body_text=text_body,
                        body_html=html_body,
                        recipient_email=recipient_email,
                        recipient_name=data.get('recipient_name', ''),
                        user_id=user_id if user_id else None,
                        alert_id=alert_id if alert_id else None,
                        cc_emails=cc_list,
                        bcc_emails=bcc_list,
                        has_attachments=bool(attachments),
                        attachments=attachments, # Asumiendo que es una lista serializable
                        status='pending',
                        priority=data.get('priority', 'normal'),
                        template_name=template_name or '',
                        template_context=context
                    )
                except Exception as e:
                    self.logger.error(f"Failed to create EmailNotification log entry: {e}")

            # --- MEJORA: Actualizar estado a 'sending' ---
            if email_notif_obj:
                 email_notif_obj.status = 'sending'
                 email_notif_obj.save(update_fields=['status'])

            # Prepare and send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=from_email,
                to=[recipient_email],
                cc=cc_list,
                bcc=bcc_list,
            )
            if html_body:
                email.attach_alternative(html_body, "text/html")

            # Attach files if provided
            for attachment in attachments:
                # attachment dict should have 'filename', 'content', 'mimetype'
                email.attach(
                    filename=attachment.get('filename'),
                    content=attachment.get('content'),
                    mimetype=attachment.get('mimetype')
                )

            email.send(fail_silently=False)

            # --- MEJORA: Marcar como enviado ---
            if email_notif_obj:
                 email_notif_obj.mark_sent() # Usa el método del modelo

            self.logger.info(f"Email sent successfully to {recipient_email}")
            return {
                'success': True,
                'recipient': recipient_email,
                'channel_message_id': 'N/A', # Django no devuelve un ID externo por defecto
                'email_notification_id': str(email_notif_obj.id) if email_notif_obj else None
            }

        except KeyError as e:
            error_msg = f"Missing key in email data: {e}"
            self.logger.error(error_msg)
            return {'success': False, 'error': 'Data_Error', 'details': error_msg}
        except Exception as e:
            error_msg = f"Failed to send email to {data.get('recipient', 'Unknown')}: {e}"
            self.logger.error(error_msg)

            # --- MEJORA: Marcar como fallido ---
            if 'email_notif_obj' in locals() and email_notif_obj:
                try:
                    email_notif_obj.mark_failed(error_msg)
                except Exception as log_error:
                    self.logger.error(f"Could not log email failure to EmailNotification object: {log_error}")

            # Re-raise as a specific channel error
            raise NotificationChannelSendError(error_msg) from e

    def validate_data(self, data: Dict[str, Any]) -> None:
        """
        Validates email-specific data.
        """
        super().validate_data(data)
        recipient = data.get('recipient')
        if not recipient or '@' not in recipient:
            raise ValueError(_("Invalid email address provided."))

    def get_channel_identifier(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Gets the email address as the channel identifier.
        """
        return data.get('recipient')
