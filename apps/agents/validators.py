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
    # NOTA: Usamos patrones más específicos para evitar falsos positivos
    dangerous_patterns = [
        (r'\bos\.system\s*\(', 'os.system()'),
        (r'\bos\.popen\s*\(', 'os.popen()'),
        (r'\bsubprocess\.', 'subprocess'),
        (r'(?<![_a-zA-Z])eval\s*\(', 'eval()'),
        (r'(?<![_a-zA-Z])exec\s*\(', 'exec()'),
        (r'\b__import__\s*\(', '__import__()'),
        (r'(?<![_a-zA-Z])open\s*\([^)]*["\'][wax]', 'open() en modo escritura'),
        (r'\bcompile\s*\(', 'compile()'),
        (r'\bglobals\s*\(\s*\)', 'globals()'),
        (r'\blocals\s*\(\s*\)', 'locals()'),
        (r'\bsetattr\s*\(', 'setattr()'),
        (r'\bdelattr\s*\(', 'delattr()'),
        (r'\b__builtins__', '__builtins__'),
        (r'\bbreakpoint\s*\(', 'breakpoint()'),
        # input() solo si es la función, no variables como input_layers
        (r'(?<![_a-zA-Z])input\s*\(\s*\)', 'input()'),
        (r'(?<![_a-zA-Z])input\s*\(\s*["\']', 'input() con prompt'),
    ]
    
    for pattern, name in dangerous_patterns:
        if re.search(pattern, code):
            raise ValidationError(
                _('El código contiene patrones no permitidos: %(pattern)s'),
                params={'pattern': name}
            )
    
    # Lista de imports peligrosos
    dangerous_imports = [
        'subprocess',
        'shutil',
        'socket',
        'requests',  # Podría permitirse en el futuro
        'urllib',
        'ftplib',
        'telnetlib',
        'smtplib',
        'pickle',
        'marshal',
        'shelve',
        'ctypes',
        'multiprocessing',
        'threading',
    ]
    
    # Verificar imports
    import_pattern = r'(?:from|import)\s+(\w+)'
    for match in re.finditer(import_pattern, code):
        module = match.group(1)
        if module in dangerous_imports:
            raise ValidationError(
                _('Import no permitido: %(module)s'),
                params={'module': module}
            )
    
    # Try to compile the code to check syntax
    try:
        compile(code, '<agent_code>', 'exec')
    except SyntaxError as e:
        raise ValidationError(
            _('Error de sintaxis en línea %(line)s: %(error)s'),
            params={'line': e.lineno, 'error': e.msg}
        )
    except Exception as e:
        raise ValidationError(
            _('Error al validar el código: %(error)s'),
            params={'error': str(e)}
        )


def validate_cron_expression(expression):
    """
    Validate cron expression format.
    """
    if not expression or not expression.strip():
        return  # Campo opcional
    
    try:
        from croniter import croniter
        croniter(expression)
    except ImportError:
        # Si croniter no está instalado, validación básica
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValidationError(
                _('La expresión cron debe tener 5 campos (minuto hora día mes día_semana)')
            )
    except Exception as e:
        raise ValidationError(
            _('Expresión cron inválida: %(error)s'),
            params={'error': str(e)}
        )


def validate_json_schema(schema):
    """
    Validate JSON Schema format.
    """
    if not schema:
        return  # Permitir esquema vacío
    
    if not isinstance(schema, dict):
        raise ValidationError(_('El esquema debe ser un objeto JSON válido.'))


def validate_parameters(parameters, schema):
    """
    Validate parameters against JSON Schema.
    """
    if not schema or not parameters:
        return
    
    if not isinstance(parameters, dict):
        raise ValidationError(_('Los parámetros deben ser un objeto JSON.'))
    
    # Validar campos requeridos
    required = schema.get('required', [])
    properties = schema.get('properties', {})
    
    for field in required:
        if field not in parameters:
            raise ValidationError(
                _('Falta el parámetro requerido: %(field)s'),
                params={'field': field}
            )
    
    # Validar tipos
    for field, value in parameters.items():
        if field in properties:
            field_schema = properties[field]
            _validate_field_type(field, value, field_schema)


def _validate_field_type(name, value, schema):
    """Validate a single field against its schema."""
    param_type = schema.get('type')
    
    if param_type == 'string' and not isinstance(value, str):
        raise ValidationError(
            _('El parámetro "%(name)s" debe ser texto'),
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
            _('El parámetro "%(name)s" debe ser verdadero o falso'),
            params={'name': name}
        )
    
    if param_type == 'array' and not isinstance(value, list):
        raise ValidationError(
            _('El parámetro "%(name)s" debe ser una lista'),
            params={'name': name}
        )


def validate_agent_requirements(requirements):
    """
    Validate agent requirements list.
    """
    if not requirements:
        return  # Permitir lista vacía
    
    if not isinstance(requirements, list):
        raise ValidationError(_('Las dependencias deben ser una lista.'))
    
    # Paquetes peligrosos
    dangerous_packages = [
        'os', 'sys', 'subprocess', 'shutil', 'socket',
        'pickle', 'marshal', 'ctypes', 'multiprocessing'
    ]
    
    for req in requirements:
        if not isinstance(req, str):
            raise ValidationError(_('Cada dependencia debe ser texto.'))
        
        # Extraer nombre del paquete
        package_name = req.split('==')[0].split('>=')[0].split('<=')[0].split('[')[0].strip().lower()
        
        if package_name in dangerous_packages:
            raise ValidationError(
                _('Paquete no permitido: %(package)s'),
                params={'package': package_name}
            )
