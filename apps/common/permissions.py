# apps/common/permissions.py
"""
SMGI Backend - Common Permissions
Sistema de Monitoreo Geoespacial Inteligente
Clases de permisos personalizadas reutilizables para el backend
"""
import logging
from rest_framework import permissions
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('apps.common.permissions')


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permite a los propietarios editar objetos, a los demás solo lectura.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos de lectura para cualquier solicitud
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permisos de escritura solo para el propietario del objeto
        return obj.created_by == request.user


class IsOwnerOrSharedWith(permissions.BasePermission):
    """
    Permite a los propietarios o usuarios con quienes se comparte el objeto editar/ver.
    """
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el propietario
        if obj.created_by == request.user:
            return True
        
        # Verificar si el objeto está compartido con el usuario
        # Asumiendo que el objeto tiene un campo 'shared_with' de tipo ManyToManyField a User
        # if hasattr(obj, 'shared_with') and request.user in obj.shared_with.all():
        #     return True
        
        # Si no se encuentra ninguna relación, denegar permiso
        return False


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Permite a los propietarios y administradores editar objetos, a los demás solo lectura.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos de lectura para cualquier solicitud
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permisos de escritura solo para el propietario o administradores
        return obj.created_by == request.user or request.user.is_staff or request.user.is_superuser


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permite a los propietarios y administradores editar/ver objetos.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos solo para el propietario o administradores
        return obj.created_by == request.user or request.user.is_staff or request.user.is_superuser


class IsOwnerOrStaffOrReadOnly(permissions.BasePermission):
    """
    Permite a los propietarios, staff y administradores editar objetos, a los demás solo lectura.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos de lectura para cualquier solicitud
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permisos de escritura solo para el propietario, staff o administradores
        return obj.created_by == request.user or request.user.is_staff or request.user.is_superuser


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Permite a los propietarios, staff y administradores editar/ver objetos.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos solo para el propietario, staff o administradores
        return obj.created_by == request.user or request.user.is_staff or request.user.is_superuser


class IsOwnerOrSuperuserOrReadOnly(permissions.BasePermission):
    """
    Permite a los propietarios y superusuarios editar objetos, a los demás solo lectura.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos de lectura para cualquier solicitud
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permisos de escritura solo para el propietario o superusuarios
        return obj.created_by == request.user or request.user.is_superuser


class IsOwnerOrSuperuser(permissions.BasePermission):
    """
    Permite a los propietarios y superusuarios editar/ver objetos.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos solo para el propietario o superusuarios
        return obj.created_by == request.user or request.user.is_superuser


class IsOwnerOrGroupMemberOrReadOnly(permissions.BasePermission):
    """
    Permite a los propietarios, miembros del grupo y administradores editar objetos, a los demás solo lectura.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos de lectura para cualquier solicitud
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permisos de escritura solo para el propietario, miembros del grupo o administradores
        return (
            obj.created_by == request.user or
            request.user.groups.filter(name__in=[obj.group.name]).exists() or
            request.user.is_staff or
            request.user.is_superuser
        )


class IsOwnerOrGroupMember(permissions.BasePermission):
    """
    Permite a los propietarios, miembros del grupo y administradores editar/ver objetos.
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos solo para el propietario, miembros del grupo o administradores
        return (
            obj.created_by == request.user or
            request.user.groups.filter(name__in=[obj.group.name]).exists() or
            request.user.is_staff or
            request.user.is_superuser
        )


class IsAuthenticatedAndActive(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados y activos.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_active


class IsAuthenticatedAndVerified(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos y verificados.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            getattr(request.user, 'email_verified', False) # Asumiendo que User tiene email_verified
        )


class IsAuthenticatedAndStaff(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos y staff.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            request.user.is_staff
        )


class IsAuthenticatedAndSuperuser(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos y superusuarios.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            request.user.is_superuser
        )


class IsAuthenticatedAndAdmin(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos y administradores.
    Asumiendo que 'administrador' es un rol específico en el modelo User.
    """
    
    def has_permission(self, request, view):
        # Asumiendo que User tiene un campo 'role' con choices y 'ADMIN' como valor
        # from apps.authentication.models import UserRole
        # return (
        #     request.user and
        #     request.user.is_authenticated and
        #     request.user.is_active and
        #     request.user.role == UserRole.ADMIN
        # )
        # O si 'admin' es un grupo
        # return (
        #     request.user and
        #     request.user.is_authenticated and
        #     request.user.is_active and
        #     request.user.groups.filter(name='admin').exists()
        # )
        # O si 'admin' es un permiso
        # return (
        #     request.user and
        #     request.user.is_authenticated and
        #     request.user.is_active and
        #     request.user.has_perm('auth.admin')
        # )
        # Placeholder: Asumir que 'admin' es un rol específico
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            getattr(request.user, 'is_admin', False) # Asumiendo que User tiene is_admin
        )


class IsAuthenticatedAndOwner(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos y propietarios del objeto.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            obj.created_by == request.user
        )


class IsAuthenticatedAndSharedWith(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos y con quienes se comparte el objeto.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            # Asumiendo que el objeto tiene un campo 'shared_with' de tipo ManyToManyField a User
            # hasattr(obj, 'shared_with') and request.user in obj.shared_with.all()
            False # Placeholder
        )


class IsAuthenticatedAndOwnerOrSharedWith(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios o con quienes se comparte el objeto.
    """
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el propietario
        if obj.created_by == request.user:
            return True
        
        # Verificar si el objeto está compartido con el usuario
        # Asumiendo que el objeto tiene un campo 'shared_with' de tipo ManyToManyField a User
        # if hasattr(obj, 'shared_with') and request.user in obj.shared_with.all():
        #     return True
        
        # Si no se encuentra ninguna relación, denegar permiso
        return False


class IsAuthenticatedAndOwnerOrAdmin(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios o administradores.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (obj.created_by == request.user or request.user.is_staff or request.user.is_superuser)
        )


class IsAuthenticatedAndOwnerOrStaff(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios, staff o administradores.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (obj.created_by == request.user or request.user.is_staff or request.user.is_superuser)
        )


class IsAuthenticatedAndOwnerOrSuperuser(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios o superusuarios.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (obj.created_by == request.user or request.user.is_superuser)
        )


class IsAuthenticatedAndOwnerOrGroupMember(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios, miembros del grupo o administradores.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (
                obj.created_by == request.user or
                request.user.groups.filter(name__in=[obj.group.name]).exists() or
                request.user.is_staff or
                request.user.is_superuser
            )
        )


class IsAuthenticatedAndOwnerOrGroupMemberOrAdmin(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios, miembros del grupo, staff o administradores.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (
                obj.created_by == request.user or
                request.user.groups.filter(name__in=[obj.group.name]).exists() or
                request.user.is_staff or
                request.user.is_superuser
            )
        )


class IsAuthenticatedAndOwnerOrGroupMemberOrStaff(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios, miembros del grupo, staff o administradores.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (
                obj.created_by == request.user or
                request.user.groups.filter(name__in=[obj.group.name]).exists() or
                request.user.is_staff or
                request.user.is_superuser
            )
        )


class IsAuthenticatedAndOwnerOrGroupMemberOrSuperuser(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios, miembros del grupo o superusuarios.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (
                obj.created_by == request.user or
                request.user.groups.filter(name__in=[obj.group.name]).exists() or
                request.user.is_superuser
            )
        )


class IsAuthenticatedAndOwnerOrGroupMemberOrAdminOrStaff(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios, miembros del grupo, staff o administradores.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (
                obj.created_by == request.user or
                request.user.groups.filter(name__in=[obj.group.name]).exists() or
                request.user.is_staff or
                request.user.is_superuser
            )
        )


class IsAuthenticatedAndOwnerOrGroupMemberOrAdminOrSuperuser(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios, miembros del grupo, staff o superusuarios.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (
                obj.created_by == request.user or
                request.user.groups.filter(name__in=[obj.group.name]).exists() or
                request.user.is_staff or
                request.user.is_superuser
            )
        )


class IsAuthenticatedAndOwnerOrGroupMemberOrAdminOrStaffOrSuperuser(permissions.BasePermission):
    """
    Permite acceso solo a usuarios autenticados, activos, propietarios, miembros del grupo, staff, administradores o superusuarios.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            (
                obj.created_by == request.user or
                request.user.groups.filter(name__in=[obj.group.name]).exists() or
                request.user.is_staff or
                request.user.is_superuser
            )
        )


class HasPermission(permissions.BasePermission):
    """
    Permite acceso basado en permisos específicos.
    """
    
    def has_permission(self, request, view):
        # Asumir que el permiso se pasa como parámetro en la vista
        # Ej: permission_required = 'reports.view_report'
        permission_required = getattr(view, 'permission_required', None)
        if not permission_required:
            return True # No permission required
        
        return request.user.has_perm(permission_required)


class HasRole(permissions.BasePermission):
    """
    Permite acceso basado en roles específicos.
    """
    
    def has_permission(self, request, view):
        # Asumir que el rol se pasa como parámetro en la vista
        # Ej: role_required = 'admin'
        role_required = getattr(view, 'role_required', None)
        if not role_required:
            return True # No role required
        
        # Asumiendo que User tiene un campo 'role' con choices
        # from apps.authentication.models import UserRole
        # return request.user.role == role_required
        # O si 'role' es un grupo
        # return request.user.groups.filter(name=role_required).exists()
        # Placeholder: Asumir que 'role' es un campo en User
        return getattr(request.user, 'role', None) == role_required


class HasGroup(permissions.BasePermission):
    """
    Permite acceso basado en grupos específicos.
    """
    
    def has_permission(self, request, view):
        # Asumir que el grupo se pasa como parámetro en la vista
        # Ej: group_required = 'developers'
        group_required = getattr(view, 'group_required', None)
        if not group_required:
            return True # No group required
        
        return request.user.groups.filter(name=group_required).exists()


class HasObjectPermission(permissions.BasePermission):
    """
    Permite acceso basado en permisos específicos sobre un objeto.
    """
    
    def has_object_permission(self, request, view, obj):
        # Asumir que el permiso se pasa como parámetro en la vista
        # Ej: object_permission_required = 'reports.change_report'
        object_permission_required = getattr(view, 'object_permission_required', None)
        if not object_permission_required:
            return True # No object permission required
        
        return request.user.has_perm(object_permission_required, obj)


class HasObjectRole(permissions.BasePermission):
    """
    Permite acceso basado en roles específicos sobre un objeto.
    """
    
    def has_object_permission(self, request, view, obj):
        # Asumir que el rol se pasa como parámetro en la vista
        # Ej: object_role_required = 'admin'
        object_role_required = getattr(view, 'object_role_required', None)
        if not object_role_required:
            return True # No object role required
        
        # Asumiendo que el objeto tiene un campo 'role' con choices
        # return obj.role == object_role_required
        # Placeholder: Asumir que 'role' es un campo en el objeto
        return getattr(obj, 'role', None) == object_role_required


class HasObjectGroup(permissions.BasePermission):
    """
    Permite acceso basado en grupos específicos sobre un objeto.
    """
    
    def has_object_permission(self, request, view, obj):
        # Asumir que el grupo se pasa como parámetro en la vista
        # Ej: object_group_required = 'developers'
        object_group_required = getattr(view, 'object_group_required', None)
        if not object_group_required:
            return True # No object group required
        
        # Asumiendo que el objeto tiene un campo 'group' de tipo ForeignKey a Group
        # return obj.group.name == object_group_required
        # Placeholder: Asumir que 'group' es un campo en el objeto
        return getattr(obj, 'group', None) and obj.group.name == object_group_required


class IsInGroup(permissions.BasePermission):
    """
    Verifica si el usuario pertenece a un grupo específico.
    """
    
    def has_permission(self, request, view):
        # Asumir que el grupo se pasa como parámetro en la vista
        # Ej: group_name = 'developers'
        group_name = getattr(view, 'group_name', None)
        if not group_name:
            return True # No group required
        
        return request.user.groups.filter(name=group_name).exists()


class HasRoleOrPermission(permissions.BasePermission):
    """
    Verifica si el usuario tiene un rol o permiso específico.
    """
    
    def has_permission(self, request, view):
        # Asumir que el rol o permiso se pasan como parámetros en la vista
        # Ej: role_required = 'admin', permission_required = 'reports.view_report'
        role_required = getattr(view, 'role_required', None)
        permission_required = getattr(view, 'permission_required', None)
        
        if not role_required and not permission_required:
            return True # No role or permission required
        
        # Verificar rol
        if role_required:
            # Asumiendo que User tiene un campo 'role' con choices
            # from apps.authentication.models import UserRole
            # if request.user.role == role_required:
            #     return True
            # O si 'role' es un grupo
            # if request.user.groups.filter(name=role_required).exists():
            #     return True
            # Placeholder: Asumir que 'role' es un campo en User
            if getattr(request.user, 'role', None) == role_required:
                return True
        
        # Verificar permiso
        if permission_required:
            if request.user.has_perm(permission_required):
                return True
        
        # Si no se cumple ninguno, denegar permiso
        return False


class IsOwnerOrHasRoleOrPermission(permissions.BasePermission):
    """
    Verifica si el usuario es el propietario o tiene un rol o permiso específico.
    """
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el propietario
        if obj.created_by == request.user:
            return True
        
        # Asumir que el rol o permiso se pasan como parámetros en la vista
        # Ej: role_required = 'admin', permission_required = 'reports.change_report'
        role_required = getattr(view, 'role_required', None)
        permission_required = getattr(view, 'permission_required', None)
        
        if not role_required and not permission_required:
            return True # No role or permission required
        
        # Verificar rol
        if role_required:
            # Asumiendo que User tiene un campo 'role' con choices
            # from apps.authentication.models import UserRole
            # if request.user.role == role_required:
            #     return True
            # O si 'role' es un grupo
            # if request.user.groups.filter(name=role_required).exists():
            #     return True
            # Placeholder: Asumir que 'role' es un campo en User
            if getattr(request.user, 'role', None) == role_required:
                return True
        
        # Verificar permiso
        if permission_required:
            if request.user.has_perm(permission_required):
                return True
        
        # Si no se cumple ninguno, denegar permiso
        return False


class IsOwnerOrHasGroupOrPermission(permissions.BasePermission):
    """
    Verifica si el usuario es el propietario o pertenece a un grupo o tiene un permiso específico.
    """
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el propietario
        if obj.created_by == request.user:
            return True
        
        # Asumir que el grupo o permiso se pasan como parámetros en la vista
        # Ej: group_required = 'developers', permission_required = 'reports.change_report'
        group_required = getattr(view, 'group_required', None)
        permission_required = getattr(view, 'permission_required', None)
        
        if not group_required and not permission_required:
            return True # No group or permission required
        
        # Verificar grupo
        if group_required:
            if request.user.groups.filter(name=group_required).exists():
                return True
        
        # Verificar permiso
        if permission_required:
            if request.user.has_perm(permission_required):
                return True
        
        # Si no se cumple ninguno, denegar permiso
        return False


class IsOwnerOrHasRoleOrGroupOrPermission(permissions.BasePermission):
    """
    Verifica si el usuario es el propietario o tiene un rol o pertenece a un grupo o tiene un permiso específico.
    """
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el propietario
        if obj.created_by == request.user:
            return True
        
        # Asumir que el rol, grupo o permiso se pasan como parámetros en la vista
        # Ej: role_required = 'admin', group_required = 'developers', permission_required = 'reports.change_report'
        role_required = getattr(view, 'role_required', None)
        group_required = getattr(view, 'group_required', None)
        permission_required = getattr(view, 'permission_required', None)
        
        if not role_required and not group_required and not permission_required:
            return True # No role, group or permission required
        
        # Verificar rol
        if role_required:
            # Asumiendo que User tiene un campo 'role' con choices
            # from apps.authentication.models import UserRole
            # if request.user.role == role_required:
            #     return True
            # O si 'role' es un grupo
            # if request.user.groups.filter(name=role_required).exists():
            #     return True
            # Placeholder: Asumir que 'role' es un campo en User
            if getattr(request.user, 'role', None) == role_required:
                return True
        
        # Verificar grupo
        if group_required:
            if request.user.groups.filter(name=group_required).exists():
                return True
        
        # Verificar permiso
        if permission_required:
            if request.user.has_perm(permission_required):
                return True
        
        # Si no se cumple ninguno, denegar permiso
        return False
