"""
Utility functions for Users app.
"""
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from typing import Optional
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def generate_username_from_email(email: str) -> str:
    """
    Generate a username from an email address.
    
    Args:
        email: Email address
    
    Returns:
        str: Generated username
    """
    username = email.split('@')[0]
    
    # Ensure uniqueness
    if User.objects.filter(username=username).exists():
        username = f"{username}_{get_random_string(4)}"
    
    return username


def send_verification_email(user):
    """
    Send verification email to user.
    
    Args:
        user: User instance
    
    Returns:
        bool: True if email was sent successfully
    """
    try:
        # Generate verification token
        token = get_random_string(32)
        
        # TODO: Store token in database or cache
        
        # Send email
        subject = 'Verifica tu cuenta SMGI'
        message = f"""
Hola {user.first_name or user.username},

Gracias por registrarte en SMGI.

Por favor verifica tu cuenta haciendo clic en el siguiente enlace:
{settings.FRONTEND_URL}/verify-email/{token}

Si no creaste esta cuenta, puedes ignorar este email.

Saludos,
Equipo SMGI
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        return False


def send_password_reset_email(user, reset_link: str):
    """
    Send password reset email to user.
    
    Args:
        user: User instance
        reset_link: Password reset link
    
    Returns:
        bool: True if email was sent successfully
    """
    try:
        subject = 'Restablecer contraseña SMGI'
        message = f"""
Hola {user.first_name or user.username},

Recibimos una solicitud para restablecer tu contraseña.

Por favor haz clic en el siguiente enlace para establecer una nueva contraseña:
{reset_link}

Este enlace expirará en 24 horas.

Si no solicitaste restablecer tu contraseña, puedes ignorar este email.

Saludos,
Equipo SMGI
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending password reset email: {str(e)}")
        return False


def is_strong_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Check if a password is strong enough.
    
    Args:
        password: Password to check
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    if not any(c.isupper() for c in password):
        return False, "La contraseña debe contener al menos una mayúscula"
    
    if not any(c.islower() for c in password):
        return False, "La contraseña debe contener al menos una minúscula"
    
    if not any(c.isdigit() for c in password):
        return False, "La contraseña debe contener al menos un número"
    
    return True, None


def get_user_stats(user):
    """
    Get statistics for a user.
    
    Args:
        user: User instance
    
    Returns:
        dict: User statistics
    """
    stats = {
        'layers_created': 0,
        'analyses_completed': 0,
        'alerts_created': 0,
        'projects_owned': 0,
    }
    
    try:
        from apps.geodata.models import Layer
        stats['layers_created'] = Layer.objects.filter(created_by=user).count()
    except:
        pass
    
    try:
        from apps.agents.models import AgentExecution
        stats['analyses_completed'] = AgentExecution.objects.filter(
            created_by=user,
            status='completed'
        ).count()
    except:
        pass
    
    try:
        from apps.alerts.models import Alert
        stats['alerts_created'] = Alert.objects.filter(created_by=user).count()
    except:
        pass
    
    try:
        from apps.monitoring.models import MonitoringProject
        stats['projects_owned'] = MonitoringProject.objects.filter(created_by=user).count()
    except:
        pass
    
    return stats


def check_user_permissions(user, action: str) -> bool:
    """
    Check if user has permission to perform an action.
    
    Args:
        user: User instance
        action: Action to check (e.g., 'create_layer', 'run_analysis')
    
    Returns:
        bool: True if user has permission
    """
    if user.is_staff:
        return True
    
    # Map actions to required roles
    role_requirements = {
        'create_layer': ['viewer', 'analyst', 'developer', 'admin'],
        'run_analysis': ['analyst', 'developer', 'admin'],
        'create_agent': ['developer', 'admin'],
        'manage_users': ['admin'],
    }
    
    required_roles = role_requirements.get(action, [])
    return user.role in required_roles


def sanitize_user_input(text: str, max_length: int = 255) -> str:
    """
    Sanitize user input text.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length
    
    Returns:
        str: Sanitized text
    """
    import re
    
    # Remove potentially harmful characters
    text = re.sub(r'[<>\"\'&]', '', text)
    
    # Trim whitespace
    text = text.strip()
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def format_user_display_name(user) -> str:
    """
    Get formatted display name for a user.
    
    Args:
        user: User instance
    
    Returns:
        str: Formatted display name
    """
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    else:
        return user.username
