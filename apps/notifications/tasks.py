"""
SMGI Backend - Notifications Tasks
Sistema de Monitoreo Geoespacial Inteligente
Tareas asíncronas completas para el sistema de notificaciones
"""
import logging
import time
import requests
from celery import shared_task, current_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('apps.notifications')


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_email_notification(self, email_notification_id):
    """
    Enviar notificación por email con reintentos
    """
    from apps.notifications.models import EmailNotification
    
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
        except:
            pass
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_alert_email(self, alert_id, user_id):
    """
    Enviar email de alerta a un usuario
    """
    from apps.alerts.models import Alert
    from apps.authentication.models import User
    from apps.notifications.models import EmailNotification
    
    try:
        alert = Alert.objects.get(id=alert_id)
        user = User.objects.get(id=user_id)
        
        # Check user preferences
        if not user.get_notification_preference('email_alerts'):
            logger.info(f"User {user.email} has email alerts disabled")
            return {'success': True, 'skipped': True}
        
        # Prepare email content
        context = {
            'alert': alert,
            'user': user,
            'severity': alert.get_severity_display(),
            'category': alert.get_category_display(),
            'service_name': alert.service.name if alert.service else 'N/A',
            'layer_name': alert.layer.name if alert.layer else 'N/A',
            'view_url': f"{settings.FRONTEND_URL}/alerts/{alert.id}" if hasattr(settings, 'FRONTEND_URL') else '',
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
        
    except Exception as e:
        logger.error(f"Error sending alert email: {e}")
        raise self.retry(exc=e)


@shared_task
def process_alert_notification(alert_id):
    """
    Procesar todas las notificaciones para una alerta
    """
    from apps.alerts.models import Alert
    from apps.notifications.models import Notification, NotificationPreference
    
    try:
        alert = Alert.objects.select_related('service', 'layer', 'assigned_to').get(id=alert_id)
        
        logger.info(f"Processing notifications for alert: {alert.alert_id}")
        
        # Determine users to notify
        users_to_notify = set()
        
        # 1. Assigned user
        if alert.assigned_to:
            users_to_notify.add(alert.assigned_to)
        
        # 2. Users subscribed to this service/layer
        if alert.layer:
            # Add users monitoring this specific layer
            from apps.authentication.models import User
            monitoring_users = User.objects.filter(
                is_active=True,
                email_verified=True
            )
            # In production, you'd filter based on actual subscriptions
            users_to_notify.update(monitoring_users)
        
        # 3. Admins for critical alerts
        if alert.severity == 'critical':
            from apps.authentication.models import User, UserRole
            admins = User.objects.filter(
                role=UserRole.ADMIN,
                is_active=True
            )
            users_to_notify.update(admins)
        
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
            
            # Send email if user has it enabled
            send_alert_email.delay(str(alert.id), str(user.id))
            
            notification_count += 1
        
        logger.info(f"Created {notification_count} notifications for alert {alert.alert_id}")
        
        return {
            'success': True,
            'alert_id': str(alert.id),
            'users_notified': notification_count
        }
        
    except Exception as e:
        logger.error(f"Error processing alert notification for {alert_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def send_webhook_notification(self, webhook_notification_id):
    """
    Enviar notificación vía webhook
    """
    from apps.notifications.models import WebhookNotification
    
    try:
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
        
    except Exception as e:
        logger.error(f"Error sending webhook {webhook_notification_id}: {e}")
        
        try:
            webhook = WebhookNotification.objects.get(id=webhook_notification_id)
            webhook.mark_failed(str(e))
        except:
            pass
        
        raise self.retry(exc=e)


@shared_task
def cleanup_old_notifications(days_to_keep=90):
    """
    Limpiar notificaciones antiguas
    """
    from apps.notifications.models import Notification, EmailNotification, WebhookNotification
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Delete old in-app notifications (read ones)
        deleted_in_app = Notification.objects.filter(
            created__lt=cutoff_date,
            is_read=True
        ).delete()[0]
        
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
    from apps.notifications.models import EmailNotification
    
    try:
        # Get failed emails that are ready for retry
        failed_emails = EmailNotification.objects.filter(
            status='failed',
            retry_count__lt=models.F('max_retries'),
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
    from apps.notifications.models import Notification, NotificationPreference
    from apps.authentication.models import User
    
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
            from apps.notifications.models import EmailNotification
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


@shared_task
def send_password_reset_email(user_id):
    """
    Enviar email de restablecimiento de contraseña
    """
    from apps.authentication.models import User, PasswordResetToken
    from apps.notifications.models import EmailNotification
    import secrets
    
    try:
        user = User.objects.get(id=user_id)
        
        # Generate reset token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)
        
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        # Prepare email content
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}" if hasattr(settings, 'FRONTEND_URL') else f"http://localhost:3000/reset-password?token={token}"
        
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
        
    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_verification_email(user_id):
    """
    Enviar email de verificación de cuenta
    """
    from apps.authentication.models import User, EmailVerificationToken
    from apps.notifications.models import EmailNotification
    import secrets
    
    try:
        user = User.objects.get(id=user_id)
        
        # Check if already verified
        if user.email_verified:
            logger.info(f"User {user.email} already verified")
            return {'success': True, 'already_verified': True}
        
        # Generate verification token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7)
        
        verification_token = EmailVerificationToken.objects.create(
            user=user,
            email=user.email,
            token=token,
            expires_at=expires_at
        )
        
        # Prepare email content
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}" if hasattr(settings, 'FRONTEND_URL') else f"http://localhost:3000/verify-email?token={token}"
        
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
        
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_welcome_email(user_id):
    """
    Enviar email de bienvenida a nuevos usuarios
    """
    from apps.authentication.models import User
    from apps.notifications.models import EmailNotification
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prepare email content
        context = {
            'user': user,
            'login_url': f"{settings.FRONTEND_URL}/login" if hasattr(settings, 'FRONTEND_URL') else "http://localhost:3000/login"
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
        
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_report_ready_notification(report_id, user_id):
    """
    Notificar cuando un reporte está listo
    """
    from apps.reports.models import Report
    from apps.authentication.models import User
    from apps.notifications.models import Notification, EmailNotification
    
    try:
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
                'report_type': report.report_type,
                'format': report.format
            }
        )
        
        # Send email if user has it enabled
        if user.get_notification_preference('email_report_notifications'):
            context = {
                'user': user,
                'report': report,
                'download_url': f"{settings.FRONTEND_URL}/reports/{report.id}/download" if hasattr(settings, 'FRONTEND_URL') else ''
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
        
        logger.info(f"Report ready notification sent for report {report.id}")
        
        return {
            'success': True,
            'report_id': str(report_id),
            'user_id': str(user_id)
        }
        
    except Exception as e:
        logger.error(f"Error sending report ready notification: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_system_notification(title, message, notification_type='system', priority='normal'):
    """
    Enviar notificación del sistema a todos los administradores
    """
    from apps.authentication.models import User, UserRole
    from apps.notifications.models import Notification
    
    try:
        admins = User.objects.filter(
            role=UserRole.ADMIN,
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
    from apps.authentication.models import User, UserRole
    from apps.notifications.models import EmailNotification
    
    try:
        admins = User.objects.filter(
            role=UserRole.ADMIN,
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