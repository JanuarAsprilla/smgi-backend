# apps/alerts/handlers/websocket_handler.py
import json
import logging
from typing import Dict, Any, List, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from apps.alerts.models import Alert


logger = logging.getLogger('apps.alerts.handlers.websocket')


class WebSocketHandler:
    """
    Handler for sending alert notifications via WebSockets using Django Channels.
    Assumes a consumer that listens on a specific group (e.g., 'alerts_group').
    """

    def __init__(self, channel_layer_alias: str = 'default'):
        """
        Initializes the WebSocketHandler.

        Args:
            channel_layer_alias (str): Alias of the channel layer to use (defined in Django settings).
        """
        self.channel_layer = get_channel_layer(alias=channel_layer_alias)
        if not self.channel_layer:
             logger.error(f"Channel layer '{channel_layer_alias}' not found or not configured.")
        # The group name where alert notifications are broadcasted
        self.alerts_group_name = "alerts_group" 

    def send_alert_websocket(self, alert: Alert, specific_channels: Optional[List[str]] = None) -> bool:
        """
        Sends an alert notification via WebSocket.

        Args:
            alert (Alert): The alert instance triggering the notification.
            specific_channels (Optional[List[str]]): List of specific channel names to send the message to.
                                                     If None, broadcasts to the 'alerts_group'.

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        if not self.channel_layer:
            logger.error("Channel layer not available.")
            return False

        # Prepare the message data
        message_data = {
            "type": "alert.message", # Type expected by the consumer
            "alert_id": str(alert.id),
            "alert_title": alert.title,
            "alert_description": alert.description,
            "alert_category": alert.category,
            "alert_severity": alert.severity,
            "first_detected": alert.first_detected.isoformat(),
            "assigned_to": alert.assigned_to.get_full_name() if alert.assigned_to else None,
            "service_name": alert.service.name if alert.service else None,
            "layer_name": alert.layer.name if alert.layer else None,
        }

        try:
            if specific_channels:
                # Send to specific channels
                for channel_name in specific_channels:
                    async_to_sync(self.channel_layer.send)(
                        channel_name,
                        message_data
                    )
                logger.info(f"WebSocket notification sent to specific channels for alert {alert.alert_id}")
            else:
                # Broadcast to the group
                async_to_sync(self.channel_layer.group_send)(
                    self.alerts_group_name,
                    message_data
                )
                logger.info(f"WebSocket notification broadcasted to group '{self.alerts_group_name}' for alert {alert.alert_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to send WebSocket notification for alert {alert.alert_id}: {e}")
            return False

    def add_to_alerts_group(self, channel_name: str) -> bool:
        """
        Adds a WebSocket channel to the alerts group.

        Args:
            channel_name (str): The name of the channel to add.

        Returns:
            bool: True if added successfully, False otherwise.
        """
        if not self.channel_layer:
            logger.error("Channel layer not available.")
            return False
        try:
            async_to_sync(self.channel_layer.group_add)(
                self.alerts_group_name,
                channel_name
            )
            logger.info(f"Channel {channel_name} added to group '{self.alerts_group_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to add channel {channel_name} to group '{self.alerts_group_name}': {e}")
            return False

    def remove_from_alerts_group(self, channel_name: str) -> bool:
        """
        Removes a WebSocket channel from the alerts group.

        Args:
            channel_name (str): The name of the channel to remove.

        Returns:
            bool: True if removed successfully, False otherwise.
        """
        if not self.channel_layer:
            logger.error("Channel layer not available.")
            return False
        try:
            async_to_sync(self.channel_layer.group_discard)(
                self.alerts_group_name,
                channel_name
            )
            logger.info(f"Channel {channel_name} removed from group '{self.alerts_group_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to remove channel {channel_name} from group '{self. alerts_group_name}': {e}")
            return False
