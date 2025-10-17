# apps/notifications/channels/base_channel.py
"""
SMGI Backend - Base Notification Channel
Sistema de Monitoreo Geoespacial Inteligente

Defines the base class and interface for all notification channels.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('apps.notifications.channels')


class NotificationChannelError(Exception):
    """Excepción base para errores en canales de notificación."""
    pass


class NotificationChannelSendError(NotificationChannelError):
    """Excepción para errores específicos de envío."""
    pass


class BaseNotificationChannel(ABC):
    """
    Abstract base class for all notification channels.
    Defines the interface that specific channels must implement.
    """

    def __init__(self, name: str, description: str = "", is_active: bool = True):
        self.name = name
        self.description = description
        self.is_active = is_active
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    @abstractmethod
    def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a notification through this channel.

        Args:
            data (Dict[str, Any]): A dictionary containing the notification data.
                                   Structure depends on the specific channel.
                                   Common keys might include 'recipient', 'title',
                                   'message', 'priority', 'context', etc.

        Returns:
            Dict[str, Any]: A dictionary with the result of the send operation.
                           Should include at least {'success': bool, ...}.
                           Can include 'channel_message_id', 'error', 'details', etc.

        Raises:
            NotificationChannelSendError: If the send operation fails.
            NotificationChannelError: For other channel-related errors.
        """
        pass

    def validate_data(self, data: Dict[str, Any]) -> None:
        """
        Validates the data dictionary before sending.
        Subclasses can override this for specific validations.

        Args:
            data (Dict[str, Any]): The notification data.

        Raises:
            NotificationChannelError: If data is invalid.
        """
        if not isinstance(data, dict):
            raise NotificationChannelError(_("Data must be a dictionary."))

        required_keys = ['recipient', 'title', 'message']
        for key in required_keys:
            if key not in data or not data[key]:
                raise NotificationChannelError(_("Missing required key: {}").format(key))

    def format_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Formats a message string with optional context variables.
        Simple placeholder replacement. For complex templating, use Django templates.

        Args:
            message (str): The message template.
            context (Optional[Dict[str, Any]]): Context variables for formatting.

        Returns:
            str: The formatted message.
        """
        if not context:
            return message
        try:
            # Simple string formatting. For more complex templates, integrate Django templating.
            return message.format(**context)
        except (KeyError, ValueError) as e:
            self.logger.warning(f"Error formatting message: {e}. Returning raw message.")
            return message

    def get_channel_identifier(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extracts a unique identifier for the recipient/channel from the data.
        E.g., email address for email, device token for push, user ID for websocket.
        Subclasses should override this.

        Args:
            data (Dict[str, Any]): The notification data.

        Returns:
            Optional[str]: The channel-specific identifier, or None if not applicable/extractable.
        """
        return data.get('recipient') # Generic fallback

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.name}>"

    def __repr__(self):
        return self.__str__()
