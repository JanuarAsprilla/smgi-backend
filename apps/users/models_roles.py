"""
Sistema de Roles y Permisos Multi-nivel
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Role(models.Model):
    """Roles predefinidos en el sistema"""
    
    ROLE_TYPES = [
        ('super_admin', 'Super Administrador'),
        ('area_admin', 'Administrador de Área'),
        ('analyst_ai', 'Analista IA'),
        ('loader', 'Cargador de Capas'),
        ('monitor_analyst', 'Analista de Monitoreo'),
        ('viewer', 'Visualizador'),
        ('downloader', 'Descargador'),
        ('editor', 'Editor'),
        ('custom', 'Rol Personalizado'),
    ]
    
    name = models.CharField(max_length=100)
    role_type = models.CharField(max_length=20, choices=ROLE_TYPES)
    description = models.TextField(blank=True)
    
    # Permisos del rol
    can_upload_layers = models.BooleanField(default=False)
    can_view_layers = models.BooleanField(default=True)
    can_edit_layers = models.BooleanField(default=False)
    can_delete_layers = models.BooleanField(default=False)
    can_download_layers = models.BooleanField(default=False)
    
    can_create_analysis = models.BooleanField(default=False)
    can_view_analysis = models.BooleanField(default=True)
    can_delete_analysis = models.BooleanField(default=False)
    can_upload_agents = models.BooleanField(default=False)
    
    can_create_monitors = models.BooleanField(default=False)
    can_view_monitors = models.BooleanField(default=True)
    can_configure_alerts = models.BooleanField(default=False)
    
    can_manage_users = models.BooleanField(default=False)
    can_approve_users = models.BooleanField(default=False)
    can_create_areas = models.BooleanField(default=False)
    can_share_resources = models.BooleanField(default=False)
    
    can_export_reports = models.BooleanField(default=False)
    can_view_audit_logs = models.BooleanField(default=False)
    
    is_system_role = models.BooleanField(default=True)  # No se puede eliminar
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users_role'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
    
    def __str__(self):
        return self.name


class Area(models.Model):
    """Áreas o grupos de trabajo"""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Administradores del área (pueden haber varios)
    admins = models.ManyToManyField(
        User,
        related_name='administered_areas',
        blank=True
    )
    
    # Configuración de privacidad
    PRIVACY_CHOICES = [
        ('private', 'Privado'),
        ('internal', 'Interno'),
        ('public', 'Público'),
    ]
    privacy = models.CharField(
        max_length=20,
        choices=PRIVACY_CHOICES,
        default='private'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users_area'
        verbose_name = 'Área'
        verbose_name_plural = 'Áreas'
    
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Perfil extendido de usuario"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Rol y área
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    
    # Información adicional
    phone = models.CharField(max_length=20, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=200, blank=True)
    
    # Estado de aprobación
    STATUS_CHOICES = [
        ('pending', 'Pendiente de Aprobación'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('suspended', 'Suspendido'),
    ]
    approval_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Justificación de solicitud
    access_justification = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Fechas importantes
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users'
    )
    
    # Preferencias de notificaciones
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    
    # Notificaciones específicas
    notify_analysis_complete = models.BooleanField(default=True)
    notify_analysis_failed = models.BooleanField(default=True)
    notify_alerts_critical = models.BooleanField(default=True)
    notify_alerts_medium = models.BooleanField(default=False)
    notify_alerts_low = models.BooleanField(default=False)
    notify_resource_shared = models.BooleanField(default=True)
    notify_weekly_report = models.BooleanField(default=False)
    
    # 2FA
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    
    # Metadata
    last_activity = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users_profile'
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    def has_permission(self, permission):
        """Verificar si el usuario tiene un permiso específico"""
        if not self.role:
            return False
        return getattr(self.role, permission, False)


class ActivityLog(models.Model):
    """Log de actividad de usuarios"""
    
    ACTION_TYPES = [
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
        ('upload_layer', 'Subir Capa'),
        ('delete_layer', 'Eliminar Capa'),
        ('export_layer', 'Exportar Capa'),
        ('create_analysis', 'Crear Análisis'),
        ('delete_analysis', 'Eliminar Análisis'),
        ('create_monitor', 'Crear Monitor'),
        ('share_resource', 'Compartir Recurso'),
        ('edit_user', 'Editar Usuario'),
        ('approve_user', 'Aprobar Usuario'),
        ('reject_user', 'Rechazar Usuario'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField(blank=True)
    
    # Detalles técnicos
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Metadata adicional (JSON)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users_activity_log'
        verbose_name = 'Log de Actividad'
        verbose_name_plural = 'Logs de Actividad'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.created_at}"
