# apps/authentication/tokens.py
"""
SMGI Backend - Authentication Tokens
Sistema de Monitoreo Geoespacial Inteligente
Gestión de tokens de autenticación y autorización
"""
import secrets
import string
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.authentication.models import User, PasswordResetToken, EmailVerificationToken

logger = logging.getLogger('apps.authentication.tokens')


class TokenGeneratorError(Exception):
    """Excepción base para errores en generadores de tokens"""
    pass


class InvalidTokenError(TokenGeneratorError):
    """Excepción para tokens inválidos o expirados"""
    pass


class TokenGenerator:
    """
    Generador base de tokens seguros para autenticación y autorización
    """
    
    def __init__(self, token_length: int = 32, expiry_hours: int = 24):
        """
        Inicializa el generador de tokens

        Args:
            token_length (int): Longitud del token generado. Por defecto 32.
            expiry_hours (int): Horas hasta la expiración del token. Por defecto 24.
        """
        self.token_length = token_length
        self.expiry_hours = expiry_hours
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    def generate_secure_token(self) -> str:
        """
        Genera un token seguro y único usando secrets.token_urlsafe

        Returns:
            str: Token seguro generado
        """
        self.logger.debug(f"Generating secure token of length {self.token_length}")
        try:
            # Generar token URL-safe usando secrets (más seguro que random)
            token = secrets.token_urlsafe(self.token_length)
            self.logger.info(f"Secure token generated successfully")
            return token
        except Exception as e:
            self.logger.error(f"Error generating secure token: {e}")
            raise TokenGeneratorError(f"Failed to generate secure token: {e}")

    def generate_numeric_token(self, length: int = 6) -> str:
        """
        Genera un token numérico seguro (útil para códigos de verificación SMS 2FA)

        Args:
            length (int): Longitud del token numérico. Por defecto 6.

        Returns:
            str: Token numérico generado
        """
        self.logger.debug(f"Generating numeric token of length {length}")
        try:
            # Generar token numérico usando secrets.choice
            alphabet = string.digits
            token = ''.join(secrets.choice(alphabet) for _ in range(length))
            self.logger.info(f"Numeric token generated successfully")
            return token
        except Exception as e:
            self.logger.error(f"Error generating numeric token: {e}")
            raise TokenGeneratorError(f"Failed to generate numeric token: {e}")

    def generate_alphanumeric_token(self, length: int = 8) -> str:
        """
        Genera un token alfanumérico seguro

        Args:
            length (int): Longitud del token alfanumérico. Por defecto 8.

        Returns:
            str: Token alfanumérico generado
        """
        self.logger.debug(f"Generating alphanumeric token of length {length}")
        try:
            # Generar token alfanumérico usando secrets.choice
            alphabet = string.ascii_letters + string.digits
            token = ''.join(secrets.choice(alphabet) for _ in range(length))
            self.logger.info(f"Alphanumeric token generated successfully")
            return token
        except Exception as e:
            self.logger.error(f"Error generating alphanumeric token: {e}")
            raise TokenGeneratorError(f"Failed to generate alphanumeric token: {e}")

    def calculate_expiry_time(self, hours: Optional[int] = None) -> timezone.datetime:
        """
        Calcula la fecha y hora de expiración del token

        Args:
            hours (Optional[int]): Horas hasta la expiración. Si es None, usa self.expiry_hours.

        Returns:
            timezone.datetime: Fecha y hora de expiración
        """
        hours = hours or self.expiry_hours
        self.logger.debug(f"Calculating expiry time for {hours} hours")
        try:
            expiry_time = timezone.now() + timedelta(hours=hours)
            self.logger.info(f"Expiry time calculated: {expiry_time}")
            return expiry_time
        except Exception as e:
            self.logger.error(f"Error calculating expiry time: {e}")
            raise TokenGeneratorError(f"Failed to calculate expiry time: {e}")

    def hash_token(self, token: str) -> str:
        """
        Hashea un token para almacenamiento seguro

        Args:
            token (str): Token a hashear

        Returns:
            str: Hash SHA-256 del token
        """
        self.logger.debug("Hashing token for secure storage")
        try:
            # Hashear token usando SHA-256 para almacenamiento seguro
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            self.logger.info("Token hashed successfully")
            return token_hash
        except Exception as e:
            self.logger.error(f"Error hashing token: {e}")
            raise TokenGeneratorError(f"Failed to hash token: {e}")

    def verify_token(self, token: str, token_hash: str) -> bool:
        """
        Verifica si un token coincide con su hash

        Args:
            token (str): Token a verificar
            token_hash (str): Hash del token almacenado

        Returns:
            bool: True si el token es válido, False en caso contrario
        """
        self.logger.debug("Verifying token against stored hash")
        try:
            # Hashear el token proporcionado y comparar con el hash almacenado
            provided_hash = self.hash_token(token)
            is_valid = provided_hash == token_hash
            self.logger.info(f"Token verification result: {is_valid}")
            return is_valid
        except Exception as e:
            self.logger.error(f"Error verifying token: {e}")
            return False

    def is_token_expired(self, token_instance: Any) -> bool:
        """
        Verifica si un token (instancia de modelo) ha expirado

        Args:
            token_instance (Any): Instancia del modelo de token (PasswordResetToken, EmailVerificationToken, etc.)

        Returns:
            bool: True si el token ha expirado, False en caso contrario
        """
        self.logger.debug(f"Checking if token {token_instance.id} has expired")
        try:
            if not hasattr(token_instance, 'expires_at') or not token_instance.expires_at:
                self.logger.warning(f"Token {token_instance.id} has no expiry time")
                return True
            
            is_expired = timezone.now() > token_instance.expires_at
            self.logger.info(f"Token {token_instance.id} expiry check: {is_expired}")
            return is_expired
        except Exception as e:
            self.logger.error(f"Error checking token expiry: {e}")
            return True # Asumir expirado en caso de error

    def invalidate_token(self, token_instance: Any) -> bool:
        """
        Invalida un token (instancia de modelo)

        Args:
            token_instance (Any): Instancia del modelo de token

        Returns:
            bool: True si el token fue invalidado, False en caso contrario
        """
        self.logger.debug(f"Invalidating token {token_instance.id}")
        try:
            if not hasattr(token_instance, 'is_valid') or not token_instance.is_valid:
                self.logger.info(f"Token {token_instance.id} is already invalid")
                return True
            
            token_instance.is_valid = False
            token_instance.save(update_fields=['is_valid'])
            self.logger.info(f"Token {token_instance.id} invalidated successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error invalidating token {token_instance.id}: {e}")
            return False

    def cleanup_expired_tokens(self, token_model: Any) -> int:
        """
        Limpia tokens expirados de un modelo específico

        Args:
            token_model (Any): Clase del modelo de token (PasswordResetToken, EmailVerificationToken, etc.)

        Returns:
            int: Número de tokens eliminados
        """
        self.logger.debug(f"Cleaning up expired tokens for model {token_model.__name__}")
        try:
            # Eliminar tokens expirados
            expired_tokens = token_model.objects.filter(
                expires_at__lt=timezone.now(),
                is_valid=True
            )
            deleted_count = expired_tokens.count()
            
            if deleted_count > 0:
                expired_tokens.update(is_valid=False)
                self.logger.info(f"Cleaned up {deleted_count} expired tokens for model {token_model.__name__}")
            
            return deleted_count
        except Exception as e:
            self.logger.error(f"Error cleaning up expired tokens for model {token_model.__name__}: {e}")
            return 0


class PasswordResetTokenGenerator(TokenGenerator):
    """
    Generador específico para tokens de restablecimiento de contraseña
    """
    
    def __init__(self, token_length: int = 32, expiry_hours: int = 24):
        """
        Inicializa el generador de tokens de restablecimiento de contraseña

        Args:
            token_length (int): Longitud del token generado. Por defecto 32.
            expiry_hours (int): Horas hasta la expiración del token. Por defecto 24.
        """
        super().__init__(token_length, expiry_hours)
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    def create_token(self, user: User) -> PasswordResetToken:
        """
        Crea un nuevo token de restablecimiento de contraseña para un usuario

        Args:
            user (User): Instancia del modelo User

        Returns:
            PasswordResetToken: Instancia del modelo PasswordResetToken creada
        """
        self.logger.info(f"Creating password reset token for user {user.email}")
        try:
            # Generar token seguro
            token = self.generate_secure_token()
            
            # Hashear token para almacenamiento seguro
            token_hash = self.hash_token(token)
            
            # Calcular fecha de expiración
            expires_at = self.calculate_expiry_time()
            
            # Crear instancia de PasswordResetToken
            password_reset_token = PasswordResetToken.objects.create(
                user=user,
                token_hash=token_hash,
                expires_at=expires_at,
                is_valid=True
            )
            
            self.logger.info(f"Password reset token created successfully for user {user.email}")
            return password_reset_token
        except Exception as e:
            self.logger.error(f"Error creating password reset token for user {user.email}: {e}")
            raise TokenGeneratorError(f"Failed to create password reset token: {e}")

    def verify_and_invalidate_token(self, user: User, token: str) -> bool:
        """
        Verifica si un token de restablecimiento de contraseña es válido y lo invalida

        Args:
            user (User): Instancia del modelo User
            token (str): Token a verificar

        Returns:
            bool: True si el token es válido, False en caso contrario
        """
        self.logger.info(f"Verifying and invalidating password reset token for user {user.email}")
        try:
            # Buscar token válido para el usuario
            try:
                password_reset_token = PasswordResetToken.objects.get(
                    user=user,
                    is_valid=True
                )
            except PasswordResetToken.DoesNotExist:
                self.logger.warning(f"No valid password reset token found for user {user.email}")
                return False
            
            # Verificar si el token ha expirado
            if self.is_token_expired(password_reset_token):
                self.logger.warning(f"Password reset token for user {user.email} has expired")
                password_reset_token.is_valid = False
                password_reset_token.save(update_fields=['is_valid'])
                return False
            
            # Verificar si el token coincide
            if not self.verify_token(token, password_reset_token.token_hash):
                self.logger.warning(f"Invalid password reset token provided for user {user.email}")
                return False
            
            # Invalidar token después de usarlo (one-time use)
            self.invalidate_token(password_reset_token)
            
            self.logger.info(f"Password reset token verified and invalidated for user {user.email}")
            return True
        except Exception as e:
            self.logger.error(f"Error verifying and invalidating password reset token for user {user.email}: {e}")
            return False


class EmailVerificationTokenGenerator(TokenGenerator):
    """
    Generador específico para tokens de verificación de email
    """
    
    def __init__(self, token_length: int = 32, expiry_hours: int = 24):
        """
        Inicializa el generador de tokens de verificación de email

        Args:
            token_length (int): Longitud del token generado. Por defecto 32.
            expiry_hours (int): Horas hasta la expiración del token. Por defecto 24.
        """
        super().__init__(token_length, expiry_hours)
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    def create_token(self, user: User) -> EmailVerificationToken:
        """
        Crea un nuevo token de verificación de email para un usuario

        Args:
            user (User): Instancia del modelo User

        Returns:
            EmailVerificationToken: Instancia del modelo EmailVerificationToken creada
        """
        self.logger.info(f"Creating email verification token for user {user.email}")
        try:
            # Generar token seguro
            token = self.generate_secure_token()
            
            # Hashear token para almacenamiento seguro
            token_hash = self.hash_token(token)
            
            # Calcular fecha de expiración
            expires_at = self.calculate_expiry_time()
            
            # Crear instancia de EmailVerificationToken
            email_verification_token = EmailVerificationToken.objects.create(
                user=user,
                email=user.email,
                token_hash=token_hash,
                expires_at=expires_at,
                is_valid=True
            )
            
            self.logger.info(f"Email verification token created successfully for user {user.email}")
            return email_verification_token
        except Exception as e:
            self.logger.error(f"Error creating email verification token for user {user.email}: {e}")
            raise TokenGeneratorError(f"Failed to create email verification token: {e}")

    def verify_and_invalidate_token(self, user: User, token: str) -> bool:
        """
        Verifica si un token de verificación de email es válido y lo invalida

        Args:
            user (User): Instancia del modelo User
            token (str): Token a verificar

        Returns:
            bool: True si el token es válido, False en caso contrario
        """
        self.logger.info(f"Verifying and invalidating email verification token for user {user.email}")
        try:
            # Buscar token válido para el usuario y email
            try:
                email_verification_token = EmailVerificationToken.objects.get(
                    user=user,
                    email=user.email,
                    is_valid=True
                )
            except EmailVerificationToken.DoesNotExist:
                self.logger.warning(f"No valid email verification token found for user {user.email}")
                return False
            
            # Verificar si el token ha expirado
            if self.is_token_expired(email_verification_token):
                self.logger.warning(f"Email verification token for user {user.email} has expired")
                email_verification_token.is_valid = False
                email_verification_token.save(update_fields=['is_valid'])
                return False
            
            # Verificar si el token coincide
            if not self.verify_token(token, email_verification_token.token_hash):
                self.logger.warning(f"Invalid email verification token provided for user {user.email}")
                return False
            
            # Invalidar token después de usarlo (one-time use)
            self.invalidate_token(email_verification_token)
            
            self.logger.info(f"Email verification token verified and invalidated for user {user.email}")
            return True
        except Exception as e:
            self.logger.error(f"Error verifying and invalidating email verification token for user {user.email}: {e}")
            return False


class TwoFactorTokenGenerator(TokenGenerator):
    """
    Generador específico para tokens de autenticación de dos factores (2FA)
    """
    
    def __init__(self, token_length: int = 6, expiry_minutes: int = 5):
        """
        Inicializa el generador de tokens de 2FA

        Args:
            token_length (int): Longitud del token generado. Por defecto 6 (numérico).
            expiry_minutes (int): Minutos hasta la expiración del token. Por defecto 5.
        """
        super().__init__(token_length, expiry_minutes)
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    def generate_2fa_token(self) -> str:
        """
        Genera un token numérico de 6 dígitos para 2FA

        Returns:
            str: Token numérico de 6 dígitos
        """
        self.logger.debug("Generating 2FA token")
        try:
            # Generar token numérico de 6 dígitos
            token = self.generate_numeric_token(length=6)
            self.logger.info(f"2FA token generated: {token}")
            return token
        except Exception as e:
            self.logger.error(f"Error generating 2FA token: {e}")
            raise TokenGeneratorError(f"Failed to generate 2FA token: {e}")

    def verify_2fa_token(self, user: User, token: str) -> bool:
        """
        Verifica si un token de 2FA es válido para un usuario

        Args:
            user (User): Instancia del modelo User
            token (str): Token de 2FA a verificar

        Returns:
            bool: True si el token es válido, False en caso contrario
        """
        self.logger.info(f"Verifying 2FA token for user {user.email}")
        try:
            # Obtener el secreto TOTP del usuario
            try:
                totp_secret = user.two_factor_secrets.get(is_active=True)
            except TwoFactorSecret.DoesNotExist:
                self.logger.warning(f"No active TOTP secret found for user {user.email}")
                return False
            
            # Verificar token usando pyotp (biblioteca de 2FA)
            import pyotp
            totp = pyotp.TOTP(totp_secret.secret_key)
            is_valid = totp.verify(token)
            
            if is_valid:
                self.logger.info(f"2FA token verified successfully for user {user.email}")
            else:
                self.logger.warning(f"Invalid 2FA token provided for user {user.email}")
            
            return is_valid
        except ImportError:
            self.logger.error("pyotp library not installed. Please install it: pip install pyotp")
            return False
        except Exception as e:
            self.logger.error(f"Error verifying 2FA token for user {user.email}: {e}")
            return False


# --- Instancias Globales de Generadores ---

# Generador de tokens base
token_generator = TokenGenerator()

# Generador de tokens de restablecimiento de contraseña
password_reset_token_generator = PasswordResetTokenGenerator(
    token_length=32,
    expiry_hours=getattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS', 24)
)

# Generador de tokens de verificación de email
email_verification_token_generator = EmailVerificationTokenGenerator(
    token_length=32,
    expiry_hours=getattr(settings, 'EMAIL_VERIFICATION_TIMEOUT_HOURS', 24)
)

# Generador de tokens de 2FA
two_factor_token_generator = TwoFactorTokenGenerator(
    token_length=6,
    expiry_minutes=getattr(settings, 'TWO_FACTOR_TOKEN_TIMEOUT_MINUTES', 5)
)
