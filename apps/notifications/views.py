"""
Views para gestión de notificaciones
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services import notification_service


class NotificationViewSet(viewsets.ViewSet):
    """ViewSet para notificaciones"""
    
    permission_classes = [IsAuthenticated]
    
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
