#!/bin/bash

# Este script crea la estructura base para las apps restantes

create_base_files() {
    APP_NAME=$1
    
    # models.py base
    cat > apps/$APP_NAME/models.py << 'MODELS_EOF'
"""
Models for APP_NAME app.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import User


class BaseModel(models.Model):
    """
    Abstract base model with common fields.
    """
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_created',
        verbose_name=_('creado por')
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_updated',
        verbose_name=_('actualizado por')
    )
    created_at = models.DateTimeField(
        _('fecha de creación'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('fecha de actualización'),
        auto_now=True
    )
    is_active = models.BooleanField(
        _('activo'),
        default=True
    )
    
    class Meta:
        abstract = True


# TODO: Add specific models for APP_NAME
MODELS_EOF
    sed -i "s/APP_NAME/$APP_NAME/g" apps/$APP_NAME/models.py
    
    # apps.py
    APP_NAME_TITLE=$(echo $APP_NAME | sed 's/\b\(.\)/\u\1/g')
    cat > apps/$APP_NAME/apps.py << APPS_EOF
"""
$APP_NAME_TITLE app configuration.
"""
from django.apps import AppConfig


class ${APP_NAME_TITLE}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.$APP_NAME'
    verbose_name = '$APP_NAME_TITLE'
    
    def ready(self):
        import apps.$APP_NAME.signals
APPS_EOF
    
    # serializers.py
    cat > apps/$APP_NAME/serializers.py << SERIALIZERS_EOF
"""
Serializers for $APP_NAME app.
"""
from rest_framework import serializers

# TODO: Add serializers for $APP_NAME
SERIALIZERS_EOF
    
    # views.py
    cat > apps/$APP_NAME/views.py << VIEWS_EOF
"""
Views for $APP_NAME app.
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

# TODO: Add views for $APP_NAME
VIEWS_EOF
    
    # urls.py
    cat > apps/$APP_NAME/urls.py << URLS_EOF
"""
URLs for $APP_NAME app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

# TODO: Register viewsets

urlpatterns = [
    path('', include(router.urls)),
]
URLS_EOF
    
    # admin.py
    cat > apps/$APP_NAME/admin.py << ADMIN_EOF
"""
Admin configuration for $APP_NAME app.
"""
from django.contrib import admin

# TODO: Register models in admin
ADMIN_EOF
    
    # signals.py
    cat > apps/$APP_NAME/signals.py << SIGNALS_EOF
"""
Signals for $APP_NAME app.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

# TODO: Add signals for $APP_NAME
SIGNALS_EOF
    
    # tasks.py
    cat > apps/$APP_NAME/tasks.py << TASKS_EOF
"""
Celery tasks for $APP_NAME app.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

# TODO: Add tasks for $APP_NAME
TASKS_EOF
    
    # permissions.py
    cat > apps/$APP_NAME/permissions.py << PERMISSIONS_EOF
"""
Custom permissions for $APP_NAME app.
"""
from rest_framework import permissions

# TODO: Add custom permissions for $APP_NAME
PERMISSIONS_EOF
    
    # filters.py
    cat > apps/$APP_NAME/filters.py << FILTERS_EOF
"""
Filters for $APP_NAME app.
"""
from django_filters import rest_framework as filters

# TODO: Add filters for $APP_NAME
FILTERS_EOF
    
    # tests.py
    cat > apps/$APP_NAME/tests.py << TESTS_EOF
"""
Tests for $APP_NAME app.
"""
from django.test import TestCase
from rest_framework.test import APITestCase

# TODO: Add tests for $APP_NAME
TESTS_EOF
    
    echo "✅ Estructura base creada para $APP_NAME"
}

# Crear estructura para cada app
create_base_files "geodata"
create_base_files "agents"
create_base_files "monitoring"
create_base_files "alerts"
create_base_files "automation"

echo "✅ ¡Todas las estructuras base han sido creadas!"
