"""
Utility functions for Automation app.
"""
from django.utils import timezone
from datetime import timedelta, datetime
from croniter import croniter


def calculate_next_run(schedule):
    """
    Calculate next run time for a schedule.
    
    Args:
        schedule: WorkflowSchedule instance
        
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


def validate_workflow_definition(workflow_definition):
    """
    Validate workflow definition structure.
    
    Args:
        workflow_definition: Workflow definition dictionary
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(workflow_definition, dict):
        return False, "Workflow definition must be a dictionary"
    
    # Check for required fields
    required_fields = ['tasks']
    for field in required_fields:
        if field not in workflow_definition:
            return False, f"Missing required field: {field}"
    
    # Validate tasks
    tasks = workflow_definition.get('tasks', [])
    if not isinstance(tasks, list):
        return False, "Tasks must be a list"
    
    if len(tasks) == 0:
        return False, "Workflow must have at least one task"
    
    return True, None


def validate_task_configuration(task_type, configuration):
    """
    Validate task configuration based on task type.
    
    Args:
        task_type: Type of task
        configuration: Configuration dictionary
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(configuration, dict):
        return False, "Configuration must be a dictionary"
    
    required_fields = {
        'agent_execution': ['agent_id'],
        'data_sync': ['data_source_id'],
        'monitor_check': ['monitor_id'],
        'notification': ['message', 'recipients'],
        'api_call': ['url', 'method'],
        'script': ['script'],
        'data_transform': ['transform_type'],
    }
    
    required = required_fields.get(task_type, [])
    
    # Check required fields
    for field in required:
        if field not in configuration or not configuration[field]:
            return False, f"Campo requerido faltante: {field}"
    
    # Validate specific field types
    if task_type == 'api_call':
        valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        method = configuration.get('method', '').upper()
        if method not in valid_methods:
            return False, f"Método HTTP inválido: {method}"
        
        # Validate URL format
        url = configuration.get('url', '')
        if not url.startswith(('http://', 'https://')):
            return False, "URL debe comenzar con http:// o https://"
    
    elif task_type == 'notification':
        recipients = configuration.get('recipients', [])
        if not isinstance(recipients, list) or len(recipients) == 0:
            return False, "Recipients debe ser una lista no vacía"
    
    elif task_type == 'data_transform':
        valid_transforms = ['filter', 'aggregate', 'sort', 'select']
        transform_type = configuration.get('transform_type')
        if transform_type not in valid_transforms:
            return False, f"Tipo de transformación inválido: {transform_type}"
    
    return True, None


def build_workflow_graph(workflow):
    """
    Build a dependency graph for workflow tasks.
    
    Args:
        workflow: Workflow instance
        
    Returns:
        dict: Task dependency graph
    """
    tasks = workflow.tasks.filter(is_active=True).prefetch_related('depends_on')
    
    graph = {}
    for task in tasks:
        dependencies = [dep.id for dep in task.depends_on.all()]
        graph[task.id] = {
            'task': task,
            'depends_on': dependencies,
            'order': task.order
        }
    
    return graph


def topological_sort_tasks(workflow):
    """
    Sort workflow tasks in topological order based on dependencies.
    
    Args:
        workflow: Workflow instance
        
    Returns:
        list: Ordered list of tasks
    """
    graph = build_workflow_graph(workflow)
    
    # Simple topological sort using Kahn's algorithm
    in_degree = {task_id: 0 for task_id in graph}
    
    for task_id in graph:
        for dep_id in graph[task_id]['depends_on']:
            in_degree[task_id] += 1
    
    queue = [task_id for task_id in in_degree if in_degree[task_id] == 0]
    sorted_tasks = []
    
    while queue:
        # Sort by order field
        queue.sort(key=lambda tid: graph[tid]['order'])
        task_id = queue.pop(0)
        sorted_tasks.append(graph[task_id]['task'])
        
        # Update in-degrees
        for other_id in graph:
            if task_id in graph[other_id]['depends_on']:
                in_degree[other_id] -= 1
                if in_degree[other_id] == 0:
                    queue.append(other_id)
    
    if len(sorted_tasks) != len(graph):
        # Circular dependency detected
        return None
    
    return sorted_tasks


def check_circular_dependencies(workflow):
    """
    Check if workflow has circular dependencies.
    
    Args:
        workflow: Workflow instance
        
    Returns:
        bool: True if circular dependencies exist
    """
    sorted_tasks = topological_sort_tasks(workflow)
    return sorted_tasks is None
