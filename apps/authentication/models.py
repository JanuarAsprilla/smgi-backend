"""
SMGI Backend - Authentication Models
Sistema de Monitoreo Geoespacial Inteligente
Modelos de autenticación y autorización profesionales
"""
import uuid
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.gis.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel, SoftDeletableModel
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import UserManager as BaseUserManager


class UserManager(BaseUserManager):
    """Custom User Manager with additional methods"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password"""
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
            
        return self.create_user(email, password, **extra_fields)
    
    def active_users(self):
        """Return only active users"""
        return self.filter(is_active=True, is_removed=False)
    
    def verified_users(self):
        """Return only verified users"""
        return self.filter(email_verified=True, is_active=True)


class UserRole(models.TextChoices):
    """User role choices"""
    ADMIN = 'admin', _('Administrador')
    MANAGER = 'manager', _('Gestor')
    ANALYST = 'analyst', _('Analista')
    VIEWER = 'viewer', _('Visualizador')
    GUEST = 'guest', _('Invitado')


class Department(models.TextChoices):
    """Colombian departments"""
    AMAZONAS = 'amazonas', _('Amazonas')
    ANTIOQUIA = 'antioquia', _('Antioquia')
    ARAUCA = 'arauca', _('Arauca')
    ATLANTICO = 'atlantico', _('Atlántico')
    BOLIVAR = 'bolivar', _('Bolívar')
    BOYACA = 'boyaca', _('Boyacá')
    CALDAS = 'caldas', _('Caldas')
    CAQUETA = 'caqueta', _('Caquetá')
    CASANARE = 'casanare', _('Casanare')
    CAUCA = 'cauca', _('Cauca')
    CESAR = 'cesar', _('Cesar')
    CHOCO = 'choco', _('Chocó')
    CORDOBA = 'cordoba', _('Córdoba')
    CUNDINAMARCA = 'cundinamarca', _('Cundinamarca')
    GUAINIA = 'guainia', _('Guainía')
    GUAVIARE = 'guaviare', _('Guaviare')
    HUILA = 'huila', _('Huila')
    LA_GUAJIRA = 'la_guajira', _('La Guajira')
    MAGDALENA = 'magdalena', _('Magdalena')
    META = 'meta', _('Meta')
    NARINO = 'narino', _('Nariño')
    NORTE_SANTANDER = 'norte_santander', _('Norte de Santander')
    PUTUMAYO = 'putumayo', _('Putumayo')
    QUINDIO = 'quindio', _('Quindío')
    RISARALDA = 'risaralda', _('Risaralda')
    SAN_ANDRES = 'san_andres', _('San Andrés y Providencia')
    SANTANDER = 'santander', _('Santander')
    SUCRE = 'sucre', _('Sucre')
    TOLIMA = 'tolima', _('Tolima')
    VALLE_DEL_CAUCA = 'valle_del_cauca', _('Valle del Cauca')
    VAUPES = 'vaupes', _('Vaupés')
    VICHADA = 'vichada', _('Vichada')
    BOGOTA = 'bogota', _('Bogotá D.C.')


class User(AbstractUser, TimeStampedModel, SoftDeletableModel):
    """
    Custom User model with enhanced fields for professional system
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Override username field - we use email as username
    username = None
    email = models.EmailField(_('Email Address'), unique=True, db_index=True)
    
    # Personal Information
    first_name = models.CharField(_('First Name'), max_length=150, blank=False)
    last_name = models.CharField(_('Last Name'), max_length=150, blank=False)
    document_type = models.CharField(
        _('Document Type'),
        max_length=20,
        choices=[
            ('CC', _('Cédula de Ciudadanía')),
            ('CE', _('Cédula de Extranjería')),
            ('TI', _('Tarjeta de Identidad')),
            ('PP', _('Pasaporte')),
        ],
        default='CC'
    )
    document_number = models.CharField(
        _('Document Number'),
        max_length=20,
        validators=[RegexValidator(regex=r'^\d{6,20}$', message=_('Document number must be numeric'))],
        unique=True,
        db_index=True
    )
    
    # Contact Information
    phone = PhoneNumberField(_('Phone Number'), blank=True, null=True)
    mobile = PhoneNumberField(_('Mobile Number'), blank=True, null=True)
    
    # Professional Information
    organization = models.CharField(_('Organization'), max_length=200, blank=True)
    department = models.CharField(
        _('Department'),
        max_length=50,
        choices=Department.choices,
        blank=True
    )
    position = models.CharField(_('Position'), max_length=100, blank=True)
    
    # System Fields
    role = models.CharField(
        _('Role'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VIEWER
    )
    
    # Account Status
    email_verified = models.BooleanField(_('Email Verified'), default=False)
    email_verification_token = models.CharField(max_length=255, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    
    # Two-Factor Authentication
    two_factor_enabled = models.BooleanField(_('2FA Enabled'), default=False)
    backup_tokens = models.JSONField(_('Backup Tokens'), default=list, blank=True)
    
    # Password Management
    password_changed_at = models.DateTimeField(_('Password Changed At'), auto_now_add=True)
    must_change_password = models.BooleanField(_('Must Change Password'), default=False)
    failed_login_attempts = models.PositiveIntegerField(_('Failed Login Attempts'), default=0)
    account_locked_until = models.DateTimeField(_('Account Locked Until'), blank=True, null=True)
    
    # Activity Tracking
    last_login_ip = models.GenericIPAddressField(_('Last Login IP'), blank=True, null=True)
    last_activity = models.DateTimeField(_('Last Activity'), auto_now=True)
    timezone = models.CharField(
        _('Timezone'),
        max_length=50,
        default='America/Bogota'
    )
    
    # Preferences
    language = models.CharField(
        _('Language'),
        max_length=10,
        choices=[
            ('es', _('Spanish')),
            ('en', _('English')),
        ],
        default='es'
    )
    notification_preferences = models.JSONField(
        _('Notification Preferences'),
        default=dict,
        blank=True,
        help_text=_('JSON object with notification preferences')
    )
    
    # Soft delete field is inherited from SoftDeletableModel
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'document_number']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['document_number']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['email_verified']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the short name for the user"""
        return self.first_name
    
    def is_account_locked(self):
        """Check if account is locked"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration"""
        self.account_locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])
    
    def unlock_account(self):
        """Unlock account"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])
    
    def increment_failed_login(self):
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:  # Lock after 5 failed attempts
            self.lock_account()
        else:
            self.save(update_fields=['failed_login_attempts'])
    
    def reset_failed_login(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        self.save(update_fields=['failed_login_attempts'])
    
    def can_access_feature(self, feature):
        """Check if user can access a specific feature based on role"""
        permissions_map = {
            UserRole.ADMIN: ['all'],
            UserRole.MANAGER: ['manage_services', 'view_reports', 'manage_alerts', 'view_analytics'],
            UserRole.ANALYST: ['view_reports', 'view_analytics', 'create_reports'],
            UserRole.VIEWER: ['view_basic'],
            UserRole.GUEST: ['view_public'],
        }
        
        user_permissions = permissions_map.get(self.role, [])
        return 'all' in user_permissions or feature in user_permissions
    
    def get_notification_preference(self, notification_type):
        """Get notification preference for specific type"""
        default_preferences = {
            'email_alerts': True,
            'email_reports': True,
            'push_notifications': True,
            'sms_critical': False,
        }
        
        return self.notification_preferences.get(
            notification_type, 
            default_preferences.get(notification_type, False)
        )
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class RefreshToken(TimeStampedModel):
    """
    Model to track refresh tokens for JWT authentication
    Allows for token rotation and blacklisting
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token = models.CharField(_('Token'), max_length=500, unique=True, db_index=True)
    expires_at = models.DateTimeField(_('Expires At'))
    is_blacklisted = models.BooleanField(_('Is Blacklisted'), default=False)
    
    # Device/Session tracking
    device_info = models.JSONField(_('Device Info'), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    class Meta:
        db_table = 'auth_refresh_token'
        verbose_name = _('Refresh Token')
        verbose_name_plural = _('Refresh Tokens')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_blacklisted']),
        ]
    
    def __str__(self):
        return f"Token for {self.user.email} - {self.token[:20]}..."
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    def blacklist(self):
        """Blacklist this token"""
        self.is_blacklisted = True
        self.save(update_fields=['is_blacklisted'])


class PasswordResetToken(TimeStampedModel):
    """
    Model for password reset tokens
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(_('Token'), max_length=255, unique=True, db_index=True)
    expires_at = models.DateTimeField(_('Expires At'))
    used = models.BooleanField(_('Used'), default=False)
    ip_address = models.GenericIPAddressField(_('IP Address'), blank=True, null=True)
    
    class Meta:
        db_table = 'auth_password_reset_token'
        verbose_name = _('Password Reset Token')
        verbose_name_plural = _('Password Reset Tokens')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['used']),
        ]
    
    def __str__(self):
        return f"Password reset for {self.user.email}"
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid (not expired and not used)"""
        return not self.is_expired() and not self.used
    
    def use_token(self):
        """Mark token as used"""
        self.used = True
        self.save(update_fields=['used'])


class EmailVerificationToken(TimeStampedModel):
    """
    Model for email verification tokens
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verification_tokens')
    token = models.CharField(_('Token'), max_length=255, unique=True, db_index=True)
    email = models.EmailField(_('Email to Verify'))
    expires_at = models.DateTimeField(_('Expires At'))
    used = models.BooleanField(_('Used'), default=False)
    
    class Meta:
        db_table = 'auth_email_verification_token'
        verbose_name = _('Email Verification Token')
        verbose_name_plural = _('Email Verification Tokens')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['token']),
            models.Index(fields=['email']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Email verification for {self.email}"
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid"""
        return not self.is_expired() and not self.used
    
    def verify_email(self):
        """Mark token as used and verify user email"""
        self.used = True
        self.user.email_verified = True
        self.user.email = self.email  # In case email was changed
        
        self.save(update_fields=['used'])
        self.user.save(update_fields=['email_verified', 'email'])


class LoginAttempt(TimeStampedModel):
    """
    Model to track login attempts for security monitoring
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='login_attempts')
    email = models.EmailField(_('Email Attempted'))
    ip_address = models.GenericIPAddressField(_('IP Address'))
    user_agent = models.TextField(_('User Agent'), blank=True)
    success = models.BooleanField(_('Success'), default=False)
    failure_reason = models.CharField(_('Failure Reason'), max_length=100, blank=True)
    
    # Location data (if available)
    country = models.CharField(_('Country'), max_length=100, blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True)
    
    class Meta:
        db_table = 'auth_login_attempt'
        verbose_name = _('Login Attempt')
        verbose_name_plural = _('Login Attempts')
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['email']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['success']),
            models.Index(fields=['created']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else f"Failed ({self.failure_reason})"
        return f"{self.email} from {self.ip_address} - {status}"


class UserSession(TimeStampedModel):
    """
    Model to track active user sessions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(_('Session Key'), max_length=255, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(_('IP Address'))
    user_agent = models.TextField(_('User Agent'), blank=True)
    is_active = models.BooleanField(_('Is Active'), default=True)
    last_activity = models.DateTimeField(_('Last Activity'), auto_now=True)
    expires_at = models.DateTimeField(_('Expires At'))
    
    # Device info
    device_type = models.CharField(
        _('Device Type'),
        max_length=20,
        choices=[
            ('desktop', _('Desktop')),
            ('mobile', _('Mobile')),
            ('tablet', _('Tablet')),
            ('unknown', _('Unknown')),
        ],
        default='unknown'
    )
    browser = models.CharField(_('Browser'), max_length=100, blank=True)
    os = models.CharField(_('Operating System'), max_length=100, blank=True)
    
    class Meta:
        db_table = 'auth_user_session'
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_key']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_activity']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.ip_address})"
    
    def is_expired(self):
        """Check if session is expired"""
        return timezone.now() > self.expires_at
    
    def terminate(self):
        """Terminate session"""
        self.is_active = False
        self.save(update_fields=['is_active'])
    
    def update_activity(self):
        """Update last activity"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class APIKey(TimeStampedModel, SoftDeletableModel):
    """
    Model for API keys for programmatic access
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(_('Key Name'), max_length=100)
    key = models.CharField(_('API Key'), max_length=255, unique=True, db_index=True)
    is_active = models.BooleanField(_('Is Active'), default=True)
    expires_at = models.DateTimeField(_('Expires At'), blank=True, null=True)
    
    # Usage tracking
    last_used = models.DateTimeField(_('Last Used'), blank=True, null=True)
    usage_count = models.PositiveIntegerField(_('Usage Count'), default=0)
    
    # Permissions and restrictions
    allowed_ips = models.JSONField(
        _('Allowed IP Addresses'),
        default=list,
        blank=True,
        help_text=_('List of IP addresses allowed to use this key')
    )
    rate_limit = models.PositiveIntegerField(
        _('Rate Limit (per hour)'),
        default=1000,
        help_text=_('Maximum requests per hour')
    )
    scopes = models.JSONField(
        _('Scopes'),
        default=list,
        blank=True,
        help_text=_('List of API scopes this key can access')
    )
    
    class Meta:
        db_table = 'auth_api_key'
        verbose_name = _('API Key')
        verbose_name_plural = _('API Keys')
        ordering = ['-created']
        unique_together = ['user', 'name']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['key']),
            models.Index(fields=['is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.user.email})"
    
    def is_expired(self):
        """Check if API key is expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if API key is valid"""
        return self.is_active and not self.is_expired() and not self.is_removed
    
    def can_access_ip(self, ip_address):
        """Check if IP address is allowed"""
        if not self.allowed_ips:
            return True
        return ip_address in self.allowed_ips
    
    def has_scope(self, scope):
        """Check if API key has specific scope"""
        return scope in self.scopes
    
    def increment_usage(self):
        """Increment usage counter"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])
    
    def revoke(self):
        """Revoke API key"""
        self.is_active = False
        self.save(update_fields=['is_active'])