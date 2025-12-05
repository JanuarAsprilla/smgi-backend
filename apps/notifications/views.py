"""
Views para gestión de notificaciones
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Notification
from .serializers import NotificationSerializer, NotificationPreferencesSerializer
from .services import notification_service


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet para notificaciones"""
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.none()  # Evitar error en spectacular
    
    def get_queryset(self):
        """Get notifications for the current user."""
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a notification as read.
        POST /api/v1/notifications/{id}/mark-read/
        """
        notification = self.get_object()
        notification.mark_as_read()
        
        return Response({
            'message': 'Notificación marcada como leída',
            'notification': NotificationSerializer(notification).data
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all notifications as read.
        POST /api/v1/notifications/mark-all-read/
        """
        from django.utils import timezone
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'{updated} notificaciones marcadas como leídas'
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications.
        GET /api/v1/notifications/unread-count/
        """
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def test_email(self, request):
        """
        Enviar email de prueba
        POST /api/v1/notifications/test-email/
        """
        success = notification_service.send_test_notification(
            request.user,
            channel='email'
        )
        
        if success:
            return Response({
                'message': 'Email de prueba enviado correctamente',
                'email': request.user.email
            })
        else:
            return Response(
                {'error': 'Error al enviar email de prueba'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def test_sms(self, request):
        """
        Enviar SMS de prueba
        POST /api/v1/notifications/test-sms/
        """
        if not request.user.profile.phone:
            return Response(
                {'error': 'No tienes un número de teléfono configurado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = notification_service.send_test_notification(
            request.user,
            channel='sms'
        )
        
        if success:
            return Response({
                'message': 'SMS de prueba enviado correctamente',
                'phone': request.user.profile.phone
            })
        else:
            return Response(
                {'error': 'Error al enviar SMS. Verifica la configuración de Twilio.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def preferences(self, request):
        """
        Obtener preferencias de notificaciones del usuario
        GET /api/v1/notifications/preferences/
        """
        profile = request.user.profile
        
        return Response({
            'email_notifications': profile.email_notifications,
            'sms_notifications': profile.sms_notifications,
            'push_notifications': profile.push_notifications,
            'notify_analysis_complete': profile.notify_analysis_complete,
            'notify_analysis_failed': profile.notify_analysis_failed,
            'notify_alerts_critical': profile.notify_alerts_critical,
            'notify_alerts_medium': profile.notify_alerts_medium,
            'notify_alerts_low': profile.notify_alerts_low,
            'notify_resource_shared': profile.notify_resource_shared,
            'notify_weekly_report': profile.notify_weekly_report,
        })
    
    @action(detail=False, methods=['put'])
    def update_preferences(self, request):
        """
        Actualizar preferencias de notificaciones
        PUT /api/v1/notifications/update-preferences/
        """
        profile = request.user.profile
        
        # Actualizar campos si están en el request
        allowed_fields = [
            'email_notifications', 'sms_notifications', 'push_notifications',
            'notify_analysis_complete', 'notify_analysis_failed',
            'notify_alerts_critical', 'notify_alerts_medium', 'notify_alerts_low',
            'notify_resource_shared', 'notify_weekly_report',
        ]
        
        for field in allowed_fields:
            if field in request.data:
                setattr(profile, field, request.data[field])
        
        profile.save()
        
        return Response({
            'message': 'Preferencias actualizadas correctamente',
            'preferences': {
                'email_notifications': profile.email_notifications,
                'sms_notifications': profile.sms_notifications,
                'push_notifications': profile.push_notifications,
            }
        })
