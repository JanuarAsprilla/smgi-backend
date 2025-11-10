"""
Signals for Automation app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Workflow, WorkflowExecution
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Workflow)
def workflow_post_save(sender, instance, created, **kwargs):
    """
    Actions after Workflow is saved.
    """
    if created:
        logger.info(f"New workflow created: {instance.name}")


@receiver(post_save, sender=WorkflowExecution)
def workflow_execution_post_save(sender, instance, created, **kwargs):
    """
    Actions after WorkflowExecution is saved.
    """
    if not created and instance.status in ['success', 'failed']:
        logger.info(f"Workflow execution {instance.id} completed with status: {instance.status}")
