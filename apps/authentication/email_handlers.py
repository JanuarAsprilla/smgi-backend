# apps/authentication/email_handlers.py
"""
SMGI Backend - Authentication Email Handlers
Sistema de Monitoreo Geoespacial Inteligente
Manejadores para el envío de emails relacionados con autenticación
"""
import logging
from typing import Dict, Any, Optional, Union
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string, strip_tags
from django.conf import settings
from django.urls import reverse

from apps.authentication.models import User, EmailVerificationToken, PasswordResetToken, UserInvitation
# Importar modelos relacionados
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert
from apps.reports.models import Report
from apps.notifications.models import Notification, EmailNotification, WebhookNotification
# Importar canal de email del sistema de notificaciones
from apps.notifications.channels.email_channel import EmailNotificationChannel
# Importar tarea para enviar email
from apps.notifications.tasks import send_email_notification
# Importar tipos de notificación del sistema de notificaciones
from apps.notifications.models import NotificationType, NotificationPriority, NotificationChannel, NotificationStatus

logger = logging.getLogger('apps.authentication.email_handlers')


class AuthenticationEmailHandler:
    """
    Manejador para el envío de emails relacionados con autenticación
    """

    def __init__(self):
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        # Usar el canal de email del sistema de notificaciones
        self.email_channel = EmailNotificationChannel(
            name='Authentication Email Channel',
            description='Sends authentication-related emails',
            is_active=True
        )

    def send_welcome_email(self, user: User) -> Optional[str]:
        """
        Envía un email de bienvenida a un nuevo usuario

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending welcome email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'login_url': getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login'),
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/welcome.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Welcome to {context['site_name']} - {user.get_full_name()}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/welcome.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Welcome email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send welcome email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending welcome email to {user.email}: {e}")
            return None

    def send_email_verification(self, user: User, token: str) -> Optional[str]:
        """
        Envía un email de verificación de dirección de correo

        Args:
            user (User): Instancia del modelo User
            token (str): Token de verificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending email verification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'verification_url': f"{getattr(settings, 'FRONTEND_VERIFY_EMAIL_URL', 'http://localhost:3000/verify-email')}?token={token}",
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'token': token
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/email_verification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Verify your email address - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/email_verification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Email verification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send email verification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending email verification to {user.email}: {e}")
            return None

    def send_password_reset(self, user: User, token: str) -> Optional[str]:
        """
        Envía un email para restablecer la contraseña

        Args:
            user (User): Instancia del modelo User
            token (str): Token de restablecimiento

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending password reset email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'reset_url': f"{getattr(settings, 'FRONTEND_RESET_PASSWORD_URL', 'http://localhost:3000/reset-password')}?token={token}",
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'token': token,
                'expires_hours': getattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS', 24)
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/password_reset.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Password reset request - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/password_reset.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Password reset email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send password reset email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending password reset email to {user.email}: {e}")
            return None

    def send_email_change_confirmation(self, user: User, new_email: str, token: str) -> Optional[str]:
        """
        Envía un email para confirmar el cambio de dirección de correo

        Args:
            user (User): Instancia del modelo User
            new_email (str): Nueva dirección de correo
            token (str): Token de confirmación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending email change confirmation to {new_email} for user {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'new_email': new_email,
                'confirmation_url': f"{getattr(settings, 'FRONTEND_CONFIRM_EMAIL_CHANGE_URL', 'http://localhost:3000/confirm-email-change')}?token={token}",
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'token': token,
                'expires_hours': getattr(settings, 'EMAIL_CHANGE_TIMEOUT_HOURS', 24)
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/email_change_confirmation.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': new_email,
                'title': f"Confirm email change - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [user.email], # Copia al email anterior
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/email_change_confirmation.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Email change confirmation sent successfully to {new_email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send email change confirmation to {new_email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending email change confirmation to {new_email}: {e}")
            return None

    def send_account_deactivation_notice(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la desactivación de la cuenta

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending account deactivation notice to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'reactivation_url': getattr(settings, 'FRONTEND_REACTIVATION_URL', 'http://localhost:3000/reactivate-account')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/account_deactivation_notice.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account deactivated - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/account_deactivation_notice.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Account deactivation notice sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send account deactivation notice to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending account deactivation notice to {user.email}: {e}")
            return None

    def send_account_reactivation_notice(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la reactivación de la cuenta

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending account reactivation notice to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'login_url': getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/account_reactivation_notice.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account reactivated - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/account_reactivation_notice.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Account reactivation notice sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send account reactivation notice to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending account reactivation notice to {user.email}: {e}")
            return None

    def send_account_deletion_notice(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la eliminación de la cuenta

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending account deletion notice to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/account_deletion_notice.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account deleted - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/account_deletion_notice.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Account deletion notice sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send account deletion notice to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending account deletion notice to {user.email}: {e}")
            return None

    def send_account_restoration_notice(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la restauración de la cuenta

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending account restoration notice to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'login_url': getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/account_restoration_notice.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account restored - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/account_restoration_notice.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Account restoration notice sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send account restoration notice to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending account restoration notice to {user.email}: {e}")
            return None

    def send_two_factor_setup_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la configuración de 2FA

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending 2FA setup notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'two_factor_url': getattr(settings, 'FRONTEND_TWO_FACTOR_URL', 'http://localhost:3000/two-factor')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/two_factor_setup_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Two-Factor Authentication Enabled - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/two_factor_setup_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"2FA setup notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send 2FA setup notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending 2FA setup notification to {user.email}: {e}")
            return None

    def send_two_factor_disabled_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la desactivación de 2FA

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending 2FA disabled notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/two_factor_disabled_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Two-Factor Authentication Disabled - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/two_factor_disabled_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"2FA disabled notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send 2FA disabled notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending 2FA disabled notification to {user.email}: {e}")
            return None

    def send_login_attempt_notification(self, user: User, ip_address: str, user_agent: str, success: bool) -> Optional[str]:
        """
        Envía un email notificando un intento de inicio de sesión

        Args:
            user (User): Instancia del modelo User
            ip_address (str): Dirección IP del intento
            user_agent (str): User agent del cliente
            success (bool): Indica si el intento fue exitoso

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending login attempt notification to {user.email} (success: {success})")
            
            # Preparar contexto
            context = {
                'user': user,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'success': success,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'login_url': getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login')
            }
            
            # Renderizar plantilla
            template_name = 'authentication/email/login_attempt_success.html' if success else 'authentication/email/login_attempt_failure.html'
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[{'Success' if success else 'Failure'}] Login attempt - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': template_name,
                'user_id': str(user.id) if user.id else None,
                'priority': 'high' if not success else 'normal' # Alta prioridad si falla
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Login attempt notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send login attempt notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending login attempt notification to {user.email}: {e}")
            return None

    def send_password_change_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando un cambio de contraseña

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending password change notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'login_url': getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/password_change_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Password changed - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/password_change_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Password change notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send password change notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending password change notification to {user.email}: {e}")
            return None

    def send_account_locked_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando que la cuenta ha sido bloqueada

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending account locked notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'unlock_url': getattr(settings, 'FRONTEND_UNLOCK_ACCOUNT_URL', 'http://localhost:3000/unlock-account')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/account_locked_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account locked - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/account_locked_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Account locked notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send account locked notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending account locked notification to {user.email}: {e}")
            return None

    def send_account_unlocked_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando que la cuenta ha sido desbloqueada

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending account unlocked notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'login_url': getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/account_unlocked_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account unlocked - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/account_unlocked_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Account unlocked notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send account unlocked notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending account unlocked notification to {user.email}: {e}")
            return None

    def send_suspension_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la suspensión de la cuenta

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending suspension notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'unsuspend_url': getattr(settings, 'FRONTEND_UNSUSPEND_ACCOUNT_URL', 'http://localhost:3000/unsuspend-account')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/suspension_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account suspended - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/suspension_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Suspension notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send suspension notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending suspension notification to {user.email}: {e}")
            return None

    def send_unsuspension_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la reactivación de la cuenta suspendida

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending unsuspension notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'login_url': getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/unsuspension_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account unsuspended - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/unsuspension_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Unsuspension notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send unsuspension notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending unsuspension notification to {user.email}: {e}")
            return None

    def send_ban_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando el baneo de la cuenta

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending ban notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'unban_url': getattr(settings, 'FRONTEND_UNBAN_ACCOUNT_URL', 'http://localhost:3000/unban-account')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/ban_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account banned - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/ban_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Ban notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send ban notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending ban notification to {user.email}: {e}")
            return None

    def send_unban_notification(self, user: User) -> Optional[str]:
        """
        Envía un email notificando la eliminación del baneo de la cuenta

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending unban notification to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'login_url': getattr(settings, 'FRONTEND_LOGIN_URL', 'http://localhost:3000/login')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/unban_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Account unbanned - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/unban_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Unban notification sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send unban notification to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending unban notification to {user.email}: {e}")
            return None

    def send_invitation_email(self, invitation: UserInvitation) -> Optional[str]:
        """
        Envía un email de invitación a un nuevo usuario

        Args:
            invitation (UserInvitation): Instancia del modelo UserInvitation

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending invitation email to {invitation.email}")
            
            # Preparar contexto
            context = {
                'invitation': invitation,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'accept_url': f"{getattr(settings, 'FRONTEND_INVITATION_ACCEPT_URL', 'http://localhost:3000/accept-invitation')}?token={invitation.token}",
                'decline_url': f"{getattr(settings, 'FRONTEND_INVITATION_DECLINE_URL', 'http://localhost:3000/decline-invitation')}?token={invitation.token}",
                'expires_at': invitation.expires_at.strftime('%Y-%m-%d %H:%M:%S') if invitation.expires_at else 'N/A'
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/invitation_email.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': invitation.email,
                'title': f"You've been invited to join {context['site_name']}!",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/invitation_email.html',
                'user_id': str(invitation.invited_by.id) if invitation.invited_by else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Invitation email sent successfully to {invitation.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send invitation email to {invitation.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending invitation email to {invitation.email}: {e}")
            return None

    def send_invitation_accepted_email(self, invitation: UserInvitation) -> Optional[str]:
        """
        Envía un email notificando que una invitación ha sido aceptada

        Args:
            invitation (UserInvitation): Instancia del modelo UserInvitation

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending invitation accepted email to {invitation.invited_by.email}")
            
            # Preparar contexto
            context = {
                'invitation': invitation,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'invitee_email': invitation.email,
                'accepted_at': invitation.accepted_at.strftime('%Y-%m-%d %H:%M:%S') if invitation.accepted_at else 'N/A'
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/invitation_accepted_email.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': invitation.invited_by.email,
                'title': f"Invitation accepted - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/invitation_accepted_email.html',
                'user_id': str(invitation.invited_by.id) if invitation.invited_by else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Invitation accepted email sent successfully to {invitation.invited_by.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send invitation accepted email to {invitation.invited_by.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending invitation accepted email to {invitation.invited_by.email}: {e}")
            return None

    def send_invitation_declined_email(self, invitation: UserInvitation) -> Optional[str]:
        """
        Envía un email notificando que una invitación ha sido rechazada

        Args:
            invitation (UserInvitation): Instancia del modelo UserInvitation

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending invitation declined email to {invitation.invited_by.email}")
            
            # Preparar contexto
            context = {
                'invitation': invitation,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'invitee_email': invitation.email,
                'declined_at': invitation.declined_at.strftime('%Y-%m-%d %H:%M:%S') if invitation.declined_at else 'N/A'
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/invitation_declined_email.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': invitation.invited_by.email,
                'title': f"Invitation declined - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/invitation_declined_email.html',
                'user_id': str(invitation.invited_by.id) if invitation.invited_by else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Invitation declined email sent successfully to {invitation.invited_by.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send invitation declined email to {invitation.invited_by.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending invitation declined email to {invitation.invited_by.email}: {e}")
            return None

    def send_invitation_expired_email(self, invitation: UserInvitation) -> Optional[str]:
        """
        Envía un email notificando que una invitación ha expirado

        Args:
            invitation (UserInvitation): Instancia del modelo UserInvitation

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending invitation expired email to {invitation.email}")
            
            # Preparar contexto
            context = {
                'invitation': invitation,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'expired_at': invitation.expires_at.strftime('%Y-%m-%d %H:%M:%S') if invitation.expires_at else 'N/A'
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/invitation_expired_email.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': invitation.email,
                'title': f"Invitation expired - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/invitation_expired_email.html',
                'user_id': str(invitation.invited_by.id) if invitation.invited_by else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Invitation expired email sent successfully to {invitation.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send invitation expired email to {invitation.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending invitation expired email to {invitation.email}: {e}")
            return None

    def send_invitation_revoked_email(self, invitation: UserInvitation) -> Optional[str]:
        """
        Envía un email notificando que una invitación ha sido revocada

        Args:
            invitation (UserInvitation): Instancia del modelo UserInvitation

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending invitation revoked email to {invitation.email}")
            
            # Preparar contexto
            context = {
                'invitation': invitation,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'revoked_at': invitation.revoked_at.strftime('%Y-%m-%d %H:%M:%S') if invitation.revoked_at else 'N/A'
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/invitation_revoked_email.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': invitation.email,
                'title': f"Invitation revoked - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/invitation_revoked_email.html',
                'user_id': str(invitation.invited_by.id) if invitation.invited_by else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Invitation revoked email sent successfully to {invitation.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send invitation revoked email to {invitation.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending invitation revoked email to {invitation.email}: {e}")
            return None

    def send_invitation_reminder_email(self, invitation: UserInvitation) -> Optional[str]:
        """
        Envía un email recordatorio de una invitación pendiente

        Args:
            invitation (UserInvitation): Instancia del modelo UserInvitation

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending invitation reminder email to {invitation.email}")
            
            # Preparar contexto
            context = {
                'invitation': invitation,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'accept_url': f"{getattr(settings, 'FRONTEND_INVITATION_ACCEPT_URL', 'http://localhost:3000/accept-invitation')}?token={invitation.token}",
                'decline_url': f"{getattr(settings, 'FRONTEND_INVITATION_DECLINE_URL', 'http://localhost:3000/decline-invitation')}?token={invitation.token}",
                'expires_at': invitation.expires_at.strftime('%Y-%m-%d %H:%M:%S') if invitation.expires_at else 'N/A'
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/invitation_reminder_email.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': invitation.email,
                'title': f"Reminder: You've been invited to join {context['site_name']}!",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/invitation_reminder_email.html',
                'user_id': str(invitation.invited_by.id) if invitation.invited_by else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Invitation reminder email sent successfully to {invitation.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send invitation reminder email to {invitation.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending invitation reminder email to {invitation.email}: {e}")
            return None

    def send_security_alert(self, user: User, alert_type: str, message: str) -> Optional[str]:
        """
        Envía un email de alerta de seguridad

        Args:
            user (User): Instancia del modelo User
            alert_type (str): Tipo de alerta de seguridad
            message (str): Mensaje de la alerta

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending security alert email to {user.email} (type: {alert_type})")
            
            # Preparar contexto
            context = {
                'user': user,
                'alert_type': alert_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'security_url': getattr(settings, 'FRONTEND_SECURITY_URL', 'http://localhost:3000/security')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/security_alert.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[SECURITY ALERT] {alert_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/security_alert.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Security alert email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send security alert email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending security alert email to {user.email}: {e}")
            return None

    def send_compliance_notification(self, user: User, compliance_type: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de cumplimiento

        Args:
            user (User): Instancia del modelo User
            compliance_type (str): Tipo de cumplimiento
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending compliance notification email to {user.email} (type: {compliance_type})")
            
            # Preparar contexto
            context = {
                'user': user,
                'compliance_type': compliance_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'compliance_url': getattr(settings, 'FRONTEND_COMPLIANCE_URL', 'http://localhost:3000/compliance')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/compliance_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[COMPLIANCE] {compliance_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/compliance_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Compliance notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send compliance notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending compliance notification email to {user.email}: {e}")
            return None

    def send_privacy_policy_update(self, user: User) -> Optional[str]:
        """
        Envía un email notificando una actualización de la política de privacidad

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending privacy policy update email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'privacy_url': getattr(settings, 'FRONTEND_PRIVACY_URL', 'http://localhost:3000/privacy')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/privacy_policy_update.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Privacy Policy Updated - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/privacy_policy_update.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Privacy policy update email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send privacy policy update email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending privacy policy update email to {user.email}: {e}")
            return None

    def send_terms_of_service_update(self, user: User) -> Optional[str]:
        """
        Envía un email notificando una actualización de los términos de servicio

        Args:
            user (User): Instancia del modelo User

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending terms of service update email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'tos_url': getattr(settings, 'FRONTEND_TOS_URL', 'http://localhost:3000/terms-of-service')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/terms_of_service_update.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Terms of Service Updated - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/terms_of_service_update.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Terms of service update email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send terms of service update email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending terms of service update email to {user.email}: {e}")
            return None

    def send_data_export_ready(self, user: User, export_id: str, download_url: str) -> Optional[str]:
        """
        Envía un email notificando que una exportación de datos está lista

        Args:
            user (User): Instancia del modelo User
            export_id (str): ID de la exportación
            download_url (str): URL para descargar la exportación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending data export ready email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'export_id': export_id,
                'download_url': download_url,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/data_export_ready.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Data Export Ready - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/data_export_ready.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Data export ready email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send data export ready email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending data export ready email to {user.email}: {e}")
            return None

    def send_data_import_completed(self, user: User, import_id: str, report_url: str) -> Optional[str]:
        """
        Envía un email notificando que una importación de datos se ha completado

        Args:
            user (User): Instancia del modelo User
            import_id (str): ID de la importación
            report_url (str): URL para ver el informe de la importación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending data import completed email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'import_id': import_id,
                'report_url': report_url,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/data_import_completed.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"Data Import Completed - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/data_import_completed.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Data import completed email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send data import completed email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending data import completed email to {user.email}: {e}")
            return None

    def send_data_import_failed(self, user: User, import_id: str, error_message: str) -> Optional[str]:
        """
        Envía un email notificando que una importación de datos ha fallado

        Args:
            user (User): Instancia del modelo User
            import_id (str): ID de la importación
            error_message (str): Mensaje de error de la importación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending data import failed email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'import_id': import_id,
                'error_message': error_message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/data_import_failed.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[ERROR] Data Import Failed - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/data_import_failed.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Data import failed email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send data import failed email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending data import failed email to {user.email}: {e}")
            return None

    def send_audit_notification(self, user: User, audit_id: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de auditoría

        Args:
            user (User): Instancia del modelo User
            audit_id (str): ID de la auditoría
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending audit notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'audit_id': audit_id,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'audit_url': getattr(settings, 'FRONTEND_AUDIT_URL', 'http://localhost:3000/audit')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/audit_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[AUDIT] {audit_id} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/audit_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Audit notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send audit notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending audit notification email to {user.email}: {e}")
            return None

    def send_report_notification(self, user: User, report_id: str, report_title: str, download_url: str) -> Optional[str]:
        """
        Envía un email de notificación de informe

        Args:
            user (User): Instancia del modelo User
            report_id (str): ID del informe
            report_title (str): Título del informe
            download_url (str): URL para descargar el informe

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending report notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'report_id': report_id,
                'report_title': report_title,
                'download_url': download_url,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/report_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[REPORT] {report_title} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/report_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Report notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send report notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending report notification email to {user.email}: {e}")
            return None

    def send_alert_notification(self, user: User, alert_id: str, alert_title: str, severity: str) -> Optional[str]:
        """
        Envía un email de notificación de alerta

        Args:
            user (User): Instancia del modelo User
            alert_id (str): ID de la alerta
            alert_title (str): Título de la alerta
            severity (str): Severidad de la alerta

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending alert notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'alert_id': alert_id,
                'alert_title': alert_title,
                'severity': severity,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'alert_url': getattr(settings, 'FRONTEND_ALERT_URL', 'http://localhost:3000/alerts')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/alert_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[{severity.upper()}] {alert_title} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/alert_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high' if severity in ['critical', 'high'] else 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Alert notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send alert notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending alert notification email to {user.email}: {e}")
            return None

    def send_notification_notification(self, user: User, notification_id: str, notification_title: str) -> Optional[str]:
        """
        Envía un email de notificación de notificación

        Args:
            user (User): Instancia del modelo User
            notification_id (str): ID de la notificación
            notification_title (str): Título de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending notification notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'notification_id': notification_id,
                'notification_title': notification_title,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'notification_url': getattr(settings, 'FRONTEND_NOTIFICATION_URL', 'http://localhost:3000/notifications')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/notification_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[NOTIFICATION] {notification_title} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/notification_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Notification notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send notification notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending notification notification email to {user.email}: {e}")
            return None

    def send_user_activity_notification(self, user: User, activity_type: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de actividad de usuario

        Args:
            user (User): Instancia del modelo User
            activity_type (str): Tipo de actividad
            message (str): Mensaje de la actividad

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending user activity notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'activity_type': activity_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'activity_url': getattr(settings, 'FRONTEND_ACTIVITY_URL', 'http://localhost:3000/activity')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/user_activity_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[ACTIVITY] {activity_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/user_activity_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"User activity notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send user activity notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending user activity notification email to {user.email}: {e}")
            return None

    def send_system_health_notification(self, user: User, health_status: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de salud del sistema

        Args:
            user (User): Instancia del modelo User
            health_status (str): Estado de salud del sistema
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending system health notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'health_status': health_status,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'health_url': getattr(settings, 'FRONTEND_HEALTH_URL', 'http://localhost:3000/health')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/system_health_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[HEALTH] {health_status} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/system_health_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high' if health_status in ['critical', 'error'] else 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"System health notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send system health notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending system health notification email to {user.email}: {e}")
            return None

    def send_data_quality_notification(self, user: User, quality_score: float, message: str) -> Optional[str]:
        """
        Envía un email de notificación de calidad de datos

        Args:
            user (User): Instancia del modelo User
            quality_score (float): Puntaje de calidad de datos
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending data quality notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'quality_score': quality_score,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'quality_url': getattr(settings, 'FRONTEND_QUALITY_URL', 'http://localhost:3000/quality')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/data_quality_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[QUALITY] Data Quality Score: {quality_score:.2f} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/data_quality_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high' if quality_score < 0.7 else 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Data quality notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send data quality notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending data quality notification email to {user.email}: {e}")
            return None

    def send_change_detection_notification(self, user: User, change_type: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de detección de cambios

        Args:
            user (User): Instancia del modelo User
            change_type (str): Tipo de cambio detectado
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending change detection notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'change_type': change_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'change_url': getattr(settings, 'FRONTEND_CHANGE_URL', 'http://localhost:3000/change')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/change_detection_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[CHANGE] {change_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/change_detection_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high' if change_type in ['critical', 'high'] else 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Change detection notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send change detection notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending change detection notification email to {user.email}: {e}")
            return None

    def send_gis_service_interaction_notification(self, user: User, service_name: str, interaction_type: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de interacción con servicio GIS

        Args:
            user (User): Instancia del modelo User
            service_name (str): Nombre del servicio GIS
            interaction_type (str): Tipo de interacción
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending GIS service interaction notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'service_name': service_name,
                'interaction_type': interaction_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'service_url': getattr(settings, 'FRONTEND_SERVICE_URL', 'http://localhost:3000/services')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/gis_service_interaction_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[GIS] {service_name} - {interaction_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/gis_service_interaction_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"GIS service interaction notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send GIS service interaction notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending GIS service interaction notification email to {user.email}: {e}")
            return None

    def send_authentication_notification(self, user: User, auth_type: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de autenticación

        Args:
            user (User): Instancia del modelo User
            auth_type (str): Tipo de autenticación
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending authentication notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'auth_type': auth_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'auth_url': getattr(settings, 'FRONTEND_AUTH_URL', 'http://localhost:3000/auth')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/authentication_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[AUTH] {auth_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/authentication_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high' if auth_type in ['login_failure', 'password_reset'] else 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Authentication notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send authentication notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending authentication notification email to {user.email}: {e}")
            return None

    def send_authorization_notification(self, user: User, authz_type: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de autorización

        Args:
            user (User): Instancia del modelo User
            authz_type (str): Tipo de autorización
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending authorization notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'authz_type': authz_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'authz_url': getattr(settings, 'FRONTEND_AUTHZ_URL', 'http://localhost:3000/authz')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/authorization_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[AUTHZ] {authz_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/authorization_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high' if authz_type in ['denied_access', 'restricted_access'] else 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Authorization notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send authorization notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending authorization notification email to {user.email}: {e}")
            return None

    def send_error_handling_notification(self, user: User, error_type: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de manejo de errores

        Args:
            user (User): Instancia del modelo User
            error_type (str): Tipo de error
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending error handling notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'error_type': error_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'error_url': getattr(settings, 'FRONTEND_ERROR_URL', 'http://localhost:3000/errors')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/error_handling_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[ERROR] {error_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/error_handling_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Error handling notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send error handling notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending error handling notification email to {user.email}: {e}")
            return None

    def send_performance_monitoring_notification(self, user: User, perf_type: str, message: str) -> Optional[str]:
        """
        Envía un email de notificación de monitoreo de rendimiento

        Args:
            user (User): Instancia del modelo User
            perf_type (str): Tipo de monitoreo de rendimiento
            message (str): Mensaje de la notificación

        Returns:
            Optional[str]: ID de la notificación de email creada, o None si falla
        """
        try:
            self.logger.info(f"Sending performance monitoring notification email to {user.email}")
            
            # Preparar contexto
            context = {
                'user': user,
                'perf_type': perf_type,
                'message': message,
                'site_name': getattr(settings, 'SITE_NAME', 'SMGI Backend'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@smgi.iiap.edu.pe'),
                'perf_url': getattr(settings, 'FRONTEND_PERF_URL', 'http://localhost:3000/performance')
            }
            
            # Renderizar plantilla
            html_content = render_to_string('authentication/email/performance_monitoring_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Preparar datos para el canal de email
            email_data = {
                'recipient': user.email,
                'title': f"[PERF] {perf_type} - {context['site_name']}",
                'message': text_content,
                'html_message': html_content,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smgi.iiap.edu.pe'),
                'cc': [],
                'bcc': [],
                'attachments': [],
                'context': context,
                'template_name': 'authentication/email/performance_monitoring_notification.html',
                'user_id': str(user.id) if user.id else None,
                'priority': 'high' if perf_type in ['slow_query', 'high_cpu', 'high_memory'] else 'normal'
            }
            
            # Enviar email usando el canal
            result = self.email_channel.send(email_data)
            
            if result.get('success'):
                self.logger.info(f"Performance monitoring notification email sent successfully to {user.email}")
                return result.get('email_notification_id')
            else:
                self.logger.error(f"Failed to send performance monitoring notification email to {user.email}: {result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending performance monitoring notification email to {user.email}: {e}")
            return None
