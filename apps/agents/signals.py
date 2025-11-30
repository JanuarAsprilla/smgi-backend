"""
Signals for Agents app.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Agent, AgentExecution, AgentRating
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Agent)
def agent_post_save(sender, instance, created, **kwargs):
    """
    Actions after Agent is saved.
    """
    if created:
        logger.info(f"New agent created: {instance.name}")
        
        # Send notification to admins about new agent
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_admins(
                title="Nuevo Agente Creado",
                message=f"El usuario {instance.created_by.username if instance.created_by else 'Desconocido'} ha creado un nuevo agente: {instance.name}",
                notification_type="agent_created",
                related_object_id=instance.id,
                related_object_type="agent"
            )
        except ImportError:
            logger.warning("NotificationService not available, skipping notification")
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
    
    # If agent is published, notify followers
    if instance.status == 'published' and not created:
        logger.info(f"Agent published: {instance.name}")
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_users(
                title="Agente Publicado",
                message=f"El agente '{instance.name}' ha sido publicado y está disponible en el marketplace.",
                notification_type="agent_published",
                related_object_id=instance.id,
                related_object_type="agent",
                user_ids=[instance.created_by.id] if instance.created_by else []
            )
        except ImportError:
            logger.warning("NotificationService not available, skipping notification")
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")


@receiver(post_save, sender=AgentExecution)
def agent_execution_post_save(sender, instance, created, **kwargs):
    """
    Actions after AgentExecution is saved.
    """
    if not created and instance.status in ['success', 'failed']:
        logger.info(f"Execution {instance.id} completed with status: {instance.status}")
        
        # Send notification to user
        from .tasks import notify_execution_completion
        notify_execution_completion.delay(instance.id)


@receiver(post_save, sender=AgentRating)
def agent_rating_post_save(sender, instance, created, **kwargs):
    """
    Actions after AgentRating is saved.
    Update agent average rating.
    """
    from django.db.models import Avg
    
    agent = instance.agent
    avg_rating = agent.ratings.aggregate(Avg('rating'))['rating__avg']
    
    if avg_rating:
        agent.rating = round(avg_rating, 2)
        agent.save(update_fields=['rating'])
        logger.info(f"Updated rating for agent {agent.name}: {agent.rating}")


@receiver(pre_delete, sender=AgentRating)
def agent_rating_pre_delete(sender, instance, **kwargs):
    """
    Actions before AgentRating is deleted.
    Update agent average rating.
    """
    from django.db.models import Avg
    
    agent = instance.agent
    
    # Calculate new average without this rating
    remaining_ratings = agent.ratings.exclude(id=instance.id)
    avg_rating = remaining_ratings.aggregate(Avg('rating'))['rating__avg']
    
    agent.rating = round(avg_rating, 2) if avg_rating else 0.0
    agent.save(update_fields=['rating'])
    logger.info(f"Updated rating for agent {agent.name} after deletion: {agent.rating}")
