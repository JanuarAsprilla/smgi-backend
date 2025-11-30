"""
Custom permissions for alerts app.
"""
from rest_framework import permissions


class CanManageAlertChannels(permissions.BasePermission):
    """
    Permission to manage alert channels.
    Only analysts and above can manage channels.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role in ['analyst', 'manager', 'admin']
        )
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        if request.user.is_staff:
            return True
        
        return obj.created_by == request.user


class CanManageAlertRules(permissions.BasePermission):
    """
    Permission to manage alert rules.
    Only analysts and above can manage rules.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role in ['analyst', 'manager', 'admin']
        )
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        if request.user.is_staff:
            return True
        
        if obj.created_by == request.user:
            return True
        
        user_projects = obj.projects.filter(created_by=request.user)
        return user_projects.exists()
