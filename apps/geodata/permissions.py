"""
Custom permissions for geodata app.
"""
from rest_framework import permissions


class CanManageDataSources(permissions.BasePermission):
    """Permission to manage data sources. Only developers and above."""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role in ['developer', 'manager', 'admin']
        )
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        if request.user.is_staff:
            return True
        
        return obj.created_by == request.user


class CanManageLayers(permissions.BasePermission):
    """Permission to manage layers. Analysts and above."""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role in ['analyst', 'developer', 'manager', 'admin']
        )
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Public layers can be viewed by anyone
            if getattr(obj, 'is_public', False):
                return True
            return request.user.is_authenticated
        
        if request.user.is_staff:
            return True
        
        return obj.created_by == request.user


class CanViewPublicData(permissions.BasePermission):
    """Permission to view public geodata."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Anyone authenticated can view public data
        if getattr(obj, 'is_public', False):
            return True
        
        # Staff and owners can view private data
        if request.user.is_staff:
            return True
        
        return obj.created_by == request.user
