"""
Utility functions for Agents app.
"""
from django.utils import timezone
from datetime import timedelta
from croniter import croniter


def calculate_next_run(schedule):
    """
    Calculate next run time for a schedule.
    
    Args:
        schedule: AgentSchedule instance
        
    Returns:
        datetime: Next run time
    """
    now = timezone.now()
    
    if schedule.schedule_type == 'interval':
        if schedule.last_run:
            next_run = schedule.last_run + timedelta(minutes=schedule.interval_minutes)
        else:
            next_run = now + timedelta(minutes=schedule.interval_minutes)
    
    elif schedule.schedule_type == 'cron':
        try:
            cron = croniter(schedule.cron_expression, now)
            next_run = cron.get_next(datetime)
        except Exception:
            # Invalid cron expression, default to 1 hour
            next_run = now + timedelta(hours=1)
    
    elif schedule.schedule_type == 'once':
        next_run = schedule.scheduled_time
    
    else:
        next_run = now + timedelta(hours=1)
    
    return next_run


def validate_agent_code(code):
    """
    Validate agent code for security and syntax.
    
    Args:
        code: Python code string
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check for dangerous imports
    dangerous_imports = [
        'subprocess',
        'os.system',
        'eval',
        'exec',
        '__import__',
    ]
    
    for dangerous in dangerous_imports:
        if dangerous in code:
            return False, f"Código contiene importación/función peligrosa: {dangerous}"
    
    # Try to compile the code
    try:
        compile(code, '<string>', 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Error de sintaxis: {str(e)}"
    except Exception as e:
        return False, f"Error al validar código: {str(e)}"


def get_agent_template(template_name):
    """
    Get a predefined agent template.
    
    Args:
        template_name: Name of the template
        
    Returns:
        dict: Template configuration
    """
    templates = {
        'change_detection': {
            'name': 'Detección de Cambios',
            'description': 'Detecta cambios entre dos capas temporales',
            'code': '''
# Agente de Detección de Cambios
import logging

logger = logging.getLogger(__name__)

# Obtener capas de entrada
if len(input_layers) < 2:
    raise ValueError("Se requieren al menos 2 capas para comparar")

layer1 = input_layers[0]
layer2 = input_layers[1]

logger.info(f"Comparando {layer1.name} con {layer2.name}")

# Obtener parámetros
threshold = parameters.get('threshold', 0.5)
logger.info(f"Umbral de cambio: {threshold}")

# TODO: Implementar lógica de detección de cambios

# Guardar resultados
output_data['changes_detected'] = 0
output_data['threshold'] = threshold
output_data['message'] = 'Análisis completado'

logger.info("Detección de cambios completada")
''',
            'parameters_schema': {
                'type': 'object',
                'properties': {
                    'threshold': {
                        'type': 'number',
                        'minimum': 0,
                        'maximum': 1,
                        'default': 0.5
                    }
                }
            }
        },
        'statistics': {
            'name': 'Estadísticas Básicas',
            'description': 'Calcula estadísticas básicas de una capa',
            'code': '''
# Agente de Estadísticas
import logging

logger = logging.getLogger(__name__)

# Obtener capa de entrada
if not input_layers:
    raise ValueError("Se requiere al menos 1 capa")

layer = input_layers[0]
logger.info(f"Calculando estadísticas para {layer.name}")

# Obtener features
features = layer.features.filter(is_active=True)
feature_count = features.count()

logger.info(f"Total de features: {feature_count}")

# Guardar resultados
output_data['feature_count'] = feature_count
output_data['layer_name'] = layer.name
output_data['geometry_type'] = layer.geometry_type
output_data['message'] = 'Estadísticas calculadas'

logger.info("Cálculo de estadísticas completado")
''',
            'parameters_schema': {
                'type': 'object',
                'properties': {}
            }
        }
    }
    
    return templates.get(template_name)
