"""
Django settings initialization.
Automatically selects the appropriate settings based on environment.
"""
import os

# Detectar entorno de Railway
if os.environ.get('RAILWAY_ENVIRONMENT'):
    from .production import *
    print("✅ Cargando configuración de PRODUCCIÓN (Railway)")
else:
    # Intentar cargar desarrollo, si falla usar base
    try:
        from .development import *
        print("🔧 Cargando configuración de DESARROLLO")
    except ImportError:
        from .base import *
        print("🔧 Cargando configuración BASE")