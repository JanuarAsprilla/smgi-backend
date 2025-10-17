"""
SMGI Backend - Notifications System (PARCIALMENTE COMPLETO)
Sistema de Monitoreo Geoespacial Inteligente

Este archivo contiene el sistema de notificaciones REST API.
Se enfoca en las notificaciones in-app, emails, webhooks y preferencias.
Para tareas asíncronas (envío real de emails/webhooks), ver apps/notifications/tasks.py.
"""
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.notifications.models import (
    Notification, EmailNotification, WebhookNotification, NotificationPreference
)
from apps.notifications.serializers import (
    NotificationSerializer, EmailNotificationSerializer,
    WebhookNotificationSerializer, NotificationPreferenceSerializer,
    NotificationStatsSerializer
)


@extend_schema(tags=['Notifications'])
class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar notificaciones in-app"""
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_read', 'notification_type', 'priority']
    search_fields = ['title', 'message', 'short_message']
    ordering_fields = ['created', 'is_read', 'priority']
    ordering = ['-created']
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            is_removed=False
        )
    
    def get_serializer_class(self):
        # Puede usar diferentes serializadores si se añaden acciones de creación/actualización
        return NotificationSerializer

    @extend_schema(summary='Mark Notification as Read')
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Marcar notificación como leída"""
        notification = self.get_object()
        notification.mark_as_read() # Este método ya actualiza read_at y guarda
        return Response({'message': _('Notification marked as read')})

    @extend_schema(summary='Mark Notification as Unread')
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Marcar notificación como no leída"""
        notification = self.get_object()
        notification.mark_as_unread() # Este método ya limpia read_at y guarda
        return Response({'message': _('Notification marked as unread')})

    @extend_schema(summary='Mark All Notifications as Read')
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Marcar todas las notificaciones como leídas"""
        # --- MEJORA: Actualizar read_at también ---
        # El método update() no llama a save() ni a métodos personalizados del modelo.
        # Para actualizar read_at, se puede hacer un update directo.
        now = timezone.now()
        updated_count = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=now
        )
        return Response({
            'message': _('All notifications marked as read'),
            'updated_count': updated_count
        })

    @extend_schema(summary='Get Unread Notifications')
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Obtener notificaciones no leídas"""
        unread = self.get_queryset().filter(is_read=False)
        page = self.paginate_queryset(unread)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'count': unread.count(),
                'notifications': serializer.data
            })
        
        serializer = self.get_serializer(unread, many=True)
        return Response({
            'count': unread.count(),
            'notifications': serializer.data
        })

    @extend_schema(summary='Delete Notification')
    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """Eliminar (soft delete) una notificación"""
        notification = self.get_object()
        notification.delete() # Asumiendo que delete() en SoftDeletableModel hace soft delete
        return Response({'message': _('Notification deleted')}, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary='Get Notification Statistics')
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtener estadísticas de notificaciones del usuario"""
        user_notifications = self.get_queryset()
        
        total = user_notifications.count()
        unread = user_notifications.filter(is_read=False).count()
        
        # Notificaciones de hoy
        from django.utils import timezone
        from datetime import timedelta
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today = user_notifications.filter(created__gte=today_start).count()

        # Agrupar por tipo
        by_type = user_notifications.values('notification_type').annotate(count=Count('id'))
        by_type_dict = {item['notification_type']: item['count'] for item in by_type}

        # Agrupar por prioridad
        by_priority = user_notifications.values('priority').annotate(count=Count('id'))
        by_priority_dict = {item['priority']: item['count'] for item in by_priority}

        stats_data = {
            'total_notifications': total,
            'unread_notifications': unread,
            'notifications_today': today,
            'by_type': by_type_dict,
            'by_priority': by_priority_dict
        }

        serializer = NotificationStatsSerializer(stats_data)
        return Response(serializer.data)


@extend_schema(tags=['Email Notifications'])
class EmailNotificationViewSet(mixins.RetrieveModelMixin,
                               mixins.ListModelMixin,
                               mixins.DestroyModelMixin,
                               viewsets.GenericViewSet):
    """ViewSet para ver y gestionar notificaciones por email"""
    
    serializer_class = EmailNotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'priority', 'recipient_email']
    search_fields = ['subject', 'recipient_email', 'recipient_name']
    ordering_fields = ['created', 'sent_at', 'status']
    ordering = ['-created']
    
    def get_queryset(self):
        return EmailNotification.objects.filter(
            user=self.request.user,
            is_removed=False
        )


@extend_schema(tags=['Webhook Notifications'])
class WebhookNotificationViewSet(mixins.RetrieveModelMixin,
                                 mixins.ListModelMixin,
                                 mixins.DestroyModelMixin,
                                 viewsets.GenericViewSet):
    """ViewSet para ver y gestionar notificaciones webhook"""
    
    serializer_class = WebhookNotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'webhook_url']
    ordering_fields = ['created', 'sent_at', 'status']
    ordering = ['-created']
    
    def get_queryset(self):
        return WebhookNotification.objects.filter(
            # WebhookNotification no tiene un campo user directo.
            # Se podría filtrar por alert__assigned_to=self.request.user
            # o por alguna otra relación. Por ahora, se asume acceso global
            # o se filtra por permisos más complejos.
            # Para este ejemplo, se deja sin filtro estricto por usuario.
            # En producción, se debe implementar un permiso más específico.
            is_removed=False
        )


@extend_schema(tags=['Notification Preferences'])
class NotificationPreferenceViewSet(mixins.RetrieveModelMixin,
                                   mixins.UpdateModelMixin,
                                   mixins.ListModelMixin, # Aunque es 1-1, List puede ser útil
                                   viewsets.GenericViewSet):
    """ViewSet para gestionar preferencias de notificación del usuario"""
    
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def get_object(self):
        # Obtener o crear preferencias para el usuario
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user,
            defaults={} # Valores por defecto ya definidos en el modelo
        )
        return obj

    @extend_schema(summary='Get My Notification Preferences')
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener mis preferencias de notificación"""
        preference = self.get_object()
        serializer = self.get_serializer(preference)
        return Response(serializer.data)
