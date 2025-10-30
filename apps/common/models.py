# apps/common/models.py
"""
SMGI Backend - Common Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos base y utilidades comunes
"""
import uuid
import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from model_utils.models import TimeStampedModel, SoftDeletableModel
from apps.authentication.models import User # Asumiendo que User está en authentication

logger = logging.getLogger('apps.common.models')


class BaseModel(TimeStampedModel, SoftDeletableModel):
    """
    Abstract base model with common fields for all models.
    Extends TimeStampedModel and SoftDeletableModel with additional fields and methods.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # --- MEJORA: Campos adicionales para soft delete ---
    removed_at = models.DateTimeField(_('Removed At'), blank=True, null=True)
    removed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_removed_by'
    )
    restored_at = models.DateTimeField(_('Restored At'), blank=True, null=True)
    restored_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_restored_by'
    )
    is_archived = models.BooleanField(_('Is Archived'), default=False, db_index=True)
    archived_at = models.DateTimeField(_('Archived At'), blank=True, null=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_archived_by'
    )
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user=None):
        """
        Soft delete this instance.
        Marks the object as removed and records who removed it and when.
        """
        # --- MEJORA: Llamar al método del padre para asegurar consistencia ---
        # super().delete() # SoftDeletableModel.delete() ya hace is_removed=True
        # Pero para extender la funcionalidad, lo hacemos manualmente.
        
        if not self.is_removed:
            self.is_removed = True
            self.removed_at = timezone.now()
            self.removed_by = user
            self.save(update_fields=['is_removed', 'removed_at', 'removed_by'])
            logger.info(f"Soft deleted {self.__class__.__name__} {self.id} by user {user.email if user else 'System'}")
        else:
            logger.warning(f"Attempted to soft delete already removed {self.__class__.__name__} {self.id}")
    
    def restore(self, user=None):
        """
        Restore soft deleted instance.
        Marks the object as not removed and records who restored it and when.
        """
        # --- MEJORA: Llamar al método del padre para asegurar consistencia ---
        # super().restore() # SoftDeletableModel.restore() ya hace is_removed=False
        # Pero para extender la funcionalidad, lo hacemos manualmente.
        
        if self.is_removed:
            self.is_removed = False
            self.removed_at = None
            self.removed_by = None
            self.restored_at = timezone.now()
            self.restored_by = user
            self.save(update_fields=['is_removed', 'removed_at', 'removed_by', 'restored_at', 'restored_by'])
            logger.info(f"Restored {self.__class__.__name__} {self.id} by user {user.email if user else 'System'}")
        else:
            logger.warning(f"Attempted to restore non-removed {self.__class__.__name__} {self.id}")
    
    def hard_delete(self):
        """
        Hard delete this instance.
        Permanently removes the object from the database.
        """
        logger.info(f"Hard deleting {self.__class__.__name__} {self.id}")
        super().delete() # Llama al método delete() real del modelo base de Django
    
    @property
    def is_active(self):
        """
        Check if object is active (not removed and not archived).
        """
        return not self.is_removed and not self.is_archived
    
    @property
    def is_deleted(self):
        """
        Check if object is deleted (soft deleted).
        """
        return self.is_removed
    
    @property
    def is_archived(self):
        """
        Check if object is archived.
        """
        return self.is_archived
    
    def archive(self, user=None):
        """
        Archive this instance.
        Marks the object as archived and records who archived it and when.
        """
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            self.archived_by = user
            self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
            logger.info(f"Archived {self.__class__.__name__} {self.id} by user {user.email if user else 'System'}")
        else:
            logger.warning(f"Attempted to archive already archived {self.__class__.__name__} {self.id}")
    
    def unarchive(self, user=None):
        """
        Unarchive this instance.
        Marks the object as not archived and records who unarchived it and when.
        """
        if self.is_archived:
            self.is_archived = False
            self.archived_at = None
            self.archived_by = None
            self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
            logger.info(f"Unarchived {self.__class__.__name__} {self.id} by user {user.email if user else 'System'}")
        else:
            logger.warning(f"Attempted to unarchive non-archived {self.__class__.__name__} {self.id}")


# --- MEJORA: Manager personalizado para filtrar objetos eliminados ---
class BaseManager(models.Manager):
    """
    Custom manager to filter out soft deleted objects by default.
    """
    def get_queryset(self):
        """
        Returns a queryset that excludes soft deleted objects.
        """
        return super().get_queryset().filter(is_removed=False)
    
    def active(self):
        """
        Returns a queryset of active objects (not removed and not archived).
        """
        return self.get_queryset().filter(is_archived=False)
    
    def deleted(self):
        """
        Returns a queryset of soft deleted objects.
        """
        return super().get_queryset().filter(is_removed=True)
    
    def archived(self):
        """
        Returns a queryset of archived objects.
        """
        return self.get_queryset().filter(is_archived=True)
    
    def all_with_deleted(self):
        """
        Returns a queryset of all objects, including soft deleted ones.
        """
        return super().get_queryset()


# --- MEJORA: Modelo con Manager personalizado ---
class BaseModelWithManager(BaseModel):
    """
    Abstract base model with a custom manager to filter out soft deleted objects.
    """
    objects = BaseManager()
    
    class Meta:
        abstract = True
