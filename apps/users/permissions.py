"""
Custom permissions for Users app.
"""
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners of an object or admins to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner or admin
        return obj == request.user or request.user.is_staff


class IsAdminUser(permissions.BasePermission):
    """
    Permission to only allow admin users.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsAnalystOrAbove(permissions.BasePermission):
    """
    Permission to only allow analyst role or above.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        allowed_roles = ['analyst', 'developer', 'admin']
        return request.user.role in allowed_roles or request.user.is_staff


class IsDeveloperOrAbove(permissions.BasePermission):
    """
    Permission to only allow developer role or above.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        allowed_roles = ['developer', 'admin']
        return request.user.role in allowed_roles or request.user.is_staff
