"""
Utility functions for Notifications app.
"""
from typing import List
from django.contrib.auth import get_user_model
from .models import Notification
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def create_notification(user, title, message, type='info', 
                       related_object_type=None, related_object_id=None):
    """
    Create a notification for a user.
    
    Args:
        user: User instance
        title: Notification title
        message: Notification message
        type: Notification type (info, success, warning, error, alert)
        related_object_type: Optional related object type
        related_object_id: Optional related object ID
    
    Returns:
        Notification instance
    """
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        related_object_type=related_object_type,
        related_object_id=related_object_id
    )
    
    logger.info(f"Notification created for user {user.username}: {title}")
    return notification


def create_bulk_notifications(users: List, title, message, type='info'):
    """
    Create notifications for multiple users.
    
    Args:
        users: List of User instances
        title: Notification title
        message: Notification message
        type: Notification type
    
    Returns:
        List of created notifications
    """
    notifications = []
    
    for user in users:
        notification = Notification(
            user=user,
            type=type,
            title=title,
            message=message
        )
        notifications.append(notification)
    
    created = Notification.objects.bulk_create(notifications)
    logger.info(f"Created {len(created)} bulk notifications")
    
    return created


def get_unread_count(user):
    """
    Get count of unread notifications for a user.
    
    Args:
        user: User instance
    
    Returns:
        int: Count of unread notifications
    """
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_all_read(user):
    """
    Mark all notifications as read for a user.
    
    Args:
        user: User instance
    
    Returns:
        int: Number of notifications marked as read
    """
    from django.utils import timezone
    
    updated = Notification.objects.filter(
        user=user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    logger.info(f"Marked {updated} notifications as read for user {user.username}")
    return updated
