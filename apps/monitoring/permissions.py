"""
Custom permissions for monitoring app.
"""
from rest_framework import permissions


class CanManageMonitoringProjects(permissions.BasePermission):
    """
    Permission to manage monitoring projects.
    Only analysts and above can create/edit/delete projects.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for analyst role and above
        return hasattr(request.user, 'role') and request.user.role in ['analyst', 'admin']
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for all
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Admins can edit any project
        if request.user.is_staff:
            return True
        
        # Users can only edit their own projects
        return obj.created_by == request.user


class CanManageMonitors(permissions.BasePermission):
    """
    Permission to manage monitors.
    Only project owners and admins can manage monitors.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for analyst role and above
        return hasattr(request.user, 'role') and request.user.role in ['analyst', 'admin']
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for all
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Admins can edit any monitor
        if request.user.is_staff:
            return True
        
        # Users can only edit monitors in their projects
        return obj.project.created_by == request.user


class CanReviewDetections(permissions.BasePermission):
    """
    Permission to review detections.
    Only analysts and above can confirm/resolve detections.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for analyst role and above
        return hasattr(request.user, 'role') and request.user.role in ['analyst', 'admin']
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for all
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Admins can review any detection
        if request.user.is_staff:
            return True
        
        # Analysts can review detections in their projects
        return obj.monitor.project.created_by == request.user
