"""
Celery tasks for Users app.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import User
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_welcome_email(user_id):
    """
    Send welcome email to new user.
    
    Args:
        user_id: ID of the user
    """
    try:
        user = User.objects.get(id=user_id)
        subject = 'Bienvenido a SMGI'
        message = f"""
        Hola {user.full_name or user.username},
        
        ¡Bienvenido al Sistema de Monitoreo Geoespacial Inteligente!
        
        Tu cuenta ha sido creada exitosamente.
        
        Saludos,
        El equipo de SMGI
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to {user.email}")
        return f"Email sent to {user.email}"
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return f"User not found"
    except Exception as e:
        logger.error(f"Error sending welcome email: {str(e)}")
        raise


@shared_task
def send_password_reset_email(user_id, reset_token):
    """
    Send password reset email.
    
    Args:
        user_id: ID of the user
        reset_token: Password reset token
    """
    try:
        user = User.objects.get(id=user_id)
        subject = 'Restablecer contraseña - SMGI'
        message = f"""
        Hola {user.full_name or user.username},
        
        Has solicitado restablecer tu contraseña.
        
        Token de restablecimiento: {reset_token}
        
        Si no solicitaste este cambio, ignora este mensaje.
        
        Saludos,
        El equipo de SMGI
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user.email}")
        return f"Email sent to {user.email}"
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return f"User not found"
    except Exception as e:
        logger.error(f"Error sending password reset email: {str(e)}")
        raise


@shared_task
def cleanup_unverified_users():
    """
    Delete unverified users older than 7 days.
    Runs daily via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    threshold_date = timezone.now() - timedelta(days=7)
    deleted_users = User.objects.filter(
        is_verified=False,
        created_at__lt=threshold_date
    ).delete()
    
    logger.info(f"Deleted {deleted_users[0]} unverified users")
    return f"Deleted {deleted_users[0]} users"
