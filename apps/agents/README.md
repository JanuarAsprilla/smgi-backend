# Agents App - SMGI

## Descripción

La app **Agents** proporciona un sistema completo para crear, gestionar y ejecutar agentes de análisis geoespacial. Los agentes son componentes reutilizables que pueden realizar análisis automatizados sobre datos geográficos.

## Características Principales

### 1. Gestión de Agentes

- **Creación y edición** de agentes personalizados
- **Categorización** para organizar agentes
- **Versionado** de agentes
- **Marketplace** de agentes públicos
- **Sistema de calificaciones** y comentarios

### 2. Ejecución de Agentes

- Ejecución **asíncrona** mediante Celery
- **Seguimiento en tiempo real** del estado
- **Logs detallados** de cada ejecución
- **Métricas de rendimiento** (tiempo, memoria)
- **Gestión de resultados** y capas de salida

### 3. Programación Automática

- **Schedules** con múltiples tipos:
  - Intervalo (cada X minutos)
  - Cron (expresiones cron)
  - Una vez (fecha/hora específica)
- **Gestión automática** de próximas ejecuciones
- **Historial** de ejecuciones programadas

### 4. Plantillas de Agentes

- **Templates predefinidos** para casos comunes
- **Clonación** de agentes existentes
- **Personalización** fácil

## Modelos

### AgentCategory

Categorías para organizar agentes.

**Campos principales:**

- `name`: Nombre de la categoría
- `description`: Descripción
- `icon`: Icono representativo
- `color`: Color en formato hexadecimal

### Agent

Modelo principal de agentes de análisis.

**Campos principales:**

- `name`: Nombre del agente
- `description`: Descripción detallada
- `agent_type`: Tipo (detección de cambios, clasificación, etc.)
- `code`: Código Python del agente
- `parameters_schema`: JSON Schema para validar parámetros
- `status`: Estado (draft, published, archived)
- `is_public`: Si es visible en marketplace
- `is_verified`: Si está verificado por SMGI

**Estadísticas:**

- `execution_count`: Número total de ejecuciones
- `success_count`: Ejecuciones exitosas
- `failure_count`: Ejecuciones fallidas
- `rating`: Calificación promedio
- `downloads`: Número de descargas

### AgentExecution

Registro de ejecuciones de agentes.

**Campos principales:**

- `agent`: Agente ejecutado
- `status`: Estado (pending, running, success, failed, cancelled)
- `parameters`: Parámetros de entrada
- `input_layers`: Capas de entrada
- `input_datasets`: Datasets de entrada
- `output_data`: Datos de salida
- `logs`: Logs de ejecución
- `processing_time`: Tiempo de procesamiento

### AgentSchedule

Programación automática de agentes.

**Campos principales:**

- `agent`: Agente a ejecutar
- `schedule_type`: Tipo (interval, cron, once)
- `interval_minutes`: Intervalo en minutos
- `cron_expression`: Expresión cron
- `scheduled_time`: Fecha/hora programada
- `is_enabled`: Si está habilitado
- `next_run`: Próxima ejecución calculada

### AgentRating

Calificaciones de usuarios para agentes.

**Campos principales:**

- `agent`: Agente calificado
- `user`: Usuario que califica
- `rating`: Calificación (1-5)
- `comment`: Comentario opcional

### AgentTemplate

Plantillas predefinidas de agentes.

**Campos principales:**

- `name`: Nombre de la plantilla
- `code_template`: Código con placeholders
- `parameters_schema`: Esquema de parámetros
- `is_featured`: Si es destacada

## API Endpoints

### Categorías

- `GET /api/v1/agents/categories/` - Listar categorías
- `POST /api/v1/agents/categories/` - Crear categoría
- `GET /api/v1/agents/categories/{id}/` - Detalle de categoría
- `PUT /api/v1/agents/categories/{id}/` - Actualizar categoría
- `DELETE /api/v1/agents/categories/{id}/` - Eliminar categoría

### Agentes

- `GET /api/v1/agents/agents/` - Listar agentes
- `POST /api/v1/agents/agents/` - Crear agente
- `GET /api/v1/agents/agents/{id}/` - Detalle de agente
- `PUT /api/v1/agents/agents/{id}/` - Actualizar agente
- `DELETE /api/v1/agents/agents/{id}/` - Eliminar agente
- `POST /api/v1/agents/agents/{id}/execute/` - Ejecutar agente
- `POST /api/v1/agents/agents/{id}/publish/` - Publicar agente
- `POST /api/v1/agents/agents/{id}/archive/` - Archivar agente
- `POST /api/v1/agents/agents/{id}/clone/` - Clonar agente
- `POST /api/v1/agents/agents/{id}/rate/` - Calificar agente
- `GET /api/v1/agents/agents/{id}/ratings/` - Ver calificaciones
- `GET /api/v1/agents/agents/{id}/executions/` - Ver ejecuciones
- `GET /api/v1/agents/agents/marketplace/` - Marketplace público
- `GET /api/v1/agents/agents/statistics/` - Estadísticas generales

### Ejecuciones

- `GET /api/v1/agents/executions/` - Listar ejecuciones
- `POST /api/v1/agents/executions/` - Crear ejecución
- `GET /api/v1/agents/executions/{id}/` - Detalle de ejecución
- `POST /api/v1/agents/executions/{id}/cancel/` - Cancelar ejecución
- `POST /api/v1/agents/executions/{id}/retry/` - Reintentar ejecución

### Programaciones

- `GET /api/v1/agents/schedules/` - Listar programaciones
- `POST /api/v1/agents/schedules/` - Crear programación
- `GET /api/v1/agents/schedules/{id}/` - Detalle de programación
- `PUT /api/v1/agents/schedules/{id}/` - Actualizar programación
- `DELETE /api/v1/agents/schedules/{id}/` - Eliminar programación
- `POST /api/v1/agents/schedules/{id}/enable/` - Habilitar programación
- `POST /api/v1/agents/schedules/{id}/disable/` - Deshabilitar programación
- `POST /api/v1/agents/schedules/{id}/run_now/` - Ejecutar ahora

### Templates

- `GET /api/v1/agents/templates/` - Listar templates
- `GET /api/v1/agents/templates/{id}/` - Detalle de template
- `POST /api/v1/agents/templates/{id}/use/` - Usar template
- `GET /api/v1/agents/templates/featured/` - Templates destacados

## Permisos

### Roles de Usuario

- **viewer**: Solo puede ver agentes públicos
- **analyst**: Puede ejecutar agentes y crear programaciones
- **developer**: Puede crear, editar y publicar agentes
- **admin**: Acceso completo

### Permisos Personalizados

- `CanExecuteAgent`: Verificar si puede ejecutar un agente
- `CanManageAgent`: Verificar si puede editar/eliminar un agente
- `CanPublishAgent`: Verificar si puede publicar un agente
- `CanScheduleAgent`: Verificar si puede programar ejecuciones

## Validadores

### validate_agent_code

Valida el código Python del agente para seguridad:

- Detecta imports y funciones peligrosas
- Verifica sintaxis correcta
- Previene inyección de código

### validate_cron_expression

Valida expresiones cron usando croniter.

### validate_json_schema

Valida que el schema sea JSON válido y tenga estructura correcta.

### validate_parameters

Valida parámetros contra JSON Schema definido.

### validate_agent_requirements

Valida lista de dependencias y detecta paquetes peligrosos.

## Tareas Celery

### execute_agent

Ejecuta un agente de forma asíncrona.

- Prepara el entorno de ejecución
- Ejecuta el código del agente
- Captura logs y resultados
- Actualiza estadísticas

### schedule_agent_execution

Ejecuta un agente programado.

### process_scheduled_agents

Procesa todos los schedules que deben ejecutarse (se ejecuta cada minuto).

### cleanup_old_executions

Limpia ejecuciones antiguas (por defecto 30 días).

### update_agent_statistics

Actualiza estadísticas de todos los agentes (diario).

### calculate_agent_ratings

Recalcula calificaciones promedio de agentes (cada hora).

## Signals

### agent_post_save

- Notifica cuando se crea un nuevo agente
- Notifica cuando se publica un agente

### agent_execution_post_save

- Envía notificación cuando termina una ejecución

### agent_rating_post_save

- Actualiza calificación promedio del agente

### agent_rating_pre_delete

- Recalcula calificación al eliminar una calificación

## Uso Básico

### Crear un Agente

```python
from apps.agents.models import Agent, AgentCategory

# Crear categoría
category = AgentCategory.objects.create(
    name="Análisis",
    description="Agentes de análisis estadístico",
    icon="chart",
    color="#3B82F6"
)

# Crear agente
agent = Agent.objects.create(
    name="Contador de Features",
    description="Cuenta features en una capa",
    category=category,
    agent_type="statistics",
    code="""
import logging
logger = logging.getLogger(__name__)

layer = input_layers[0]
count = layer.features.count()

output_data['feature_count'] = count
logger.info(f"Total features: {count}")
""",
    parameters_schema={
        "type": "object",
        "properties": {}
    },
    status="published",
    is_public=True,
    created_by=user
)
```

### Ejecutar un Agente

```python
from apps.agents.models import AgentExecution
from apps.agents.tasks import execute_agent

# Crear ejecución
execution = AgentExecution.objects.create(
    agent=agent,
    name="Mi ejecución",
    parameters={},
    created_by=user
)

# Añadir capas de entrada
execution.input_layers.add(layer1, layer2)

# Lanzar tarea asíncrona
task = execute_agent.delay(execution.id)
execution.task_id = task.id
execution.save()
```

### Programar Ejecución

```python
from apps.agents.models import AgentSchedule
from apps.agents.utils import calculate_next_run

# Programación con intervalo
schedule = AgentSchedule.objects.create(
    agent=agent,
    name="Análisis diario",
    schedule_type="interval",
    interval_minutes=1440,  # 24 horas
    parameters={},
    is_enabled=True,
    created_by=user
)

# Calcular próxima ejecución
schedule.next_run = calculate_next_run(schedule)
schedule.save()
```

## Testing

Ejecutar tests de la app:

```bash
python manage.py test apps.agents
```

Tests con cobertura:

```bash
pytest apps/agents/tests.py --cov=apps.agents --cov-report=html
```

## Configuración en settings.py

```python
# Agregar a INSTALLED_APPS
INSTALLED_APPS = [
    # ...
    'apps.agents',
]

# Configuración de Celery Beat
CELERY_BEAT_SCHEDULE = {
    'process-scheduled-agents': {
        'task': 'apps.agents.tasks.process_scheduled_agents',
        'schedule': crontab(minute='*/1'),
    },
    'update-agent-statistics': {
        'task': 'apps.agents.tasks.update_agent_statistics',
        'schedule': crontab(hour=0, minute=0),
    },
    'calculate-agent-ratings': {
        'task': 'apps.agents.tasks.calculate_agent_ratings',
        'schedule': crontab(minute=0),
    },
    'cleanup-old-executions': {
        'task': 'apps.agents.tasks.cleanup_old_executions',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

## Notas de Seguridad

1. El código de los agentes se valida para prevenir inyección de código
2. Se bloquean imports y funciones peligrosas
3. Solo usuarios con rol 'developer' o superior pueden crear agentes
4. Los agentes deben ser publicados para ser ejecutados
5. Las ejecuciones se aíslan en un entorno controlado

## Mejoras Futuras

- [ ] Sandbox más robusto para ejecución de código
- [ ] Sistema de plugins para extender funcionalidad
- [ ] Versionado completo de agentes
- [ ] Rollback de versiones
- [ ] Análisis de dependencias automático
- [ ] Sistema de recomendaciones de agentes
- [ ] Integración con notebooks Jupyter
- [ ] Visualización de resultados en tiempo real
