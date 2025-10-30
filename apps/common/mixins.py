# apps/common/mixins.py
"""
SMGI Backend - Common Mixins
Sistema de Monitoreo Geoespacial Inteligente
Mixins reutilizables para modelos, vistas y serializadores
"""
import logging
from typing import Dict, Any, Optional, List, Union
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import models, transaction
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('apps.common.mixins')
User = get_user_model()


# === MIXINS PARA MODELOS ===

class UUIDModelMixin(models.Model):
    """
    Mixin para añadir un campo UUID como primary key a un modelo.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class TimestampedModelMixin(models.Model):
    """
    Mixin para añadir campos de creación y modificación a un modelo.
    """
    created = models.DateTimeField(_('Created'), auto_now_add=True, db_index=True)
    modified = models.DateTimeField(_('Modified'), auto_now=True, db_index=True)
    
    class Meta:
        abstract = True
        ordering = ['-created']
        indexes = [
            models.Index(fields=['created']),
            models.Index(fields=['modified']),
        ]


class SoftDeletableModelMixin(models.Model):
    """
    Mixin para añadir soft delete a un modelo.
    """
    is_removed = models.BooleanField(_('Is Removed'), default=False, db_index=True)
    removed_at = models.DateTimeField(_('Removed At'), blank=True, null=True)
    removed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_removed_by'
    )
    
    class Meta:
        abstract = True
    
    def delete(self, user=None):
        """
        Soft delete: marca el objeto como eliminado.
        """
        self.is_removed = True
        self.removed_at = timezone.now()
        self.removed_by = user
        self.save(update_fields=['is_removed', 'removed_at', 'removed_by'])
        logger.info(f"Soft deleted {self.__class__.__name__} {self.id}")
    
    def restore(self, user=None):
        """
        Restaura un objeto eliminado.
        """
        self.is_removed = False
        self.removed_at = None
        self.removed_by = None
        self.save(update_fields=['is_removed', 'removed_at', 'removed_by'])
        logger.info(f"Restored {self.__class__.__name__} {self.id}")
    
    def hard_delete(self):
        """
        Hard delete: elimina el objeto permanentemente.
        """
        logger.info(f"Hard deleting {self.__class__.__name__} {self.id}")
        super().delete()
    
    @property
    def is_active(self):
        """
        Verifica si el objeto está activo (no eliminado).
        """
        return not self.is_removed
    
    @property
    def is_deleted(self):
        """
        Verifica si el objeto está eliminado.
        """
        return self.is_removed


class OwnedModelMixin(models.Model):
    """
    Mixin para añadir campos de propiedad a un modelo.
    """
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created_by'
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_modified_by'
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """
        Guarda el objeto, estableciendo created_by y modified_by si es necesario.
        """
        user = kwargs.pop('user', None)
        if user and not self.pk and not self.created_by:
            self.created_by = user
        if user:
            self.modified_by = user
        super().save(*args, **kwargs)


class NamedModelMixin(models.Model):
    """
    Mixin para añadir un campo de nombre a un modelo.
    """
    name = models.CharField(_('Name'), max_length=200, db_index=True)
    
    class Meta:
        abstract = True
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class DescribedModelMixin(models.Model):
    """
    Mixin para añadir un campo de descripción a un modelo.
    """
    description = models.TextField(_('Description'), blank=True)
    
    class Meta:
        abstract = True


class ActivatableModelMixin(models.Model):
    """
    Mixin para añadir un campo de activación a un modelo.
    """
    is_active = models.BooleanField(_('Is Active'), default=True, db_index=True)
    
    class Meta:
        abstract = True
    
    def activate(self, user=None):
        """
        Activa el objeto.
        """
        self.is_active = True
        self.save(update_fields=['is_active'])
        logger.info(f"Activated {self.__class__.__name__} {self.id}")
    
    def deactivate(self, user=None):
        """
        Desactiva el objeto.
        """
        self.is_active = False
        self.save(update_fields=['is_active'])
        logger.info(f"Deactivated {self.__class__.__name__} {self.id}")


class ConfigurableModelMixin(models.Model):
    """
    Mixin para añadir campos de configuración a un modelo.
    """
    config = models.JSONField(
        _('Configuration'),
        default=dict,
        blank=True,
        help_text=_('Custom configuration for this object')
    )
    metadata = models.JSONField(
        _('Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional metadata for this object')
    )
    
    class Meta:
        abstract = True


class TaggableModelMixin(models.Model):
    """
    Mixin para añadir campos de etiquetas a un modelo.
    """
    tags = ArrayField(
        models.CharField(max_length=50),
        size=10,
        default=list,
        blank=True,
        verbose_name=_('Tags')
    )
    
    class Meta:
        abstract = True
    
    def add_tag(self, tag: str):
        """
        Añade una etiqueta al objeto.
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.save(update_fields=['tags'])
    
    def remove_tag(self, tag: str):
        """
        Elimina una etiqueta del objeto.
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.save(update_fields=['tags'])


class VersionedModelMixin(models.Model):
    """
    Mixin para añadir versionado a un modelo.
    """
    version = models.CharField(_('Version'), max_length=50, blank=True)
    
    class Meta:
        abstract = True


class AuditableModelMixin(models.Model):
    """
    Mixin para añadir campos de auditoría a un modelo.
    """
    last_audited = models.DateTimeField(_('Last Audited'), blank=True, null=True)
    audit_status = models.CharField(
        _('Audit Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('auditing', _('Auditing')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
        ],
        default='pending',
        db_index=True
    )
    audit_findings = models.JSONField(
        _('Audit Findings'),
        default=list,
        blank=True,
        help_text=_('Findings from the last audit')
    )
    
    class Meta:
        abstract = True
    
    def mark_as_audited(self, findings: Optional[List[Dict[str, Any]]] = None):
        """
        Marca el objeto como auditado.
        """
        self.last_audited = timezone.now()
        self.audit_status = 'completed'
        if findings:
            self.audit_findings = findings
        self.save(update_fields=['last_audited', 'audit_status', 'audit_findings'])
        logger.info(f"Marked {self.__class__.__name__} {self.id} as audited")
    
    def mark_as_audit_failed(self, error_message: str = ""):
        """
        Marca el objeto como fallido en auditoría.
        """
        self.last_audited = timezone.now()
        self.audit_status = 'failed'
        if error_message:
            self.audit_findings = [{'error': error_message}]
        self.save(update_fields=['last_audited', 'audit_status', 'audit_findings'])
        logger.info(f"Marked {self.__class__.__name__} {self.id} as audit failed")


class TrackableModelMixin(models.Model):
    """
    Mixin para añadir campos de seguimiento a un modelo.
    """
    tracking_id = models.CharField(
        _('Tracking ID'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('Unique identifier for tracking this object')
    )
    source = models.CharField(_('Source'), max_length=100, blank=True)
    destination = models.CharField(_('Destination'), max_length=100, blank=True)
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('processing', _('Processing')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
            ('cancelled', _('Cancelled')),
        ],
        default='pending',
        db_index=True
    )
    progress = models.PositiveIntegerField(
        _('Progress'),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    estimated_completion = models.DateTimeField(
        _('Estimated Completion'),
        blank=True,
        null=True
    )
    
    class Meta:
        abstract = True
    
    def update_progress(self, progress: int, estimated_completion: Optional[timezone.datetime] = None):
        """
        Actualiza el progreso del objeto.
        """
        self.progress = progress
        if estimated_completion:
            self.estimated_completion = estimated_completion
        self.save(update_fields=['progress', 'estimated_completion'])
        logger.info(f"Updated progress for {self.__class__.__name__} {self.id} to {progress}%")
    
    def mark_as_processing(self):
        """
        Marca el objeto como en proceso.
        """
        self.status = 'processing'
        self.save(update_fields=['status'])
        logger.info(f"Marked {self.__class__.__name__} {self.id} as processing")
    
    def mark_as_completed(self):
        """
        Marca el objeto como completado.
        """
        self.status = 'completed'
        self.progress = 100
        self.estimated_completion = None
        self.save(update_fields=['status', 'progress', 'estimated_completion'])
        logger.info(f"Marked {self.__class__.__name__} {self.id} as completed")
    
    def mark_as_failed(self, error_message: str = ""):
        """
        Marca el objeto como fallido.
        """
        self.status = 'failed'
        self.progress = 0
        self.estimated_completion = None
        if error_message:
            self.metadata['last_error'] = error_message
        self.save(update_fields=['status', 'progress', 'estimated_completion', 'metadata'])
        logger.info(f"Marked {self.__class__.__name__} {self.id} as failed")


class ExpirableModelMixin(models.Model):
    """
    Mixin para añadir expiración a un modelo.
    """
    expires_at = models.DateTimeField(_('Expires At'), blank=True, null=True)
    is_expired = models.BooleanField(_('Is Expired'), default=False, db_index=True)
    
    class Meta:
        abstract = True
    
    @property
    def has_expired(self):
        """
        Verifica si el objeto ha expirado.
        """
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def mark_as_expired(self):
        """
        Marca el objeto como expirado.
        """
        self.is_expired = True
        self.save(update_fields=['is_expired'])
        logger.info(f"Marked {self.__class__.__name__} {self.id} as expired")


class NotifiableModelMixin(models.Model):
    """
    Mixin para añadir notificaciones a un modelo.
    """
    notification_sent = models.BooleanField(_('Notification Sent'), default=False)
    notification_count = models.PositiveIntegerField(_('Notification Count'), default=0)
    last_notification_sent = models.DateTimeField(_('Last Notification Sent'), blank=True, null=True)
    
    class Meta:
        abstract = True
    
    def increment_notification_count(self):
        """
        Incrementa el contador de notificaciones y actualiza la fecha de la última notificación.
        """
        self.notification_count += 1
        self.last_notification_sent = timezone.now()
        self.notification_sent = True
        self.save(update_fields=['notification_count', 'last_notification_sent', 'notification_sent'])
        logger.info(f"Incremented notification count for {self.__class__.__name__} {self.id}")


class ResolvableModelMixin(models.Model):
    """
    Mixin para añadir resolución automática a un modelo.
    """
    auto_resolve = models.BooleanField(_('Auto Resolve'), default=False)
    auto_resolve_duration = models.PositiveIntegerField(
        _('Auto Resolve Duration (hours)'),
        default=24,
        blank=True,
        null=True
    )
    
    class Meta:
        abstract = True
    
    @property
    def should_auto_resolve(self):
        """
        Verifica si el objeto debería resolverse automáticamente.
        """
        if not self.auto_resolve or not self.auto_resolve_duration:
            return False
        
        # Asumir que hay un campo 'created' de tipo DateTimeField
        auto_resolve_time = self.created + timedelta(hours=self.auto_resolve_duration)
        return timezone.now() > auto_resolve_time


class SuppressibleModelMixin(models.Model):
    """
    Mixin para añadir supresión de notificaciones similares a un modelo.
    """
    suppress_similar = models.BooleanField(_('Suppress Similar Notifications'), default=True)
    suppression_duration = models.PositiveIntegerField(
        _('Suppression Duration (minutes)'),
        default=60
    )
    
    class Meta:
        abstract = True
    
    def get_similar_active_objects(self, minutes: int = 60):
        """
        Obtiene objetos similares activos dentro de un período de tiempo.
        Esta es una implementación base que debería ser sobrescrita por subclases.
        """
        # Esta implementación es un placeholder.
        # Las subclases deben implementar su propia lógica de similitud.
        return self.__class__.objects.none() # Retorna un queryset vacío
    
    def should_suppress_notifications(self):
        """
        Verifica si las notificaciones deberían suprimirse debido a objetos similares.
        """
        if not self.suppress_similar:
            return False
        
        similar_objects = self.get_similar_active_objects(self.suppression_duration)
        return similar_objects.exists()


# === MIXINS PARA SERIALIZADORES ===

class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    Un ModelSerializer que toma un parámetro `fields` adicional para
    controlar dinámicamente qué campos se deben renderizar.
    
    Uso:
        GET /api/users/?fields=id,username,email
    """
    
    def __init__(self, *args, **kwargs):
        # Extraer campos de la solicitud si están presentes
        fields = kwargs.pop('fields', None)
        
        # Inicializar el serializer padre
        super().__init__(*args, **kwargs)
        
        if fields is not None:
            # Dividir los campos por coma
            fields = fields.split(',')
            # Remover campos que no se especificaron
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class ReadOnlyFieldsModelSerializer(serializers.ModelSerializer):
    """
    Un ModelSerializer que automáticamente establece todos los campos como read_only.
    Útil para serializadores de listado o detalle donde no se permite modificación.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer todos los campos read_only
        for field_name, field in self.fields.items():
            field.read_only = True


class WriteOnlyFieldsModelSerializer(serializers.ModelSerializer):
    """
    Un ModelSerializer que automáticamente establece todos los campos como write_only.
    Útil para serializadores de creación donde no se quiere devolver datos sensibles.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer todos los campos write_only
        for field_name, field in self.fields.items():
            field.write_only = True


class ExcludeFieldsModelSerializer(serializers.ModelSerializer):
    """
    Un ModelSerializer que toma un parámetro `exclude_fields` adicional para
    controlar dinámicamente qué campos se deben excluir.
    
    Uso:
        GET /api/users/?exclude_fields=password,last_login
    """
    
    def __init__(self, *args, **kwargs):
        # Extraer campos a excluir de la solicitud si están presentes
        exclude_fields = kwargs.pop('exclude_fields', None)
        
        # Inicializar el serializer padre
        super().__init__(*args, **kwargs)
        
        if exclude_fields is not None:
            # Dividir los campos por coma
            exclude_fields = exclude_fields.split(',')
            # Remover campos que se especificaron para excluir
            for field_name in exclude_fields:
                self.fields.pop(field_name, None)


# === MIXINS PARA VIEWS ===

class OwnerRequiredMixin:
    """
    Mixin para vistas que requieren que el usuario sea el propietario del objeto.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(created_by=self.request.user)


class OwnedOrSharedRequiredMixin:
    """
    Mixin para vistas que requieren que el usuario sea el propietario
    o que el objeto esté compartido con él.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            Q(created_by=self.request.user) |
            Q(shared_with=self.request.user)
        )


class ActiveOnlyMixin:
    """
    Mixin para vistas que solo muestran objetos activos.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(is_active=True)


class SoftDeleteAwareMixin:
    """
    Mixin para vistas que son conscientes de soft deletes.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        # Excluir objetos eliminados por soft delete
        return queryset.filter(is_removed=False)


class PaginatedResponseMixin:
    """
    Mixin para vistas que devuelven respuestas paginadas con metadatos.
    """
    def get_paginated_response(self, data):
        """
        Devuelve una respuesta paginada con metadatos adicionales.
        """
        # Asumir que se usa el paginador por defecto de DRF
        # Si se usa un paginador personalizado, se debe ajustar aquí.
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)


class SuccessMessageMixin:
    """
    Mixin para vistas que devuelven mensajes de éxito.
    """
    def get_success_message(self, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Devuelve un mensaje de éxito con datos adicionales.
        """
        response_data = {'message': message}
        if 
            response_data.update(data)
        return response_data


class ErrorMessageMixin:
    """
    Mixin para vistas que devuelven mensajes de error.
    """
    def get_error_message(self, message: str, error: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Devuelve un mensaje de error con detalles adicionales.
        """
        response_data = {'error': message}
        if error:
            response_data['error_code'] = error
        if details:
            response_data['details'] = details
        return response_data


class AuditTrailMixin:
    """
    Mixin para vistas que registran cambios en objetos en AuditTrail.
    """
    def perform_create(self, serializer):
        """
        Registra la creación del objeto en AuditTrail.
        """
        user = self.request.user
        obj = serializer.save(created_by=user)
        
        # Registrar en AuditTrail
        from apps.audit.models import AuditTrail
        AuditTrail.objects.create(
            model_name=obj.__class__.__name__,
            object_id=str(obj.id),
            field_name='created',
            old_value='',
            new_value=str(obj),
            change_type='CREATED',
            user=user,
            timestamp=timezone.now(),
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            session_key=self.request.session.session_key if hasattr(self.request, 'session') else None,
            request_id=self.request.META.get('HTTP_X_REQUEST_ID'),
            correlation_id=self.request.META.get('HTTP_X_CORRELATION_ID')
        )
    
    def perform_update(self, serializer):
        """
        Registra la actualización del objeto en AuditTrail.
        """
        user = self.request.user
        old_obj = self.get_object()
        new_obj = serializer.save(modified_by=user)
        
        # Registrar cambios en campos específicos en AuditTrail
        from apps.audit.models import AuditTrail
        for field_name, field in new_obj._meta.fields:
            old_value = getattr(old_obj, field_name, None)
            new_value = getattr(new_obj, field_name, None)
            
            if old_value != new_value:
                AuditTrail.objects.create(
                    model_name=new_obj.__class__.__name__,
                    object_id=str(new_obj.id),
                    field_name=field_name,
                    old_value=str(old_value),
                    new_value=str(new_value),
                    change_type='UPDATED',
                    user=user,
                    timestamp=timezone.now(),
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    user_agent=self.request.META.get('HTTP_USER_AGENT'),
                    session_key=self.request.session.session_key if hasattr(self.request, 'session') else None,
                    request_id=self.request.META.get('HTTP_X_REQUEST_ID'),
                    correlation_id=self.request.META.get('HTTP_X_CORRELATION_ID')
                )
    
    def perform_destroy(self, instance):
        """
        Registra la eliminación del objeto en AuditTrail.
        """
        user = self.request.user
        obj = instance
        
        # Registrar en AuditTrail
        from apps.audit.models import AuditTrail
        AuditTrail.objects.create(
            model_name=obj.__class__.__name__,
            object_id=str(obj.id),
            field_name='deleted',
            old_value=str(obj),
            new_value='',
            change_type='DELETED',
            user=user,
            timestamp=timezone.now(),
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT'),
            session_key=self.request.session.session_key if hasattr(self.request, 'session') else None,
            request_id=self.request.META.get('HTTP_X_REQUEST_ID'),
            correlation_id=self.request.META.get('HTTP_X_CORRELATION_ID')
        )
        
        # Soft delete
        obj.delete(user=user)


# === MIXINS PARA TAREAS CELERY ===

class CeleryTaskMixin:
    """
    Mixin para tareas Celery que proporciona utilidades comunes.
    """
    def log_task_start(self, task_name: str, task_id: str, *args, **kwargs):
        """
        Registra el inicio de una tarea Celery.
        """
        logger.info(f"Starting Celery task: {task_name} (ID: {task_id}) with args: {args}, kwargs: {kwargs}")
    
    def log_task_completion(self, task_name: str, task_id: str, result: Any, duration_ms: int):
        """
        Registra la finalización exitosa de una tarea Celery.
        """
        logger.info(f"Completed Celery task: {task_name} (ID: {task_id}) in {duration_ms} ms with result: {result}")
    
    def log_task_failure(self, task_name: str, task_id: str, exc: Exception, traceback: str):
        """
        Registra la falla de una tarea Celery.
        """
        logger.error(f"Failed Celery task: {task_name} (ID: {task_id}) with exception: {exc}. Traceback: {traceback}")
    
    def log_task_retry(self, task_name: str, task_id: str, exc: Exception, retry_count: int):
        """
        Registra el reintento de una tarea Celery.
        """
        logger.warning(f"Retrying Celery task: {task_name} (ID: {task_id}), attempt {retry_count} after exception: {exc}")


class CeleryTaskResultMixin:
    """
    Mixin para tareas Celery que manejan resultados estructurados.
    """
    def get_task_result(self, success: bool, message: str,  Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> Dict[str, Any]:
        """
        Devuelve un resultado estructurado para una tarea Celery.
        """
        result = {
            'success': success,
            'message': message
        }
        if 
            result['data'] = data
        if error:
            result['error'] = error
        return result


class CeleryTaskErrorMixin:
    """
    Mixin para tareas Celery que manejan errores estructurados.
    """
    def handle_task_error(self, task_name: str, task_id: str, exc: Exception, traceback: str) -> Dict[str, Any]:
        """
        Maneja un error en una tarea Celery y devuelve un resultado estructurado.
        """
        self.log_task_failure(task_name, task_id, exc, traceback)
        return self.get_task_result(
            success=False,
            message=f"Task {task_name} failed",
            error=str(exc)
        )


# === FUNCIONES AUXILIARES ===

def get_user_from_request(request) -> Optional[User]:
    """
    Obtiene el usuario desde un objeto HttpRequest.
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


def get_ip_from_request(request) -> Optional[str]:
    """
    Obtiene la dirección IP desde un objeto HttpRequest.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent_from_request(request) -> Optional[str]:
    """
    Obtiene el user agent desde un objeto HttpRequest.
    """
    return request.META.get('HTTP_USER_AGENT')


def get_session_key_from_request(request) -> Optional[str]:
    """
    Obtiene la clave de sesión desde un objeto HttpRequest.
    """
    if hasattr(request, 'session'):
        return request.session.session_key
    return None


def get_request_id_from_request(request) -> Optional[str]:
    """
    Obtiene el ID de la solicitud desde un objeto HttpRequest.
    """
    return request.META.get('HTTP_X_REQUEST_ID')


def get_correlation_id_from_request(request) -> Optional[str]:
    """
    Obtiene el ID de correlación desde un objeto HttpRequest.
    """
    return request.META.get('HTTP_X_CORRELATION_ID')
