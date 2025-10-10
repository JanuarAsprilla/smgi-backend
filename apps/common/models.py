"""
SMGI Backend - Common Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos base y utilidades comunes
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel, SoftDeletableModel


class BaseModel(TimeStampedModel, SoftDeletableModel):
    """
    Abstract base model with common fields for all models
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Soft delete this instance"""
        self.is_removed = True
        self.save(update_fields=['is_removed'])
    
    def restore(self):
        """Restore soft deleted instance"""
        self.is_removed = False
        self.save(update_fields=['is_removed'])