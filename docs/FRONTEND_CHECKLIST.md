# ✅ Checklist de Integración Frontend-Backend

## 🚀 Setup Inicial

### 1. Configuración del Entorno

- [ ] Clonar repositorio backend
- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Copiar `.env.example` a `.env`
- [ ] Configurar variables de entorno en `.env`:
  - [ ] DATABASE_URL
  - [ ] REDIS_URL
  - [ ] SECRET_KEY
  - [ ] EMAIL\_\* (opcional inicialmente)
  - [ ] TWILIO\_\* (opcional inicialmente)
  - [ ] FRONTEND_URL (URL de tu frontend)
- [ ] Crear base de datos PostgreSQL con PostGIS
- [ ] Ejecutar migraciones: `python manage.py migrate`
- [ ] Crear superusuario: `python manage.py createsuperuser`
- [ ] Iniciar servidor: `python manage.py runserver`
- [ ] Iniciar Redis: `redis-server`
- [ ] Iniciar Celery: `celery -A config worker -l info`

### 2. Verificación Backend

- [ ] Acceder a `http://localhost:8000/api/`
- [ ] Ver documentación: `http://localhost:8000/api/schema/swagger-ui/`
- [ ] Probar login con superusuario: `POST /api/v1/auth/token/`
- [ ] Verificar que el token funcione: `GET /api/v1/users/me/`

---

## 🔐 Autenticación

### Implementar JWT

- [ ] Crear servicio de autenticación
- [ ] Endpoint de login: `POST /api/v1/auth/token/`
- [ ] Guardar access y refresh tokens (localStorage/cookies)
- [ ] Implementar interceptor HTTP para agregar header:
  ```javascript
  Authorization: Bearer {accessToken}
  ```
- [ ] Implementar refresh automático de tokens
- [ ] Endpoint de refresh: `POST /api/v1/auth/token/refresh/`
- [ ] Implementar logout (limpiar tokens)
- [ ] Manejar 401 Unauthorized (redirect a login)

### Flujo de Registro

- [ ] Form de registro
- [ ] Endpoint: `POST /api/v1/users/register/`
- [ ] Validar campos requeridos:
  - username (email)
  - password
  - email
  - first_name, last_name
  - role (opcional, default: viewer)
- [ ] Mostrar errores de validación
- [ ] Redirect a login tras registro exitoso

---

## 👤 Gestión de Usuarios

### Perfil de Usuario

- [ ] Obtener perfil: `GET /api/v1/users/me/`
- [ ] Actualizar perfil: `PUT /api/v1/users/me/`
- [ ] Mostrar datos del usuario logueado
- [ ] Form de edición de perfil
- [ ] Cambio de contraseña (futuro)

### Listado de Usuarios (Admin/Manager)

- [ ] Listar usuarios: `GET /api/v1/users/`
- [ ] Filtros por rol: `?role=analyst`
- [ ] Búsqueda: `?search=nombre`
- [ ] Paginación: `?page=1&page_size=20`
- [ ] Ver detalle: `GET /api/v1/users/{id}/`
- [ ] Ver actividad: `GET /api/v1/users/{id}/activity-log/`

### Áreas

- [ ] Listar áreas: `GET /api/v1/users/areas/`
- [ ] Crear área: `POST /api/v1/users/areas/`
- [ ] Selector de área en forms

---

## 🗺️ Geodatos

### Capas Geográficas

- [ ] Listar capas: `GET /api/v1/geodata/layers/`
- [ ] Filtros:
  - `?is_active=true`
  - `?layer_type=vector`
  - `?search=nombre`
- [ ] Ver detalle: `GET /api/v1/geodata/layers/{id}/`
- [ ] Crear capa: `POST /api/v1/geodata/layers/`
- [ ] Actualizar capa: `PUT /api/v1/geodata/layers/{id}/`
- [ ] Eliminar capa: `DELETE /api/v1/geodata/layers/{id}/`

### Visualización en Mapa

- [ ] Obtener GeoJSON: `GET /api/v1/geodata/layers/{id}/export/geojson/`
- [ ] Integrar con librería de mapas (Leaflet/MapBox/OpenLayers)
- [ ] Mostrar capas en mapa
- [ ] Toggle visibility de capas
- [ ] Popup con información de features

### Export de Datos

- [ ] Botón de export
- [ ] Formatos disponibles:
  - [ ] GeoJSON: `/export/geojson/`
  - [ ] Shapefile: `/export/shapefile/`
  - [ ] KML: `/export/kml/`
  - [ ] CSV: `/export/csv/`
- [ ] Download automático del archivo

### Datasets y Fuentes

- [ ] Listar datasets: `GET /api/v1/geodata/datasets/`
- [ ] Listar fuentes: `GET /api/v1/geodata/sources/`
- [ ] Ver logs de sync: `GET /api/v1/geodata/sync-logs/`

---

## 🤖 Agentes

### Listado y Gestión

- [ ] Listar agentes: `GET /api/v1/agents/`
- [ ] Filtros por tipo: `?agent_type=analysis`
- [ ] Ver detalle: `GET /api/v1/agents/{id}/`
- [ ] Crear agente: `POST /api/v1/agents/`
- [ ] Actualizar: `PUT /api/v1/agents/{id}/`

### Ejecución

- [ ] Botón "Ejecutar"
- [ ] Endpoint: `POST /api/v1/agents/{id}/execute/`
- [ ] Mostrar estado de ejecución
- [ ] Ver historial: `GET /api/v1/agents/{id}/executions/`
- [ ] Ver logs de ejecución
- [ ] Estadísticas: `GET /api/v1/agents/{id}/statistics/`

---

## 📊 Monitoreo

### Proyectos

- [ ] Listar proyectos: `GET /api/v1/monitoring/projects/`
- [ ] Ver detalle: `GET /api/v1/monitoring/projects/{id}/`
- [ ] Crear proyecto: `POST /api/v1/monitoring/projects/`
- [ ] Dashboard de proyecto

### Monitores

- [ ] Listar monitores: `GET /api/v1/monitoring/monitors/`
- [ ] Filtrar por proyecto: `?project={id}`
- [ ] Ver detalle: `GET /api/v1/monitoring/monitors/{id}/`
- [ ] Ejecutar monitor: `POST /api/v1/monitoring/monitors/{id}/execute/`
- [ ] Toggle activo/inactivo

### Detecciones

- [ ] Listar detecciones: `GET /api/v1/monitoring/detections/`
- [ ] Filtros:
  - `?status=pending`
  - `?severity=high`
  - `?monitor={id}`
- [ ] Ver detalle: `GET /api/v1/monitoring/detections/{id}/`
- [ ] Revisar detección: `POST /api/v1/monitoring/detections/{id}/review/`
- [ ] Mostrar en mapa (geometrías)
- [ ] Ver cambios asociados

### Reportes

- [ ] Listar reportes: `GET /api/v1/monitoring/reports/`
- [ ] Generar reporte: `POST /api/v1/monitoring/reports/`
- [ ] Descargar PDF

---

## 🚨 Alertas

### Listado y Gestión

- [ ] Listar alertas: `GET /api/v1/alerts/alerts/`
- [ ] Filtros:
  - `?status=active`
  - `?severity=critical`
  - `?is_acknowledged=false`
- [ ] Ver detalle: `GET /api/v1/alerts/alerts/{id}/`
- [ ] Badge con contador de alertas activas

### Acciones

- [ ] Reconocer alerta: `POST /api/v1/alerts/alerts/{id}/acknowledge/`
- [ ] Resolver alerta: `POST /api/v1/alerts/alerts/{id}/resolve/`
- [ ] Agregar notas
- [ ] Historial de acciones

### Reglas

- [ ] Listar reglas: `GET /api/v1/alerts/rules/`
- [ ] Crear regla: `POST /api/v1/alerts/rules/`
- [ ] Editar regla: `PUT /api/v1/alerts/rules/{id}/`
- [ ] Toggle activo/inactivo

### Estadísticas

- [ ] Endpoint: `GET /api/v1/alerts/statistics/`
- [ ] Dashboard con métricas:
  - Total alertas
  - Por severidad
  - Por estado
  - Tendencias

---

## ⚙️ Automatización

### Workflows

- [ ] Listar workflows: `GET /api/v1/automation/workflows/`
- [ ] Ver detalle: `GET /api/v1/automation/workflows/{id}/`
- [ ] Crear workflow: `POST /api/v1/automation/workflows/`
- [ ] Ejecutar: `POST /api/v1/automation/workflows/{id}/execute/`

### Ejecuciones

- [ ] Listar ejecuciones: `GET /api/v1/automation/executions/`
- [ ] Ver detalle: `GET /api/v1/automation/executions/{id}/`
- [ ] Ver logs y tasks
- [ ] Indicador de progreso
- [ ] Cancelar ejecución (futuro)

### Estadísticas

- [ ] Endpoint: `GET /api/v1/automation/statistics/`
- [ ] Dashboard de workflows
- [ ] Tasa de éxito
- [ ] Tiempo promedio

---

## 🔔 Notificaciones

### Centro de Notificaciones

- [ ] Listar notificaciones: `GET /api/v1/notifications/`
- [ ] Filtrar no leídas: `?is_read=false`
- [ ] Contador: `GET /api/v1/notifications/unread-count/`
- [ ] Badge en navbar
- [ ] Dropdown con últimas notificaciones

### Acciones

- [ ] Marcar como leída: `POST /api/v1/notifications/{id}/mark-as-read/`
- [ ] Marcar todas: `POST /api/v1/notifications/mark-all-as-read/`
- [ ] Ver detalle: `GET /api/v1/notifications/{id}/`
- [ ] Auto-marcar al abrir

### Preferencias

- [ ] Obtener: `GET /api/v1/notifications/preferences/`
- [ ] Actualizar: `PUT /api/v1/notifications/preferences/`
- [ ] Toggle email/SMS
- [ ] Seleccionar tipos de notificación
- [ ] Horarios de envío (futuro)

---

## 🎨 UI/UX

### Componentes Globales

- [ ] Navbar con:
  - Logo
  - Menú de navegación
  - Badge de notificaciones
  - Usuario + dropdown (perfil/logout)
- [ ] Sidebar (opcional)
- [ ] Breadcrumbs
- [ ] Loading states
- [ ] Error boundaries

### Feedback

- [ ] Toast/Snackbar para mensajes
- [ ] Confirmaciones de acciones
- [ ] Spinners de carga
- [ ] Empty states
- [ ] Error states con retry

### Tablas y Listas

- [ ] Paginación
- [ ] Búsqueda
- [ ] Filtros avanzados
- [ ] Ordenamiento
- [ ] Acciones por fila
- [ ] Selección múltiple (futuro)

### Forms

- [ ] Validación en frontend
- [ ] Mostrar errores del backend
- [ ] Disabled durante submit
- [ ] Success feedback
- [ ] Auto-save (opcional)

---

## 📱 Responsive

- [ ] Mobile-first design
- [ ] Breakpoints para tablet/desktop
- [ ] Menú responsive
- [ ] Tablas scrollables en mobile
- [ ] Touch-friendly buttons
- [ ] Optimizar mapa para mobile

---

## 🧪 Testing

### Unit Tests

- [ ] Servicios API
- [ ] Helpers/Utilities
- [ ] Stores/State
- [ ] Componentes puros

### Integration Tests

- [ ] Flujos de login/logout
- [ ] CRUD operations
- [ ] Navegación entre páginas

### E2E Tests (Cypress/Playwright)

- [ ] Registro + login
- [ ] Crear capa
- [ ] Ejecutar agente
- [ ] Gestionar alertas
- [ ] Flujo completo de monitoreo

---

## 🚀 Performance

### Optimización

- [ ] Lazy loading de rutas
- [ ] Code splitting
- [ ] Image optimization
- [ ] Cachear datos estáticos
- [ ] Debounce en búsquedas
- [ ] Virtual scrolling en listas largas

### Monitoring

- [ ] Google Analytics / Mixpanel
- [ ] Error tracking (Sentry)
- [ ] Performance metrics
- [ ] User behavior tracking

---

## 🔍 SEO y PWA (Futuro)

- [ ] Meta tags apropiados
- [ ] Open Graph tags
- [ ] Sitemap
- [ ] Service Worker
- [ ] Offline support
- [ ] App manifest
- [ ] Push notifications

---

## 📚 Documentación Frontend

### Crear

- [ ] README.md con setup
- [ ] CONTRIBUTING.md
- [ ] Storybook (componentes)
- [ ] JSDoc/TSDoc en código
- [ ] Changelog

---

## 🐛 Manejo de Errores

### Errores HTTP

- [ ] 400 - Mostrar errores de validación
- [ ] 401 - Redirect a login
- [ ] 403 - Mensaje "Sin permisos"
- [ ] 404 - Página 404 custom
- [ ] 500 - Error genérico + reportar

### Network Errors

- [ ] Offline detection
- [ ] Timeout handling
- [ ] Retry automático (idempotente)
- [ ] Mensaje al usuario

---

## 🔐 Seguridad Frontend

- [ ] Sanitizar inputs
- [ ] XSS prevention
- [ ] CSRF tokens (si aplica)
- [ ] Validar permisos en UI
- [ ] No exponer tokens en logs
- [ ] HTTPS en producción
- [ ] Content Security Policy

---

## 🌐 Internacionalización (i18n)

### Futuro

- [ ] Configurar i18n library
- [ ] Traducir textos estáticos
- [ ] Formatear fechas por locale
- [ ] Formatear números/monedas
- [ ] Selector de idioma

---

## 📦 Build y Deploy

### Desarrollo

- [ ] Scripts de npm/yarn
- [ ] Variables de entorno (.env)
- [ ] Hot reload funcionando
- [ ] DevTools instalados

### Staging/Producción

- [ ] Build optimizado
- [ ] Minificación
- [ ] Tree shaking
- [ ] Environment variables
- [ ] CI/CD pipeline
- [ ] Docker (opcional)
- [ ] CDN para assets

---

## ✅ Pre-Launch Checklist

### Funcional

- [ ] Todos los endpoints probados
- [ ] Flujos críticos funcionando
- [ ] Sin errores en consola
- [ ] Tests pasando

### Performance

- [ ] Lighthouse score > 90
- [ ] Bundle size < 500KB (gzipped)
- [ ] First Contentful Paint < 2s
- [ ] Time to Interactive < 3s

### Seguridad

- [ ] Audit de dependencias
- [ ] HTTPS configurado
- [ ] Headers de seguridad
- [ ] Rate limiting (si aplica)

### UX

- [ ] Responsive en todos los dispositivos
- [ ] Navegación intuitiva
- [ ] Loading states claros
- [ ] Error messages útiles
- [ ] Accesibilidad básica (A11y)

---

## 🎯 Prioridades

### MVP (Mínimo Viable Product)

1. ✅ Autenticación (login/logout)
2. ✅ Ver capas en mapa
3. ✅ Listar alertas activas
4. ✅ Dashboard básico
5. ✅ Perfil de usuario

### Fase 2

1. Crear/editar capas
2. Ejecutar agentes
3. Gestionar monitores
4. Centro de notificaciones completo
5. Reportes

### Fase 3

1. Workflows automation
2. Analytics dashboard
3. Configuración avanzada
4. Mobile app
5. Real-time con WebSockets

---

## 📞 Soporte

**Documentación Backend:**

- `/docs/FRONTEND_INTEGRATION.md` - Guía completa
- `/docs/REVISION_SUMMARY.md` - Resumen ejecutivo
- `/schema.yml` - OpenAPI schema
- `http://localhost:8000/api/schema/swagger-ui/` - API docs interactiva

**Contacto:**

- Backend Team: [tu-email]
- Slack: #smgi-backend
- Issues: GitHub Issues

---

**¡Éxito con la integración! 🚀**
