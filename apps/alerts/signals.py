"""
Signals for Alerts app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Alert
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Alert)
def alert_post_save(sender, instance, created, **kwargs):
    """
    Actions after Alert is saved.
    """
    if created:
        logger.info(f"New alert created: {instance.title} (severity: {instance.severity})")
        
        # If pending, schedule send
        if instance.status == 'pending':
            from .tasks import send_alert
            send_alert.delay(instance.id)
