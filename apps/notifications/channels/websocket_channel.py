# apps/notifications/channels/websocket_channel.py
"""
SMGI Backend - Websocket Notification Channel
Sistema de Monitoreo Geoespacial Inteligente

Concrete implementation for sending real-time notifications via WebSockets.
Requires Django Channels.
"""
import logging
from typing import Dict, Any, Optional, Union
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.notifications.channels.base_channel import BaseNotificationChannel, NotificationChannelSendError

logger = logging.getLogger('apps.notifications.channels.websocket')


class WebsocketNotificationChannel(BaseNotificationChannel):
    """
    Notification channel for sending real-time notifications via WebSockets.
    Assumes a consumer listening on a specific group (e.g., user-specific group).
    """

    def __init__(
        self,
        name: str = "Websocket",
        description: str = "Sends real-time notifications via WebSockets",
        is_active: bool = True,
        channel_layer_alias: str = "default",
        default_group_prefix: str = "user_" # Prefix for user-specific groups
    ):
        super().__init__(name, description, is_active)
        self.channel_layer_alias = channel_layer_alias
        self.default_group_prefix = default_group_prefix
        self.channel_layer = get_channel_layer(alias=self.channel_layer_alias)

        if not self.channel_layer:
            self.logger.error(f"Channel layer '{self.channel_layer_alias}' not found or not configured.")
            # Dependiendo de la política, se podría lanzar una excepción aquí
            # o simplemente desactivar el canal.

    def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a websocket notification to a specific user group.

        Expected data keys:
            - recipient (Union[str, int]): User ID. Used to determine the group name.
            - title (str): Title of the notification.
            - message (str): Body of the notification.
            - type (str): Type of the websocket message (consumed by the consumer).
                          Defaults to 'notification.message'.
            - group_name (Optional[str]): Specific group name to send to.
                                          If not provided, it's derived from recipient.
            - payload (Optional[Dict]): Additional data to send with the notification.

        Returns:
            Dict[str, Any]: Result of the send operation.
        """
        if not self.is_active or not self.channel_layer:
            self.logger.info("Websocket channel is inactive or channel layer is unavailable. Skipping send.")
            return {'success': False, 'error': 'Channel_unavailable'}

        try:
            self.validate_data(data)

            user_id = data['recipient']
            title = data['title']
            message_body = data['message']
            message_type = data.get('type', 'notification.message') # Default type expected by consumers
            specific_group_name = data.get('group_name')
            payload = data.get('payload', {})

            # Determine the group name
            if specific_group_name:
                group_name = specific_group_name
            else:
                group_name = f"{self.default_group_prefix}{user_id}"

            # Prepare the message for the consumer
            websocket_message = {
                "type": message_type, # This corresponds to a method on the consumer
                "notification": {
                    "title": title,
                    "message": message_body,
                    "timestamp": data.get('timestamp'), # Opcional
                    **payload # Merge additional payload
                }
            }

            # Send the message to the group
            # --- MEJORA: Usar async_to_sync para llamar al método async del channel layer ---
            async_to_sync(self.channel_layer.group_send)(group_name, websocket_message)

            self.logger.info(f"Websocket notification sent to group {group_name}")
            return {
                'success': True,
                'recipient': user_id,
                'group_name': group_name,
                'message_type': message_type
            }

        except KeyError as e:
            error_msg = f"Missing key in websocket data: {e}"
            self.logger.error(error_msg)
            return {'success': False, 'error': 'Data_Error', 'details': error_msg}
        except Exception as e:
            error_msg = f"Failed to send websocket notification to group for user {data.get('recipient', 'Unknown')}: {e}"
            self.logger.error(error_msg)
            raise NotificationChannelSendError(error_msg) from e

    def validate_data(self, data: Dict[str, Any]) -> None:
        """
        Validates websocket-specific data.
        """
        super().validate_data(data)
        recipient = data.get('recipient')
        if not recipient:
            raise ValueError(_("Recipient (User ID) is required for websocket notifications."))

    def get_channel_identifier(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Gets the group name or user ID as the channel identifier.
        """
        group_name = data.get('group_name')
        if group_name:
            return group_name
        user_id = data.get('recipient')
        if user_id:
            return f"{self.default_group_prefix}{user_id}"
        return None

    # --- MÉTODOS AUXILIARES PARA INTERACCIÓN DIRECTA CON CANALES ---
    # Estos métodos son útiles si se necesita enviar a un canal específico
    # en lugar de un grupo.

    # def send_to_channel(self, channel_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     Sends a message directly to a specific channel (less common).
    #     """
    #     if not self.is_active or not self.channel_layer:
    #         return {'success': False, 'error': 'Channel_unavailable'}

    #     try:
    #         message_type = data.get('type', 'notification.message')
    #         payload = data.get('payload', {})
    #         # ... construir mensaje ...

    #         async_to_sync(self.channel_layer.send)(channel_name, {
    #             "type": message_type,
    #             "data": payload
    #         })
    #         return {'success': True, 'channel_name': channel_name}
    #     except Exception as e:
    #         error_msg = f"Failed to send to channel {channel_name}: {e}"
    #         self.logger.error(error_msg)
    #         return {'success': False, 'error': error_msg}

    # def add_to_group(self, group_name: str, channel_name: str) -> bool:
    #     """Adds a channel to a group."""
    #     if not self.channel_layer: return False
    #     try:
    #         async_to_sync(self.channel_layer.group_add)(group_name, channel_name)
    #         return True
    #     except Exception:
    #         return False

    # def remove_from_group(self, group_name: str, channel_name: str) -> bool:
    #     """Removes a channel from a group."""
    #     if not self.channel_layer: return False
    #     try:
    #         async_to_sync(self.channel_layer.group_discard)(group_name, channel_name)
    #         return True
    #     except Exception:
    #         return False
