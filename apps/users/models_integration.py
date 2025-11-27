"""
Agregar estos imports y clases a apps/users/models.py
"""

# Al inicio del archivo, después de los imports existentes:
from django.db import models
from django.contrib.auth import get_user_model

# Copiar todas las clases de models_roles.py:
# - Role
# - Area
# - UserProfile
# - ActivityLog

# Al final del archivo, agregar signals para crear UserProfile automáticamente:
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Crear perfil automáticamente al crear usuario"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Guardar perfil al guardar usuario"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
