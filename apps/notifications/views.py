"""
SMGI Backend - Notifications System (COMPLETO)
Sistema de Monitoreo Geoespacial Inteligente

Este archivo contiene TODO el sistema de notificaciones en un solo lugar
para garantizar que esté 100% completo.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar notificaciones"""
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            is_removed=False
        )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Marcar notificación como leída"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'message': _('Notification marked as read')})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Marcar todas las notificaciones como leídas"""
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'message': _('All notifications marked as read')})
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Obtener notificaciones no leídas"""
        unread = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(unread, many=True)
        return Response({
            'count': unread.count(),
            'notifications': serializer.data
        })
