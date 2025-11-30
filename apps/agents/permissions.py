"""
Custom permissions for agents app.
"""
from rest_framework import permissions


class CanExecuteAgent(permissions.BasePermission):
    """
    Permission to check if user can execute an agent.
    """
    
    def has_object_permission(self, request, view, obj):
        # Agent must be published to be executed
        if obj.status != 'published':
            return False
        
        # If agent is public, anyone authenticated can execute
        if obj.is_public:
            return request.user and request.user.is_authenticated
        
        # Otherwise, only owner or staff can execute
        return obj.created_by == request.user or request.user.is_staff


class CanManageAgent(permissions.BasePermission):
    """
    Permission to check if user can manage (edit/delete) an agent.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for owner or staff
        return obj.created_by == request.user or request.user.is_staff


class CanPublishAgent(permissions.BasePermission):
    """
    Permission to check if user can publish an agent.
    """
    
    def has_object_permission(self, request, view, obj):
        # Only owner or staff can publish
        return obj.created_by == request.user or request.user.is_staff


class CanScheduleAgent(permissions.BasePermission):
    """
    Permission to check if user can schedule agent executions.
    Requires analyst role or above.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        allowed_roles = ['analyst', 'developer', 'admin']
        return request.user.role in allowed_roles or request.user.is_staff
