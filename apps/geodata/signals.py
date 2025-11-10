"""
Signals for Geodata app.
"""
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from .models import DataSource, Layer, Feature, Dataset
from .tasks import update_layer_statistics
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DataSource)
def data_source_post_save(sender, instance, created, **kwargs):
    """
    Actions after DataSource is saved.
    """
    if created:
        logger.info(f"New data source created: {instance.name}")
        # Optionally trigger initial sync
        # from .tasks import sync_data_source
        # sync_data_source.delay(instance.id)


@receiver(post_save, sender=Layer)
def layer_post_save(sender, instance, created, **kwargs):
    """
    Actions after Layer is saved.
    """
    if created:
        logger.info(f"New layer created: {instance.name}")


@receiver(post_save, sender=Feature)
def feature_post_save(sender, instance, created, **kwargs):
    """
    Actions after Feature is saved.
    Update layer statistics.
    """
    if created:
        # Trigger async task to update layer statistics
        update_layer_statistics.delay(instance.layer.id)


@receiver(pre_delete, sender=Feature)
def feature_pre_delete(sender, instance, **kwargs):
    """
    Actions before Feature is deleted.
    """
    # Update layer statistics after deletion
    update_layer_statistics.delay(instance.layer.id)


@receiver(m2m_changed, sender=Dataset.layers.through)
def dataset_layers_changed(sender, instance, action, **kwargs):
    """
    Actions when layers are added/removed from Dataset.
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        logger.info(f"Layers changed for dataset: {instance.name}")
