"""
Servicios de notificaciones (Email y SMS)
"""
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails"""
    
    @staticmethod
    def send_email(
        subject: str,
        message: str,
        recipient_list: List[str],
        from_email: Optional[str] = None,
        html_message: Optional[str] = None
    ) -> bool:
        """
        Enviar email
        
        Args:
            subject: Asunto del email
            message: Mensaje en texto plano
            recipient_list: Lista de destinatarios
            from_email: Email del remitente (opcional)
            html_message: Mensaje en HTML (opcional)
        
        Returns:
            bool: True si se envió correctamente
        """
        try:
            from_email = from_email or settings.DEFAULT_FROM_EMAIL
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Email enviado a {len(recipient_list)} destinatarios: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email: {str(e)}")
            return False
    
    @staticmethod
    def send_analysis_complete(user, analysis):
        """Notificar que un análisis se completó"""
        subject = f"Análisis Completado: {analysis.name}"
        message = f"""
Hola {user.first_name or user.username},

Tu análisis "{analysis.name}" ha sido completado exitosamente.

Detalles:
- Capas analizadas: {analysis.layers.count()}
- Estado: Completado
- Fecha: {analysis.completed_at}

Puedes ver los resultados en: {settings.FRONTEND_URL}/processes

Saludos,
Sistema SMGI
"""
        
        return EmailService.send_email(
            subject=subject,
            message=message,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_analysis_failed(user, analysis, error):
        """Notificar que un análisis falló"""
        subject = f"Análisis Fallido: {analysis.name}"
        message = f"""
Hola {user.first_name or user.username},

Tu análisis "{analysis.name}" ha fallado.

Error: {error}

Por favor revisa la configuración e intenta nuevamente.

Puedes ver más detalles en: {settings.FRONTEND_URL}/processes

Saludos,
Sistema SMGI
"""
        
        return EmailService.send_email(
            subject=subject,
            message=message,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_alert_notification(user, alert):
        """Notificar sobre una alerta"""
        subject = f"⚠️ Alerta: {alert.title}"
        message = f"""
Hola {user.first_name or user.username},

Se ha detectado una alerta que requiere tu atención:

Título: {alert.title}
Severidad: {alert.severity}
Descripción: {alert.description}

Fecha de detección: {alert.created_at}

Puedes revisar más detalles en: {settings.FRONTEND_URL}/monitoring

Saludos,
Sistema SMGI
"""
        
        return EmailService.send_email(
            subject=subject,
            message=message,
            recipient_list=[user.email]
        )


class SMSService:
    """Servicio para envío de SMS usando Twilio"""
    
    def __init__(self):
        self.enabled = all([
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_PHONE_NUMBER,
        ])
        
        if self.enabled:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.from_phone = settings.TWILIO_PHONE_NUMBER
        else:
            logger.warning("SMS service not configured. Set TWILIO_* in settings.")
    
    def send_sms(self, to_phone: str, message: str) -> bool:
        """
        Enviar SMS
        
        Args:
            to_phone: Número de teléfono destino (formato internacional)
            message: Mensaje a enviar (máx 160 caracteres)
        
        Returns:
            bool: True si se envió correctamente
        """
        if not self.enabled:
            logger.warning(f"SMS not sent (service disabled): {message[:50]}...")
            return False
        
        try:
            # Normalizar número de teléfono
            if not to_phone.startswith('+'):
                to_phone = f'+{to_phone}'
            
            # Limitar mensaje a 160 caracteres
            if len(message) > 160:
                message = message[:157] + '...'
            
            # Enviar SMS
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=to_phone
            )
            
            logger.info(f"SMS enviado a {to_phone}: {message_obj.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando SMS a {to_phone}: {str(e)}")
            return False
    
    def send_analysis_complete_sms(self, user, analysis):
        """Notificar por SMS que un análisis se completó"""
        if not user.profile.phone or not user.profile.sms_notifications:
            return False
        
        message = f"SMGI: Análisis '{analysis.name}' completado. Ver resultados: {settings.FRONTEND_URL}"
        return self.send_sms(user.profile.phone, message)
    
    def send_analysis_failed_sms(self, user, analysis):
        """Notificar por SMS que un análisis falló"""
        if not user.profile.phone or not user.profile.sms_notifications:
            return False
        
        message = f"SMGI: Análisis '{analysis.name}' falló. Revisa detalles en {settings.FRONTEND_URL}"
        return self.send_sms(user.profile.phone, message)
    
    def send_alert_sms(self, user, alert):
        """Notificar por SMS sobre una alerta crítica"""
        if not user.profile.phone or not user.profile.sms_notifications:
            return False
        
        # Solo enviar SMS para alertas críticas
        if alert.severity != 'critical':
            return False
        
        message = f"SMGI ALERTA: {alert.title}. Ver: {settings.FRONTEND_URL}/monitoring"
        return self.send_sms(user.profile.phone, message)


class NotificationService:
    """Servicio unificado de notificaciones"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.sms_service = SMSService()
    
    def notify_analysis_complete(self, user, analysis):
        """Notificar análisis completado (email y SMS según preferencias)"""
        results = {}
        
        # Email
        if user.profile.email_notifications and user.profile.notify_analysis_complete:
            results['email'] = self.email_service.send_analysis_complete(user, analysis)
        
        # SMS
        if user.profile.sms_notifications and user.profile.notify_analysis_complete:
            results['sms'] = self.sms_service.send_analysis_complete_sms(user, analysis)
        
        return results
    
    def notify_analysis_failed(self, user, analysis, error):
        """Notificar análisis fallido (email y SMS según preferencias)"""
        results = {}
        
        # Email
        if user.profile.email_notifications and user.profile.notify_analysis_failed:
            results['email'] = self.email_service.send_analysis_failed(user, analysis, error)
        
        # SMS
        if user.profile.sms_notifications and user.profile.notify_analysis_failed:
            results['sms'] = self.sms_service.send_analysis_failed_sms(user, analysis)
        
        return results
    
    def notify_alert(self, user, alert):
        """Notificar sobre alerta según severidad y preferencias"""
        results = {}
        
        # Determinar si notificar según severidad
        should_notify = False
        if alert.severity == 'critical' and user.profile.notify_alerts_critical:
            should_notify = True
        elif alert.severity == 'medium' and user.profile.notify_alerts_medium:
            should_notify = True
        elif alert.severity == 'low' and user.profile.notify_alerts_low:
            should_notify = True
        
        if not should_notify:
            return results
        
        # Email
        if user.profile.email_notifications:
            results['email'] = self.email_service.send_alert_notification(user, alert)
        
        # SMS (solo alertas críticas)
        if user.profile.sms_notifications and alert.severity == 'critical':
            results['sms'] = self.sms_service.send_alert_sms(user, alert)
        
        return results
    
    def send_test_notification(self, user, channel='email'):
        """Enviar notificación de prueba"""
        if channel == 'email':
            return self.email_service.send_email(
                subject="Prueba de Notificación SMGI",
                message="Este es un email de prueba del sistema SMGI.",
                recipient_list=[user.email]
            )
        elif channel == 'sms':
            if not user.profile.phone:
                return False
            return self.sms_service.send_sms(
                user.profile.phone,
                "SMGI: Mensaje de prueba exitoso"
            )
        return False


# Instancia global
notification_service = NotificationService()
