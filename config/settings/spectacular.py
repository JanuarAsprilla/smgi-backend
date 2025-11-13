"""
Configuración mejorada para drf-spectacular.
"""

SPECTACULAR_SETTINGS = {
    'TITLE': 'SMGI API',
    'DESCRIPTION': '''
    # Sistema de Monitoreo Geoespacial Inteligente (SMGI)
    
    API REST completa para gestión de datos geoespaciales, monitoreo automatizado,
    agentes de IA, sistema de alertas y workflows de automatización.
    
    ## Características principales:
    
    - **Gestión de Datos Geoespaciales**: DataSources, Layers, Features con soporte PostGIS
    - **Agentes de IA**: Análisis automatizado con LLMs (Gemini, GPT, Claude)
    - **Sistema de Monitoreo**: Detección de cambios, umbrales, anomalías
    - **Alertas Inteligentes**: Múltiples canales (email, SMS, webhook, in-app)
    - **Automatización**: Workflows configurables con tareas dependientes
    - **Autenticación JWT**: Tokens de acceso y refresh
    
    ## Autenticación:
    
    1. Obtén un token en `/api/v1/users/login/`
    2. Usa el token en el header: `Authorization: Bearer <token>`
    3. Refresca el token en `/api/v1/users/token/refresh/`
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    
    # Configuración de autenticación
    'SECURITY': [
        {
            'BearerAuth': []
        }
    ],
    
    'SECURITY_DEFINITIONS': {
        'BearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': 'Token JWT obtenido del endpoint /api/v1/users/login/'
        }
    },
    
    # Prefijos de path
    'SCHEMA_PATH_PREFIX': '/api/v[0-9]',
    
    # Configuración de Swagger UI
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'tryItOutEnabled': True,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'docExpansion': 'list',
        'tagsSorter': 'alpha',
        'operationsSorter': 'alpha',
    },
    
    # Configuración de tags
    'TAGS': [
        {'name': 'users', 'description': 'Gestión de usuarios y autenticación'},
        {'name': 'geodata', 'description': 'Datos geoespaciales (DataSources, Layers, Features)'},
        {'name': 'agents', 'description': 'Agentes de IA para análisis'},
        {'name': 'monitoring', 'description': 'Sistema de monitoreo y detección de cambios'},
        {'name': 'alerts', 'description': 'Sistema de alertas y notificaciones'},
        {'name': 'automation', 'description': 'Workflows y automatización'},
    ],
    
    # Enums
    'ENUM_NAME_OVERRIDES': {
        'RoleEnum': 'apps.users.models.User.Role',
        'SourceTypeEnum': 'apps.geodata.models.DataSource.SourceType',
        'StatusEnum': 'apps.geodata.models.DataSource.Status',
        'LayerTypeEnum': 'apps.geodata.models.Layer.LayerType',
        'GeometryTypeEnum': 'apps.geodata.models.Layer.GeometryType',
        'AgentTypeEnum': 'apps.agents.models.Agent.AgentType',
        'MonitorTypeEnum': 'apps.monitoring.models.Monitor.MonitorType',
        'SeverityEnum': 'apps.alerts.models.AlertRule.Severity',
        'ChannelTypeEnum': 'apps.alerts.models.AlertChannel.ChannelType',
    },
    
    # Configuración de componentes
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
    
    # Preprocessing hooks
    'PREPROCESSING_HOOKS': [
        'drf_spectacular.hooks.preprocess_exclude_path_format',
    ],
    
    # Postprocessing hooks
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields',
    ],
    
    # Otras configuraciones
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
    
    # Deshabilitar algunas advertencias
    'DISABLE_ERRORS_AND_WARNINGS': False,
}
