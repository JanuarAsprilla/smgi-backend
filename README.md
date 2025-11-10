# SMGI - Sistema de Monitoreo Geoespacial Inteligente

Sistema completo de monitoreo geoespacial con agentes de IA, detección de cambios, alertas inteligentes y automatización.

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.11+
- Docker Desktop
- PostgreSQL + PostGIS (via Docker)
- Redis (via Docker)

### Instalación

1. **Clonar el repositorio e instalar dependencias:**
```bash
   pip install -r requirements.txt
```

2. **Iniciar todo el sistema (automático):**
```bash
   ./scripts/start_all.sh
```

3. **Iniciar el servidor Django:**
```bash
   python manage.py runserver
```

4. **Acceder a la aplicación:**
   - Admin: http://localhost:8000/admin/
   - API: http://localhost:8000/api/
   - Docs: http://localhost:8000/api/schema/swagger-ui/

### Credenciales por Defecto

- **Admin**: `admin` / `admin123`
- **Analyst**: `analyst` / `analyst123`
- **Developer**: `developer` / `dev123`
- **Viewer**: `viewer` / `viewer123`

## 📦 Arquitectura

### Apps Principales

1. **Users** - Gestión de usuarios y autenticación
2. **Geodata** - Fuentes de datos y capas geográficas
3. **Agents** - Sistema de agentes de análisis con IA
4. **Monitoring** - Motor de monitoreo y detección
5. **Alerts** - Sistema de alertas inteligentes
6. **Automation** - Motor de automatización con workflows

### Tecnologías

- **Backend**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 15 + PostGIS 3.3
- **Task Queue**: Celery + Redis
- **GIS**: GeoDjango + GDAL
- **AI**: Google Generative AI (Gemini)

## 🔧 Comandos Útiles

### Base de Datos
```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Shell interactivo
python manage.py shell
```

### Celery
```bash
# Iniciar worker
celery -A config worker -l info

# Iniciar beat (tareas programadas)
celery -A config beat -l info

# Monitorear tareas
celery -A config flower
```

### Docker
```bash
# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicios
docker-compose down

# Reiniciar servicios
docker-compose restart
```

### Tests
```bash
# Ejecutar todos los tests
python manage.py test

# Tests de una app específica
python manage.py test apps.users

# Tests con coverage
coverage run --source='.' manage.py test
coverage report
```

## 📚 Documentación de la API

La documentación completa de la API está disponible en:
- Swagger UI: http://localhost:8000/api/schema/swagger-ui/
- ReDoc: http://localhost:8000/api/schema/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## 🎯 Funcionalidades Principales

### 1. Gestión de Datos Geoespaciales
- Conexión a múltiples fuentes de datos (WMS, WFS, Shapefile, GeoJSON)
- Sincronización automática
- Gestión de capas y estilos

### 2. Agentes de Análisis
- Agentes personalizables con prompts
- Ejecución programada o manual
- Integración con Gemini AI
- Sistema de calificación y retroalimentación

### 3. Monitoreo y Detección
- Detección de cambios en tiempo real
- Múltiples tipos de monitores
- Análisis de tendencias
- Comparación temporal

### 4. Sistema de Alertas
- Alertas multi-canal (Email, SMS, Webhook, Slack)
- Reglas de alerta configurables
- Suscripciones personalizadas
- Horas silenciosas

### 5. Automatización
- Workflows personalizables
- Tareas programadas
- Reglas de automatización
- Integración completa con todas las apps

## 🔒 Seguridad

- Autenticación JWT
- Permisos basados en roles
- Encriptación de datos sensibles
- Rate limiting
- CORS configurado

## 📈 Monitoreo y Logs

Los logs se guardan en:
- `debug.log` - Logs generales
- `logs/celery_worker.log` - Logs de Celery Worker
- `logs/celery_beat.log` - Logs de Celery Beat

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT.

## 👥 Equipo

Desarrollado por el equipo de SMGI.
