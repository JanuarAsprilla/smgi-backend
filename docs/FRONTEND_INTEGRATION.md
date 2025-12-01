# Guía de Integración con Frontend

## Estado del Sistema

✅ **Sistema 100% funcional y listo para integración con frontend**

- Todas las aplicaciones revisadas y corregidas
- Schema OpenAPI generado exitosamente (`schema.yml`)
- Sin errores críticos de deployment
- Migraciones actualizadas
- Configuración completa

---

## Arquitectura del Backend

### Apps Principales

1. **users** - Gestión de usuarios, roles y áreas
2. **geodata** - Capas geográficas, datasets, fuentes de datos
3. **agents** - Agentes de procesamiento y sus ejecuciones
4. **monitoring** - Proyectos de monitoreo, detecciones y cambios
5. **alerts** - Sistema de alertas con reglas y notificaciones
6. **automation** - Workflows y automatización de tareas
7. **notifications** - Notificaciones email/SMS con preferencias
8. **core** - Utilidades compartidas y tareas base

### Stack Tecnológico

- Django 4.2.7
- Django REST Framework 3.14.0
- PostgreSQL 15 + PostGIS 3.3
- Celery 5.3.4 (Redis broker)
- Python 3.12

---

## Autenticación

### JWT Authentication

**Endpoints:**

- `POST /api/v1/auth/token/` - Obtener access + refresh tokens
- `POST /api/v1/auth/token/refresh/` - Renovar access token
- `POST /api/v1/auth/token/verify/` - Verificar token

**Registro de Usuario:**

```bash
POST /api/v1/users/register/
Content-Type: application/json

{
  "username": "usuario@example.com",
  "password": "password123",
  "email": "usuario@example.com",
  "first_name": "Nombre",
  "last_name": "Apellido",
  "role": "analyst"
}
```

**Login:**

```bash
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "usuario@example.com",
  "password": "password123"
}

# Response:
{
  "access": "eyJ0eXAiOiJKV1QiLC...",
  "refresh": "eyJ0eXAiOiJKV1QiLC..."
}
```

**Uso del Token:**

```bash
GET /api/v1/users/me/
Authorization: Bearer eyJ0eXAiOiJKV1QiLC...
```

**Duración de Tokens:**

- Access Token: 60 minutos
- Refresh Token: 7 días

---

## API Endpoints

### Base URL

```
http://localhost:8000/api/v1/
```

### 1. Users (`/api/v1/users/`)

**Endpoints:**

- `GET /users/` - Listar usuarios (admin/manager)
- `GET /users/me/` - Perfil del usuario actual
- `PUT /users/me/` - Actualizar perfil
- `POST /users/register/` - Registro de usuario
- `GET /users/{id}/` - Detalle de usuario
- `GET /users/{id}/activity-log/` - Log de actividad
- `GET /areas/` - Listar áreas
- `POST /areas/` - Crear área

**Roles disponibles:**

- `admin` - Administrador del sistema
- `manager` - Gestor de proyectos
- `analyst` - Analista de datos
- `viewer` - Solo visualización

**Ejemplo - Obtener perfil:**

```javascript
fetch("http://localhost:8000/api/v1/users/me/", {
  headers: {
    Authorization: "Bearer " + accessToken,
    "Content-Type": "application/json",
  },
});
```

---

### 2. Geodata (`/api/v1/geodata/`)

**Endpoints principales:**

- `GET /geodata/layers/` - Listar capas geográficas
- `GET /geodata/layers/{id}/` - Detalle de capa
- `POST /geodata/layers/` - Crear capa
- `GET /geodata/layers/{id}/export/{format}/` - Exportar capa
  - Formatos: `geojson`, `shapefile`, `kml`, `csv`
- `POST /geodata/layers/{id}/upload/` - Subir datos a capa
- `GET /geodata/datasets/` - Listar datasets
- `GET /geodata/sources/` - Listar fuentes de datos
- `GET /geodata/sync-logs/` - Logs de sincronización

**Filtros disponibles:**

- `?is_active=true` - Solo capas activas
- `?layer_type=vector` - Filtrar por tipo (vector/raster)
- `?search=nombre` - Búsqueda por nombre/descripción
- `?ordering=-created_at` - Ordenar resultados

**Ejemplo - Listar capas:**

```javascript
const layers = await fetch(
  "http://localhost:8000/api/v1/geodata/layers/?is_active=true",
  {
    headers: {
      Authorization: "Bearer " + accessToken,
    },
  }
).then((res) => res.json());
```

**Ejemplo - Exportar capa como GeoJSON:**

```javascript
const geojson = await fetch(
  "http://localhost:8000/api/v1/geodata/layers/1/export/geojson/",
  {
    headers: {
      Authorization: "Bearer " + accessToken,
    },
  }
).then((res) => res.json());
```

---

### 3. Agents (`/api/v1/agents/`)

**Endpoints:**

- `GET /agents/` - Listar agentes
- `GET /agents/{id}/` - Detalle de agente
- `POST /agents/` - Crear agente
- `POST /agents/{id}/execute/` - Ejecutar agente
- `GET /agents/{id}/executions/` - Historial de ejecuciones
- `GET /executions/` - Todas las ejecuciones
- `GET /executions/{id}/` - Detalle de ejecución

**Tipos de agentes:**

- `data_import` - Importación de datos
- `data_processing` - Procesamiento de datos
- `analysis` - Análisis geoespacial
- `monitoring` - Monitoreo de cambios
- `export` - Exportación de datos
- `notification` - Envío de notificaciones

**Ejemplo - Ejecutar agente:**

```javascript
await fetch("http://localhost:8000/api/v1/agents/1/execute/", {
  method: "POST",
  headers: {
    Authorization: "Bearer " + accessToken,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    parameters: {
      layer_id: 5,
      threshold: 0.8,
    },
  }),
});
```

---

### 4. Monitoring (`/api/v1/monitoring/`)

**Endpoints:**

- `GET /monitoring/projects/` - Proyectos de monitoreo
- `GET /monitoring/projects/{id}/` - Detalle de proyecto
- `POST /monitoring/projects/` - Crear proyecto
- `GET /monitoring/monitors/` - Monitores activos
- `POST /monitoring/monitors/` - Crear monitor
- `POST /monitoring/monitors/{id}/execute/` - Ejecutar monitor
- `GET /monitoring/detections/` - Detecciones de cambios
- `GET /monitoring/detections/{id}/` - Detalle de detección
- `POST /monitoring/detections/{id}/review/` - Revisar detección
- `GET /monitoring/change-records/` - Registros de cambios
- `GET /monitoring/reports/` - Reportes de monitoreo

**Estados de detección:**

- `pending` - Pendiente de revisión
- `confirmed` - Confirmado
- `false_positive` - Falso positivo
- `resolved` - Resuelto

**Ejemplo - Listar detecciones pendientes:**

```javascript
const detections = await fetch(
  "http://localhost:8000/api/v1/monitoring/detections/?status=pending&ordering=-detected_at",
  {
    headers: { Authorization: "Bearer " + accessToken },
  }
).then((res) => res.json());
```

---

### 5. Alerts (`/api/v1/alerts/`)

**Endpoints:**

- `GET /alerts/alerts/` - Listar alertas
- `GET /alerts/alerts/{id}/` - Detalle de alerta
- `POST /alerts/alerts/{id}/acknowledge/` - Reconocer alerta
- `POST /alerts/alerts/{id}/resolve/` - Resolver alerta
- `GET /alerts/rules/` - Reglas de alertas
- `POST /alerts/rules/` - Crear regla
- `GET /alerts/statistics/` - Estadísticas de alertas

**Severidades:**

- `info` - Informativa
- `warning` - Advertencia
- `error` - Error
- `critical` - Crítica

**Filtros útiles:**

- `?status=active` - Alertas activas
- `?severity=critical` - Por severidad
- `?is_acknowledged=false` - No reconocidas
- `?created_at__gte=2024-01-01` - Desde fecha

**Ejemplo - Reconocer alerta:**

```javascript
await fetch("http://localhost:8000/api/v1/alerts/alerts/1/acknowledge/", {
  method: "POST",
  headers: {
    Authorization: "Bearer " + accessToken,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    notes: "Revisando el problema",
  }),
});
```

---

### 6. Automation (`/api/v1/automation/`)

**Endpoints:**

- `GET /automation/workflows/` - Workflows disponibles
- `GET /automation/workflows/{id}/` - Detalle de workflow
- `POST /automation/workflows/` - Crear workflow
- `POST /automation/workflows/{id}/execute/` - Ejecutar workflow
- `GET /automation/executions/` - Ejecuciones de workflows
- `GET /automation/executions/{id}/` - Detalle de ejecución
- `GET /automation/statistics/` - Estadísticas

**Estados de ejecución:**

- `pending` - Pendiente
- `running` - En ejecución
- `completed` - Completado
- `failed` - Fallido
- `cancelled` - Cancelado

**Ejemplo - Ejecutar workflow:**

```javascript
await fetch("http://localhost:8000/api/v1/automation/workflows/1/execute/", {
  method: "POST",
  headers: {
    Authorization: "Bearer " + accessToken,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    parameters: {
      input_layer: 3,
      output_format: "geojson",
    },
  }),
});
```

---

### 7. Notifications (`/api/v1/notifications/`)

**Endpoints:**

- `GET /notifications/` - Listar notificaciones
- `GET /notifications/{id}/` - Detalle de notificación
- `POST /notifications/{id}/mark-as-read/` - Marcar como leída
- `POST /notifications/mark-all-as-read/` - Marcar todas
- `GET /notifications/preferences/` - Preferencias de usuario
- `PUT /notifications/preferences/` - Actualizar preferencias
- `GET /notifications/unread-count/` - Contador de no leídas

**Tipos de notificación:**

- `info` - Informativa
- `success` - Éxito
- `warning` - Advertencia
- `error` - Error

**Ejemplo - Obtener notificaciones no leídas:**

```javascript
const notifications = await fetch(
  "http://localhost:8000/api/v1/notifications/?is_read=false&ordering=-created_at",
  {
    headers: { Authorization: "Bearer " + accessToken },
  }
).then((res) => res.json());
```

**Ejemplo - Actualizar preferencias:**

```javascript
await fetch("http://localhost:8000/api/v1/notifications/preferences/", {
  method: "PUT",
  headers: {
    Authorization: "Bearer " + accessToken,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    email_enabled: true,
    sms_enabled: false,
    notification_types: {
      alert_created: true,
      detection_found: true,
      workflow_completed: true,
    },
  }),
});
```

---

## Schema OpenAPI

**Documentación interactiva:**

- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- Schema JSON: `http://localhost:8000/api/schema/`
- Schema YAML: `/schema.yml` (archivo generado)

---

## CORS Configuration

El backend está configurado para aceptar requests desde el frontend local:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
]

CORS_ALLOW_CREDENTIALS = True
```

**Headers permitidos:**

- Authorization
- Content-Type
- Accept
- X-Requested-With

---

## Paginación

Todas las listas usan paginación por defecto:

**Parámetros:**

- `?page=1` - Número de página
- `?page_size=10` - Elementos por página (máx: 100)

**Formato de respuesta:**

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/resource/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## Filtros y Búsqueda

**Búsqueda general:**

```
?search=término
```

**Filtros específicos:**

```
?is_active=true
?status=active
?created_at__gte=2024-01-01
?created_at__lte=2024-12-31
```

**Ordenamiento:**

```
?ordering=created_at        # Ascendente
?ordering=-created_at       # Descendente
?ordering=name,-created_at  # Múltiple
```

---

## Manejo de Errores

### Códigos HTTP

- `200` - Éxito
- `201` - Creado
- `204` - Sin contenido (delete exitoso)
- `400` - Bad Request (validación fallida)
- `401` - No autenticado
- `403` - Sin permisos
- `404` - No encontrado
- `500` - Error del servidor

### Formato de Error

```json
{
  "detail": "Mensaje de error",
  "errors": {
    "field_name": ["Error específico del campo"]
  }
}
```

**Ejemplo:**

```json
{
  "detail": "Validación fallida",
  "errors": {
    "email": ["Este campo es requerido"],
    "password": ["La contraseña debe tener al menos 8 caracteres"]
  }
}
```

---

## WebSockets (Futuro)

El sistema está preparado para añadir WebSockets para:

- Notificaciones en tiempo real
- Actualizaciones de ejecuciones de agentes/workflows
- Cambios en detecciones de monitoreo
- Actualizaciones de alertas

---

## Variables de Entorno Requeridas

Archivo `.env` (basado en `.env.example`):

```bash
# Django
SECRET_KEY=tu-secret-key-super-segura
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=smgi_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password

# Twilio (SMS)
TWILIO_ACCOUNT_SID=tu-account-sid
TWILIO_AUTH_TOKEN=tu-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Frontend
FRONTEND_URL=http://localhost:3000

# AWS (opcional - para storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
```

---

## Comandos de Desarrollo

### Iniciar servidor

```bash
python manage.py runserver
```

### Iniciar Celery worker

```bash
celery -A config worker -l info
```

### Iniciar Celery beat (tareas programadas)

```bash
celery -A config beat -l info
```

### Crear superusuario

```bash
python manage.py createsuperuser
```

### Ejecutar migraciones

```bash
python manage.py migrate
```

### Generar schema OpenAPI

```bash
python manage.py spectacular --file schema.yml
```

---

## Testing

### Ejecutar tests

```bash
pytest
```

### Con cobertura

```bash
pytest --cov=apps --cov-report=html
```

### Tests específicos

```bash
pytest apps/users/tests.py
pytest apps/geodata/tests.py -v
```

---

## Datos de Prueba

### Crear datos de ejemplo

```bash
python manage.py shell
from apps.users.models import User
user = User.objects.create_user(
    username='test@example.com',
    email='test@example.com',
    password='test123',
    role='analyst'
)
```

---

## Performance Tips

1. **Usar paginación** en todas las listas
2. **Limitar campos** con `?fields=id,name,status`
3. **Prefetch relacionados** - el backend ya lo hace automáticamente
4. **Cachear datos estáticos** (áreas, tipos, etc)
5. **Usar WebSockets** para actualizaciones en tiempo real (cuando esté disponible)

---

## Seguridad

### Headers requeridos

- `Authorization: Bearer {token}` - En TODAS las requests autenticadas
- `Content-Type: application/json` - Para POST/PUT/PATCH

### Refresh de tokens

Los access tokens expiran en 60 minutos. Implementar refresh automático:

```javascript
async function refreshToken(refreshToken) {
  const response = await fetch(
    "http://localhost:8000/api/v1/auth/token/refresh/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    }
  );
  const data = await response.json();
  return data.access; // Nuevo access token
}
```

### Logout

Simplemente eliminar los tokens del cliente. No hay endpoint de logout en JWT.

---

## Checklist de Integración

- [ ] Configurar variables de entorno
- [ ] Implementar autenticación JWT
- [ ] Implementar refresh automático de tokens
- [ ] Configurar interceptor para Authorization header
- [ ] Implementar manejo de errores global
- [ ] Configurar paginación
- [ ] Implementar búsqueda y filtros
- [ ] Manejar estados de carga
- [ ] Mostrar notificaciones/toasts para feedback
- [ ] Implementar polling para actualizaciones (o WebSockets)
- [ ] Cachear datos estáticos
- [ ] Implementar logout y limpieza de tokens

---

## Soporte

Para dudas o problemas:

1. Revisar documentación interactiva: `/api/schema/swagger-ui/`
2. Ver schema OpenAPI: `/schema.yml`
3. Revisar logs del servidor
4. Contactar al equipo de backend

---

## Próximos Pasos

1. ✅ Backend completamente funcional
2. 🔄 Integración con frontend
3. 🔄 Testing E2E
4. 🔜 WebSockets para tiempo real
5. 🔜 Notificaciones push
6. 🔜 Export masivo de datos
7. 🔜 Panel de analytics avanzado

---

**Última actualización:** 2024-11-30  
**Versión del Backend:** 1.0.0  
**Django:** 4.2.7  
**DRF:** 3.14.0
