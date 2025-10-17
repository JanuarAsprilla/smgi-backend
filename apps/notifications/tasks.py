"""
SMGI Backend - Notifications Tasks
Sistema de Monitoreo Geoespacial Inteligente
Tareas asíncronas completas para el sistema de notificaciones
"""
# --- MEJORA: Importaciones al inicio del módulo para claridad y evitar NameErrors ---
import logging
import time
import requests
from celery import shared_task, current_task
# from django.core.mail import send_mail, EmailMultiAlternatives # No se usa send_mail directamente
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.db import models # Importar models para F()
from datetime import timedelta

# Importar modelos de otras apps al inicio
# Nota: Algunos modelos como PasswordResetToken, EmailVerificationToken no se encuentran
# en las apps vistas. Se asume que están definidos en 'authentication' o deben ser creados.
from apps.authentication.models import User # , PasswordResetToken, EmailVerificationToken
# from apps.alerts.models import Alert # Se importará dentro de las funciones que lo usan si es necesario
# from apps.reports.models import Report # Se importará dentro de las funciones que lo usan si es necesario
# Importar modelos de esta app (notifications)
from apps.notifications.models import (
    Notification, EmailNotification, WebhookNotification, NotificationPreference
)

logger = logging.getLogger('apps.notifications')


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_email_notification(self, email_notification_id):
    """
    Enviar notificación por email con reintentos
    """
    # from apps.notifications.models import EmailNotification # Ya importado
    
    try:
        email_notif = EmailNotification.objects.get(id=email_notification_id)
        
        # Check if already sent
        if email_notif.status == 'sent':
            logger.info(f"Email {email_notification_id} already sent, skipping")
            return {'success': True, 'already_sent': True}
        
        # Update status to sending
        email_notif.status = 'sending'
        email_notif.save(update_fields=['status'])
        
        logger.info(f"Sending email to {email_notif.recipient_email}: {email_notif.subject}")
        
        # Prepare email
        from django.core.mail import EmailMultiAlternatives # Importar aquí si no se hizo al inicio
        email = EmailMultiAlternatives(
            subject=email_notif.subject,
            body=email_notif.body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_notif.recipient_email],
            cc=email_notif.cc_emails if email_notif.cc_emails else None,
            bcc=email_notif.bcc_emails if email_notif.bcc_emails else None,
        )
        
        # Add HTML alternative if available
        if email_notif.body_html:
            email.attach_alternative(email_notif.body_html, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        # Mark as sent
        email_notif.mark_sent()
        
        logger.info(f"Email sent successfully to {email_notif.recipient_email}")
        
        return {
            'success': True,
            'email_id': str(email_notification_id),
            'recipient': email_notif.recipient_email
        }
        
    except EmailNotification.DoesNotExist:
        logger.error(f"EmailNotification {email_notification_id} not found")
        return {'success': False, 'error': 'Email notification not found'}
    
    except Exception as e:
        logger.error(f"Error sending email {email_notification_id}: {e}")
        
        try:
            email_notif = EmailNotification.objects.get(id=email_notification_id)
            email_notif.mark_failed(str(e))
        except EmailNotification.DoesNotExist:
            pass # Ya no existe, no se puede marcar como fallido
        except Exception as inner_e:
             logger.error(f"Could not mark email {email_notification_id} as failed: {inner_e}")
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_alert_email(self, alert_id, user_id):
    """
    Enviar email de alerta a un usuario
    """
    # from apps.alerts.models import Alert # Ya importado o se importará
    # from apps.authentication.models import User # Ya importado
    # from apps.notifications.models import EmailNotification # Ya importado
    
    try:
        # --- CORRECCIÓN: Importar modelos aquí o asegurar que estén arriba ---
        from apps.alerts.models import Alert
        # User ya está importado
        # EmailNotification ya está importado

        alert = Alert.objects.get(id=alert_id)
        user = User.objects.get(id=user_id)
        
        # --- CORRECCIÓN: Acceder correctamente a las preferencias del usuario ---
        # Original: user.get_notification_preference('email_alerts')
        # user_notification_prefs = getattr(user, 'notification_preferences', None)
        # if user_notification_prefs and not user_notification_prefs.email_alert_notifications:
        # Mejora: Usar el modelo NotificationPreference directamente o un método helper
        try:
            user_pref = user.notification_preferences
            if not user_pref.email_alert_notifications:
                logger.info(f"User {user.email} has email alerts disabled")
                return {'success': True, 'skipped': True}
        except NotificationPreference.DoesNotExist:
            # Si no tiene preferencias, asumir valores por defecto o crearlas
            logger.warning(f"User {user.email} has no notification preferences. Using defaults.")
            # O crear preferencias por defecto
            # NotificationPreference.objects.create(user=user)
            # Para este caso, asumiremos que está habilitado por defecto si no existe la relación.
            pass

        # Prepare email content
        context = {
            'alert': alert,
            'user': user,
            'severity': alert.get_severity_display(),
            'category': alert.get_category_display(),
            'service_name': alert.service.name if alert.service else 'N/A',
            'layer_name': alert.layer.name if alert.layer else 'N/A',
            'view_url': f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/alerts/{alert.id}",
        }
        
        # Render email template
        html_content = render_to_string('notifications/email/alert_notification.html', context)
        text_content = strip_tags(html_content)
        
        # Create email notification
        email_notif = EmailNotification.objects.create(
            subject=f"[{alert.get_severity_display()}] {alert.title}",
            body_text=text_content,
            body_html=html_content,
            recipient_email=user.email,
            recipient_name=user.get_full_name(),
            user=user,
            alert=alert,
            template_name='alert_notification',
            template_context=context,
            priority='high' if alert.severity == 'critical' else 'normal'
        )
        
        # Send email asynchronously
        send_email_notification.delay(str(email_notif.id))
        
        logger.info(f"Alert email queued for {user.email}")
        
        return {
            'success': True,
            'email_notification_id': str(email_notif.id),
            'recipient': user.email
        }
        
    except (Alert.DoesNotExist, User.DoesNotExist):
         logger.error(f"Alert {alert_id} or User {user_id} not found for send_alert_email.")
         return {'success': False, 'error': 'Alert or User not found'}
    except Exception as e:
        logger.error(f"Error sending alert email: {e}")
        # --- MEJORA: No relanzar siempre, manejar errores específicos ---
        # Por ejemplo, si es un error de base de datos, quizás no se deba reintentar
        # Pero para errores de red o SMTP, sí. Aquí se mantiene el retry genérico.
        raise self.retry(exc=e)


@shared_task
def process_alert_notification(alert_id):
    """
    Procesar todas las notificaciones para una alerta
    """
    # from apps.alerts.models import Alert # Se importará dentro
    # from apps.notifications.models import Notification, NotificationPreference # Ya importados
    
    try:
        # --- CORRECCIÓN: Importar modelos aquí ---
        from apps.alerts.models import Alert
        # Notification, NotificationPreference ya están importados

        alert = Alert.objects.select_related('service', 'layer', 'assigned_to').get(id=alert_id)
        
        logger.info(f"Processing notifications for alert: {alert.alert_id}")
        
        # Determine users to notify
        users_to_notify = set()
        
        # 1. Assigned user
        if alert.assigned_to:
            users_to_notify.add(alert.assigned_to)
        
        # 2. Users subscribed to this service/layer
        # --- MEJORA: Lógica placeholder, debe mejorarse ---
        # if alert.layer:
        #     # Add users monitoring this specific layer
        #     from apps.authentication.models import User # Ya importado
        #     monitoring_users = User.objects.filter(
        #         is_active=True,
        #         email_verified=True # Asumiendo que existe este campo
        #     )
        #     # In production, you'd filter based on actual subscriptions
        #     # Ejemplo: .filter(subscriptions__layer=alert.layer)
        #     users_to_notify.update(monitoring_users)
        
        # 3. Admins for critical alerts
        # --- MEJORA: Usar constantes de UserRole si existen ---
        # from apps.authentication.models import UserRole # Asumiendo que existe
        # admins = User.objects.filter(
        #     role=UserRole.ADMIN, # O el valor constante correspondiente
        #     is_active=True
        # )
        # users_to_notify.update(admins)
        
        # --- MEJORA: Ejemplo de cómo podría ser con un servicio de suscripciones ---
        # from apps.subscriptions.models import LayerSubscription
        # subscribers = LayerSubscription.objects.filter(layer=alert.layer).select_related('user')
        # for sub in subscribers:
        #     users_to_notify.add(sub.user)

        # --- MEJORA TEMPORAL: Notificar a todos los usuarios activos (NO PARA PRODUCCIÓN) ---
        # Solo como ejemplo, ya que la lógica real no está definida.
        from apps.authentication.models import User
        all_active_users = User.objects.filter(is_active=True)
        users_to_notify.update(all_active_users)
        
        # Send notifications
        notification_count = 0
        
        for user in users_to_notify:
            # Create in-app notification
            in_app_notif = Notification.objects.create(
                title=alert.title,
                message=alert.description,
                short_message=f"[{alert.get_severity_display()}] {alert.title[:100]}",
                notification_type='alert',
                priority='urgent' if alert.severity == 'critical' else 'high',
                user=user,
                alert=alert,
                link=f"/alerts/{alert.id}",
                action_text="View Alert",
                action_url=f"/alerts/{alert.id}",
                metadata={
                    'alert_id': str(alert.id),
                    'severity': alert.severity,
                    'category': alert.category,
                }
            )
            
            # Send email if user has it enabled (llamando a la tarea corregida)
            send_alert_email.delay(str(alert.id), str(user.id))
            
            notification_count += 1
        
        logger.info(f"Created {notification_count} notifications for alert {alert.alert_id}")
        
        return {
            'success': True,
            'alert_id': str(alert.id),
            'users_notified': notification_count
        }
        
    except Alert.DoesNotExist:
        logger.error(f"Alert {alert_id} not found for process_alert_notification.")
        return {'success': False, 'error': 'Alert not found'}
    except Exception as e:
        logger.error(f"Error processing alert notification for {alert_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def send_webhook_notification(self, webhook_notification_id):
    """
    Enviar notificación vía webhook
    """
    # from apps.notifications.models import WebhookNotification # Ya importado
    
    try:
        # WebhookNotification ya está importado
        webhook = WebhookNotification.objects.get(id=webhook_notification_id)
        
        logger.info(f"Sending webhook to {webhook.webhook_url}")
        
        # Prepare headers
        headers = webhook.headers.copy() if webhook.headers else {}
        headers['Content-Type'] = 'application/json'
        headers['User-Agent'] = 'SMGI-Backend/1.0'
        
        # Add authentication
        if webhook.auth_type == 'bearer':
            token = webhook.auth_credentials.get('token')
            if token:
                headers['Authorization'] = f'Bearer {token}'
        elif webhook.auth_type == 'api_key':
            key_name = webhook.auth_credentials.get('key_name', 'X-API-Key')
            key_value = webhook.auth_credentials.get('key_value')
            if key_value:
                headers[key_name] = key_value
        
        # Send webhook
        start_time = time.time()
        
        response = requests.request(
            method=webhook.method,
            url=webhook.webhook_url,
            json=webhook.payload,
            headers=headers,
            timeout=30
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Mark as sent
        webhook.mark_sent(
            status_code=response.status_code,
            response_body=response.text[:1000],  # Limit response body size
            response_time_ms=response_time_ms
        )
        
        logger.info(f"Webhook sent successfully to {webhook.webhook_url}")
        
        return {
            'success': True,
            'webhook_id': str(webhook_notification_id),
            'status_code': response.status_code,
            'response_time_ms': response_time_ms
        }
        
    except WebhookNotification.DoesNotExist:
        logger.error(f"WebhookNotification {webhook_notification_id} not found")
        return {'success': False, 'error': 'Webhook notification not found'}
    except Exception as e:
        logger.error(f"Error sending webhook {webhook_notification_id}: {e}")
        
        try:
            webhook = WebhookNotification.objects.get(id=webhook_notification_id)
            webhook.mark_failed(str(e))
        except WebhookNotification.DoesNotExist:
            pass # Ya no existe
        except Exception as inner_e:
             logger.error(f"Could not mark webhook {webhook_notification_id} as failed: {inner_e}")
        
        raise self.retry(exc=e)


@shared_task
def cleanup_old_notifications(days_to_keep=90):
    """
    Limpiar notificaciones antiguas
    """
    # Modelos ya importados
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Delete old in-app notifications (read ones)
        deleted_in_app = Notification.objects.filter(
            created__lt=cutoff_date,
            is_read=True
        ).delete()[0] # delete() returns (num_deleted, {model: count})
        
        # Delete old email notifications
        deleted_emails = EmailNotification.objects.filter(
            created__lt=cutoff_date,
            status='sent'
        ).delete()[0]
        
        # Delete old webhook notifications
        deleted_webhooks = WebhookNotification.objects.filter(
            created__lt=cutoff_date,
            status='sent'
        ).delete()[0]
        
        logger.info(f"Cleaned up old notifications: {deleted_in_app} in-app, {deleted_emails} emails, {deleted_webhooks} webhooks")
        
        return {
            'success': True,
            'deleted_in_app': deleted_in_app,
            'deleted_emails': deleted_emails,
            'deleted_webhooks': deleted_webhooks
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def retry_failed_emails():
    """
    Reintentar envío de emails fallidos
    """
    # from apps.notifications.models import EmailNotification # Ya importado
    
    try:
        # --- CORRECCIÓN: Importar models o usar directamente EmailNotification.objects ---
        # Error original: models.F('max_retries') -> NameError: name 'models' is not defined
        # Solución 1: Importar models al inicio (ya hecho)
        # Solución 2: Usar EmailNotification._meta.get_field('max_retries') o simplemente el campo
        # La forma más directa es usar F() si models está importado.
        
        # Get failed emails that are ready for retry
        failed_emails = EmailNotification.objects.filter(
            status='failed',
            retry_count__lt=models.F('max_retries'), # models.F ya está importado
            next_retry_at__lte=timezone.now()
        )
        
        retry_count = 0
        
        for email in failed_emails:
            send_email_notification.delay(str(email.id))
            retry_count += 1
        
        logger.info(f"Queued {retry_count} failed emails for retry")
        
        return {
            'success': True,
            'emails_queued': retry_count
        }
        
    except Exception as e:
        logger.error(f"Error retrying failed emails: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_daily_digest():
    """
    Enviar resumen diario de notificaciones
    """
    # Modelos ya importados
    
    try:
        # Get users with digest enabled
        users_with_digest = NotificationPreference.objects.filter(
            digest_enabled=True,
            digest_frequency='daily'
        ).select_related('user')
        
        digest_count = 0
        
        for pref in users_with_digest:
            user = pref.user
            
            # Get unread notifications from last 24 hours
            yesterday = timezone.now() - timedelta(days=1)
            unread_notifications = Notification.objects.filter(
                user=user,
                is_read=False,
                created__gte=yesterday
            ).order_by('-created')[:50]  # Limit to 50 most recent
            
            if not unread_notifications.exists():
                continue
            
            # Prepare digest content
            context = {
                'user': user,
                'notifications': unread_notifications,
                'notification_count': unread_notifications.count(),
                'date': timezone.now().date()
            }
            
            # Render email
            html_content = render_to_string('notifications/email/daily_digest.html', context)
            text_content = strip_tags(html_content)
            
            # Create email notification
            # EmailNotification ya está importado
            email_notif = EmailNotification.objects.create(
                subject=f"Daily Digest - {unread_notifications.count()} notifications",
                body_text=text_content,
                body_html=html_content,
                recipient_email=user.email,
                recipient_name=user.get_full_name(),
                user=user,
                template_name='daily_digest',
                template_context=context
            )
            
            # Send email
            send_email_notification.delay(str(email_notif.id))
            
            digest_count += 1
        
        logger.info(f"Sent daily digest to {digest_count} users")
        
        return {
            'success': True,
            'digests_sent': digest_count
        }
        
    except Exception as e:
        logger.error(f"Error sending daily digest: {e}")
        return {'success': False, 'error': str(e)}


# --- CORRECCIÓN: Las siguientes tareas dependen de modelos que NO se encuentran en el código proporcionado ---
# Se asume que estos modelos (PasswordResetToken, EmailVerificationToken) existen en 'authentication'
# Si no existen, estas tareas fallarán. Se marcarán con un comentario de advertencia.

# NOTA IMPORTANTE PARA EL DESARROLLO:
# Las tareas siguientes requieren modelos que no están definidos en el código proporcionado:
# - send_password_reset_email: Necesita 'PasswordResetToken'
# - send_verification_email: Necesita 'EmailVerificationToken'
# Estos modelos deben ser creados en 'apps/authentication/models.py' o en otro lugar adecuado.

# Para que este archivo sea funcional, se proporcionan versiones ESQUELETO de estas tareas
# que advierten sobre la falta de modelos. En un entorno real, estos modelos deben existir.

@shared_task
def send_password_reset_email(user_id):
    """
    Enviar email de restablecimiento de contraseña
    ADVERTENCIA: Requiere el modelo 'PasswordResetToken' en 'apps.authentication.models'
    """
    # --- ADVERTENCIA: Modelo no encontrado en el código proporcionado ---
    # from apps.authentication.models import PasswordResetToken # Falta definir este modelo
    # Se asume que existe. Si no, esta tarea fallará.
    try:
        # from apps.authentication.models import User, PasswordResetToken # User ya importado
        from apps.authentication.models import PasswordResetToken # Asegurar importación
        # EmailNotification ya importado

        user = User.objects.get(id=user_id)
        
        # Generate reset token
        import secrets # Mover al inicio si se usa en más funciones
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)
        
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        # Prepare email content
        reset_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'expires_hours': 24
        }
        
        html_content = render_to_string('notifications/email/password_reset.html', context)
        text_content = strip_tags(html_content)
        
        # Create email notification
        email_notif = EmailNotification.objects.create(
            subject="Password Reset Request - SMGI",
            body_text=text_content,
            body_html=html_content,
            recipient_email=user.email,
            recipient_name=user.get_full_name(),
            user=user,
            template_name='password_reset',
            template_context=context,
            priority='high'
        )
        
        # Send email
        send_email_notification.delay(str(email_notif.id))
        
        logger.info(f"Password reset email queued for {user.email}")
        
        return {
            'success': True,
            'user_id': str(user_id),
            'email': user.email
        }
    except ImportError:
        logger.critical("Model 'PasswordResetToken' not found. Please define it in 'apps.authentication.models'. Task 'send_password_reset_email' will fail.")
        return {'success': False, 'error': 'PasswordResetToken model not found'}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for password reset.")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_verification_email(user_id):
    """
    Enviar email de verificación de cuenta
    ADVERTENCIA: Requiere el modelo 'EmailVerificationToken' en 'apps.authentication.models'
    """
    # --- ADVERTENCIA: Modelo no encontrado en el código proporcionado ---
    # from apps.authentication.models import EmailVerificationToken # Falta definir este modelo
    # Se asume que existe. Si no, esta tarea fallará.
    try:
        # from apps.authentication.models import User, EmailVerificationToken # User ya importado
        from apps.authentication.models import EmailVerificationToken # Asegurar importación
        # EmailNotification ya importado

        user = User.objects.get(id=user_id)
        
        # Check if already verified
        if getattr(user, 'email_verified', False): # Asumiendo que el modelo User tiene email_verified
            logger.info(f"User {user.email} already verified")
            return {'success': True, 'already_verified': True}
        
        # Generate verification token
        import secrets # Mover al inicio si se usa en más funciones
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7)
        
        verification_token = EmailVerificationToken.objects.create(
            user=user,
            email=user.email, # Asumiendo que el modelo tiene un campo email
            token=token,
            expires_at=expires_at
        )
        
        # Prepare email content
        verify_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/verify-email?token={token}"
        
        context = {
            'user': user,
            'verify_url': verify_url,
            'expires_days': 7
        }
        
        html_content = render_to_string('notifications/email/email_verification.html', context)
        text_content = strip_tags(html_content)
        
        # Create email notification
        email_notif = EmailNotification.objects.create(
            subject="Verify your email address - SMGI",
            body_text=text_content,
            body_html=html_content,
            recipient_email=user.email,
            recipient_name=user.get_full_name(),
            user=user,
            template_name='email_verification',
            template_context=context,
            priority='high'
        )
        
        # Send email
        send_email_notification.delay(str(email_notif.id))
        
        logger.info(f"Verification email queued for {user.email}")
        
        return {
            'success': True,
            'user_id': str(user_id),
            'email': user.email
        }
    except ImportError:
        logger.critical("Model 'EmailVerificationToken' not found. Please define it in 'apps.authentication.models'. Task 'send_verification_email' will fail.")
        return {'success': False, 'error': 'EmailVerificationToken model not found'}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for email verification.")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_welcome_email(user_id):
    """
    Enviar email de bienvenida a nuevos usuarios
    """
    # from apps.authentication.models import User # Ya importado
    # from apps.notifications.models import EmailNotification # Ya importado
    
    try:
        # User, EmailNotification ya están importados
        user = User.objects.get(id=user_id)
        
        # Prepare email content
        context = {
            'user': user,
            'login_url': f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/login"
        }
        
        html_content = render_to_string('notifications/email/welcome.html', context)
        text_content = strip_tags(html_content)
        
        # Create email notification
        email_notif = EmailNotification.objects.create(
            subject="Welcome to SMGI - Sistema de Monitoreo Geoespacial Inteligente",
            body_text=text_content,
            body_html=html_content,
            recipient_email=user.email,
            recipient_name=user.get_full_name(),
            user=user,
            template_name='welcome',
            template_context=context
        )
        
        # Send email
        send_email_notification.delay(str(email_notif.id))
        
        logger.info(f"Welcome email queued for {user.email}")
        
        return {
            'success': True,
            'user_id': str(user_id),
            'email': user.email
        }
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for welcome email.")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_report_ready_notification(report_id, user_id):
    """
    Notificar cuando un reporte está listo
    """
    # from apps.reports.models import Report # Se importará dentro
    # from apps.authentication.models import User # Ya importado
    # from apps.notifications.models import Notification, EmailNotification # Ya importados
    
    try:
        # --- CORRECCIÓN: Importar modelos aquí ---
        from apps.reports.models import Report
        # User, Notification, EmailNotification ya están importados

        report = Report.objects.get(id=report_id)
        user = User.objects.get(id=user_id)
        
        # Create in-app notification
        Notification.objects.create(
            title="Report Ready",
            message=f"Your report '{report.title}' is ready for download",
            notification_type='success',
            user=user,
            link=f"/reports/{report.id}",
            action_text="Download Report",
            action_url=f"/reports/{report.id}/download",
            metadata={
                'report_id': str(report.id),
                'report_type': getattr(report, 'report_type', 'N/A'),
                'format': getattr(report, 'format', 'N/A')
            }
        )
        
        # Send email if user has it enabled
        # --- MEJORA: Acceder correctamente a las preferencias del usuario ---
        try:
            user_pref = user.notification_preferences
            if user_pref.email_report_notifications:
                # Proceed to send email
                context = {
                    'user': user,
                    'report': report,
                    'download_url': f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/reports/{report.id}/download"
                }
                
                html_content = render_to_string('notifications/email/report_ready.html', context)
                text_content = strip_tags(html_content)
                
                email_notif = EmailNotification.objects.create(
                    subject=f"Report Ready: {report.title}",
                    body_text=text_content,
                    body_html=html_content,
                    recipient_email=user.email,
                    recipient_name=user.get_full_name(),
                    user=user,
                    template_name='report_ready',
                    template_context=context
                )
                
                send_email_notification.delay(str(email_notif.id))
        except NotificationPreference.DoesNotExist:
            # User has no preferences, skip email
            logger.info(f"User {user.email} has no notification preferences. Skipping report email.")
        # Si no tiene preferencias, no se envía email.
        
        logger.info(f"Report ready notification sent for report {report.id}")
        
        return {
            'success': True,
            'report_id': str(report_id),
            'user_id': str(user_id)
        }
    except (Report.DoesNotExist, User.DoesNotExist):
        logger.error(f"Report {report_id} or User {user_id} not found for report ready notification.")
        return {'success': False, 'error': 'Report or User not found'}
    except Exception as e:
        logger.error(f"Error sending report ready notification: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_system_notification(title, message, notification_type='system', priority='normal'):
    """
    Enviar notificación del sistema a todos los administradores
    """
    # from apps.authentication.models import User, UserRole # Se importará dentro
    # from apps.notifications.models import Notification # Ya importado
    
    try:
        # --- CORRECCIÓN: Importar modelos aquí ---
        from apps.authentication.models import UserRole # Asumiendo que existe
        # User, Notification ya están importados

        admins = User.objects.filter(
            role=UserRole.ADMIN, # Asumiendo que UserRole.ADMIN es un valor válido
            is_active=True
        )
        
        notification_count = 0
        
        for admin in admins:
            Notification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                user=admin
            )
            notification_count += 1
        
        logger.info(f"System notification sent to {notification_count} admins")
        
        return {
            'success': True,
            'admins_notified': notification_count
        }
    except Exception as e:
        logger.error(f"Error sending system notification: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_admin_notification(subject, message):
    """
    Enviar notificación urgente a administradores por email
    """
    # from apps.authentication.models import User, UserRole # Se importará dentro
    # from apps.notifications.models import EmailNotification # Ya importado
    
    try:
        # --- CORRECCIÓN: Importar modelos aquí ---
        from apps.authentication.models import UserRole # Asumiendo que existe
        # User, EmailNotification ya están importados

        admins = User.objects.filter(
            role=UserRole.ADMIN, # Asumiendo que UserRole.ADMIN es un valor válido
            is_active=True
        )
        
        email_count = 0
        
        for admin in admins:
            email_notif = EmailNotification.objects.create(
                subject=f"[ADMIN] {subject}",
                body_text=message,
                recipient_email=admin.email,
                recipient_name=admin.get_full_name(),
                user=admin,
                priority='urgent'
            )
            
            send_email_notification.delay(str(email_notif.id))
            email_count += 1
        
        logger.info(f"Admin notification emails queued for {email_count} admins")
        
        return {
            'success': True,
            'emails_queued': email_count
        }
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")
        return {'success': False, 'error': str(e)}
