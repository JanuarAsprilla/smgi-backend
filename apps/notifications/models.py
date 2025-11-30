"""
Models for Notifications app.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import User


class Notification(models.Model):
    """
    Model for storing notifications in database.
    """
    
    class NotificationType(models.TextChoices):
        INFO = 'info', _('Información')
        SUCCESS = 'success', _('Éxito')
        WARNING = 'warning', _('Advertencia')
        ERROR = 'error', _('Error')
        ALERT = 'alert', _('Alerta')
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('usuario')
    )
    type = models.CharField(
        _('tipo'),
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    title = models.CharField(
        _('título'),
        max_length=255
    )
    message = models.TextField(
        _('mensaje')
    )
    
    # Related objects
    related_object_type = models.CharField(
        _('tipo de objeto relacionado'),
        max_length=50,
        blank=True
    )
    related_object_id = models.IntegerField(
        _('ID de objeto relacionado'),
        null=True,
        blank=True
    )
    
    # Status
    is_read = models.BooleanField(
        _('leído'),
        default=False
    )
    read_at = models.DateTimeField(
        _('leído en'),
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        _('creado en'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('notificación')
        verbose_name_plural = _('notificaciones')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
