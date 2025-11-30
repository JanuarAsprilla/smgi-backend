"""
Permissions for Notifications app.
"""
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Permission to only allow owners of a notification to view/edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Only the notification owner can access it
        return obj.user == request.user
