"""
Custom permissions for automation app.
"""
from rest_framework import permissions


class CanManageWorkflows(permissions.BasePermission):
    """Permission to manage workflows. Only developers and above."""
    
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


class CanExecuteWorkflows(permissions.BasePermission):
    """Permission to execute workflows. Analysts and above."""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and 
            request.user.role in ['analyst', 'developer', 'manager', 'admin']
        )
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        # Can execute own workflows or workflows in shared projects
        return obj.created_by == request.user


class CanManageAutomationRules(permissions.BasePermission):
    """Permission to manage automation rules. Only developers and above."""
    
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
