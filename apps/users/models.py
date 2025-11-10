"""
User models for SMGI.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    """
    
    class UserRole(models.TextChoices):
        ADMIN = 'admin', _('Administrador')
        ANALYST = 'analyst', _('Analista')
        VIEWER = 'viewer', _('Observador')
        DEVELOPER = 'developer', _('Desarrollador')
    
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        _('rol'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VIEWER
    )
    organization = models.CharField(
        _('organización'),
        max_length=255,
        blank=True
    )
    phone = models.CharField(
        _('teléfono'),
        max_length=20,
        blank=True
    )
    bio = models.TextField(
        _('biografía'),
        blank=True
    )
    avatar = models.ImageField(
        _('avatar'),
        upload_to='avatars/',
        blank=True,
        null=True
    )
    is_verified = models.BooleanField(
        _('verificado'),
        default=False
    )
    created_at = models.DateTimeField(
        _('fecha de creación'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('fecha de actualización'),
        auto_now=True
    )
    
    class Meta:
        verbose_name = _('usuario')
        verbose_name_plural = _('usuarios')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username
    
    @property
    def full_name(self):
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.username


class UserProfile(models.Model):
    """
    Extended user profile information.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    preferences = models.JSONField(
        _('preferencias'),
        default=dict,
        blank=True
    )
    notification_settings = models.JSONField(
        _('configuración de notificaciones'),
        default=dict,
        blank=True
    )
    api_key = models.CharField(
        _('API key'),
        max_length=100,
        blank=True,
        unique=True,
        null=True
    )
    last_login_ip = models.GenericIPAddressField(
        _('última IP de acceso'),
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = _('perfil de usuario')
        verbose_name_plural = _('perfiles de usuario')
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
