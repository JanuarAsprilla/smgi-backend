"""
Signals for Monitoring app.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Monitor, Detection, MonitoringProject
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=MonitoringProject)
def monitoring_project_post_save(sender, instance, created, **kwargs):
    """
    Actions after MonitoringProject is saved.
    """
    if created:
        logger.info(f"New monitoring project created: {instance.name}")


@receiver(post_save, sender=Monitor)
def monitor_post_save(sender, instance, created, **kwargs):
    """
    Actions after Monitor is saved.
    """
    if created:
        logger.info(f"New monitor created: {instance.name}")
        
        # Calculate initial next_check if not set
        if not instance.next_check:
            from .utils import calculate_next_check
            instance.next_check = calculate_next_check(instance)
            instance.save(update_fields=['next_check'])


@receiver(post_save, sender=Detection)
def detection_post_save(sender, instance, created, **kwargs):
    """
    Actions after Detection is saved.
    """
    if created:
        logger.info(f"New detection created: {instance.title} (severity: {instance.severity})")
        
        # If critical, trigger alert
        if instance.severity == 'critical':
            from apps.monitoring.tasks import check_critical_detections
            check_critical_detections.delay()


@receiver(pre_delete, sender=Monitor)
def monitor_pre_delete(sender, instance, **kwargs):
    """
    Actions before Monitor is deleted.
    """
    logger.info(f"Monitor being deleted: {instance.name}")
    
    # Optionally archive detections instead of deleting them
    instance.detections.update(is_active=False)
