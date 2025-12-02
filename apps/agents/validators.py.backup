"""
Validators for Agents app.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_agent_code(code):
    """
    Validate agent code for security and correctness.
    
    Args:
        code: Python code string
        
    Raises:
        ValidationError: If code contains dangerous patterns
    """
    if not code or not code.strip():
        raise ValidationError(_('El código del agente no puede estar vacío.'))
    
    # Check for dangerous imports and functions
    dangerous_patterns = [
        r'\bos\.system\b',
        r'\bsubprocess\b',
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'\b__import__\b',
        r'\bopen\s*\(',
        r'\bfile\s*\(',
        # MODIFICADO: Solo detectar input() como función, no input_layers o input_data
        r'(?<![_a-zA-Z])input\s*\(',  # input( pero no algo_input(
        r'\braw_input\s*\(',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            raise ValidationError(
                _('El código contiene patrones peligrosos: %(pattern)s'),
                params={'pattern': pattern}
            )
    
    # Try to compile the code
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        raise ValidationError(
            _('Error de sintaxis en el código: %(error)s'),
            params={'error': str(e)}
        )
    except Exception as e:
        raise ValidationError(
            _('Error al validar el código: %(error)s'),
            params={'error': str(e)}
        )


def validate_cron_expression(expression):
    """
    Validate cron expression format.
    
    Args:
        expression: Cron expression string
        
    Raises:
        ValidationError: If expression is invalid
    """
    if not expression or not expression.strip():
        raise ValidationError(_('La expresión cron no puede estar vacía.'))
    
    from croniter import croniter
    
    try:
        croniter(expression)
    except Exception as e:
        raise ValidationError(
            _('Expresión cron inválida: %(error)s'),
            params={'error': str(e)}
        )


def validate_json_schema(schema):
    """
    Validate JSON Schema format.
    
    Args:
        schema: JSON Schema dict
        
    Raises:
        ValidationError: If schema is invalid
    """
    if not isinstance(schema, dict):
        raise ValidationError(_('El esquema debe ser un objeto JSON válido.'))
    
    # Basic JSON Schema validation
    if 'type' not in schema:
        raise ValidationError(_('El esquema debe tener un campo "type".'))
    
    valid_types = ['object', 'array', 'string', 'number', 'integer', 'boolean', 'null']
    if schema['type'] not in valid_types:
        raise ValidationError(
            _('Tipo de esquema inválido: %(type)s'),
            params={'type': schema['type']}
        )


def validate_parameters(parameters, schema):
    """
    Validate parameters against JSON Schema.
    
    Args:
        parameters: Parameters dict
        schema: JSON Schema dict
        
    Raises:
        ValidationError: If parameters don't match schema
    """
    if not isinstance(parameters, dict):
        raise ValidationError(_('Los parámetros deben ser un objeto JSON válido.'))
    
    if not schema:
        return  # No schema to validate against
    
    # Basic validation - check required fields
    if 'required' in schema:
        for required_field in schema['required']:
            if required_field not in parameters:
                raise ValidationError(
                    _('Falta el parámetro requerido: %(field)s'),
                    params={'field': required_field}
                )
    
    # Validate properties if defined
    if 'properties' in schema:
        for param_name, param_value in parameters.items():
            if param_name in schema['properties']:
                prop_schema = schema['properties'][param_name]
                validate_parameter_value(param_name, param_value, prop_schema)


def validate_parameter_value(name, value, schema):
    """
    Validate a single parameter value against its schema.
    
    Args:
        name: Parameter name
        value: Parameter value
        schema: Parameter schema
        
    Raises:
        ValidationError: If value doesn't match schema
    """
    param_type = schema.get('type')
    
    if param_type == 'string' and not isinstance(value, str):
        raise ValidationError(
            _('El parámetro "%(name)s" debe ser una cadena de texto'),
            params={'name': name}
        )
    
    if param_type == 'number' and not isinstance(value, (int, float)):
        raise ValidationError(
            _('El parámetro "%(name)s" debe ser un número'),
            params={'name': name}
        )
    
    if param_type == 'integer' and not isinstance(value, int):
        raise ValidationError(
            _('El parámetro "%(name)s" debe ser un entero'),
            params={'name': name}
        )
    
    if param_type == 'boolean' and not isinstance(value, bool):
        raise ValidationError(
            _('El parámetro "%(name)s" debe ser un booleano'),
            params={'name': name}
        )
    
    # Check minimum/maximum for numbers
    if param_type in ['number', 'integer']:
        if 'minimum' in schema and value < schema['minimum']:
            raise ValidationError(
                _('El parámetro "%(name)s" debe ser mayor o igual a %(min)s'),
                params={'name': name, 'min': schema['minimum']}
            )
        
        if 'maximum' in schema and value > schema['maximum']:
            raise ValidationError(
                _('El parámetro "%(name)s" debe ser menor o igual a %(max)s'),
                params={'name': name, 'max': schema['maximum']}
            )


def validate_agent_requirements(requirements):
    """
    Validate agent requirements list.
    
    Args:
        requirements: List of package requirements
        
    Raises:
        ValidationError: If requirements are invalid
    """
    if not isinstance(requirements, list):
        raise ValidationError(_('Las dependencias deben ser una lista.'))
    
    # Check for dangerous packages
    dangerous_packages = [
        'os',
        'subprocess',
        'sys',
        'importlib',
        '__builtin__',
        'builtins',
    ]
    
    for req in requirements:
        if not isinstance(req, str):
            raise ValidationError(_('Cada dependencia debe ser una cadena de texto.'))
        
        package_name = req.split('==')[0].split('>=')[0].split('<=')[0].strip()
        
        if package_name.lower() in dangerous_packages:
            raise ValidationError(
                _('Paquete peligroso no permitido: %(package)s'),
                params={'package': package_name}
            )
