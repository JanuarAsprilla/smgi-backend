"""
Admin configuration for Users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile."""
    model = UserProfile
    fk_name = 'user'
    can_delete = False
    verbose_name_plural = 'Perfil'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'role', 'organization', 'is_verified', 'is_active', 'created_at']
    list_filter = ['role', 'is_verified', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'organization']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Información Personal'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'bio', 'avatar')}),
        (_('Información Profesional'), {'fields': ('role', 'organization', 'is_verified')}),
        (_('Permisos'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Fechas Importantes'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'organization'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""
    list_display = ['user', 'role', 'area', 'approval_status', 'created_at']
    list_filter = ['approval_status', 'role', 'area', 'two_factor_enabled']
    search_fields = ['user__username', 'user__email', 'organization', 'department']
    readonly_fields = ['created_at', 'updated_at', 'approved_at', 'approved_by']
    
    fieldsets = (
        ('Usuario', {'fields': ('user',)}),
        ('Rol y Área', {'fields': ('role', 'area')}),
        ('Información Profesional', {'fields': ('organization', 'department', 'position', 'phone')}),
        ('Estado de Aprobación', {'fields': ('approval_status', 'access_justification', 'rejection_reason', 'approved_at', 'approved_by')}),
        ('Notificaciones', {'fields': ('email_notifications', 'sms_notifications', 'push_notifications', 'notify_analysis_complete', 'notify_analysis_failed', 'notify_alerts_critical')}),
        ('Seguridad', {'fields': ('two_factor_enabled',)}),
        ('Metadata', {'fields': ('last_activity', 'created_at', 'updated_at')}),
    )
