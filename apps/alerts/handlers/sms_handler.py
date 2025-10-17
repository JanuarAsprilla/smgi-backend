# apps/alerts/handlers/sms_handler.py
import logging
from typing import Dict, Any, List, Optional
from django.conf import settings
# Importar el cliente del servicio de SMS (ej: Twilio)
# from twilio.rest import Client
# from twilio.base.exceptions import TwilioRestException


logger = logging.getLogger('apps.alerts.handlers.sms')


class SMSHandler:
    """
    Handler for sending alert notifications via SMS.
    This example uses Twilio. You might need to adapt it for other providers.
    """

    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None, twilio_phone_number: Optional[str] = None):
        """
        Initializes the SMSHandler.

        Args:
            account_sid (Optional[str]): Twilio Account SID. If None, uses from settings.
            auth_token (Optional[str]): Twilio Auth Token. If None, uses from settings.
            twilio_phone_number (Optional[str]): Phone number to send SMS from. If None, uses from settings.
        """
        self.account_sid = account_sid or getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = auth_token or getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.twilio_phone_number = twilio_phone_number or getattr(settings, 'TWILIO_PHONE_NUMBER', None)

        if not all([self.account_sid, self.auth_token, self.twilio_phone_number]):
            logger.warning("Twilio credentials or phone number not fully configured for SMSHandler.")
            self.client = None
        else:
            try:
                # from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
            except ImportError:
                logger.error("Twilio library not installed. Install 'twilio' package.")
                self.client = None
            except Exception as e:
                logger.error(f"Error initializing Twilio client: {e}")
                self.client = None

    def send_alert_sms(self, alert: Alert, phone_numbers: List[str], message_template: str = "Alerta SMGI: {title} - {description}") -> bool:
        """
        Sends an SMS notification for an alert.

        Args:
            alert (Alert): The alert instance triggering the notification.
            phone_numbers (List[str]): List of phone numbers to send the SMS to (e.g., ['+1234567890']).
            message_template (str): Template string for the SMS message.

        Returns:
            bool: True if all SMS were sent successfully, False otherwise.
        """
        if not self.client:
            logger.error("SMSHandler not properly initialized or Twilio client unavailable.")
            return False

        message_body = message_template.format(title=alert.title[:20], description=alert.description[:50]) # Truncate if needed by SMS provider

        success = True
        for number in phone_numbers:
            try:
                # from twilio.base.exceptions import TwilioRestException
                message = self.client.messages.create(
                    body=message_body,
                    from_=self.twilio_phone_number,
                    to=number
                )
                logger.info(f"SMS notification sent successfully for alert {alert.alert_id} to {number}. SID: {message.sid}")
            except Exception as e: # TwilioRestException as e:
                logger.error(f"Failed to send SMS notification for alert {alert.alert_id} to {number}: {e}")
                success = False # Mark as failed if any single message fails

        return success
