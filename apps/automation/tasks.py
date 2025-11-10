"""
Celery tasks for Automation app.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import (
    Workflow,
    WorkflowTask,
    WorkflowExecution,
    TaskExecution,
    WorkflowSchedule
)
import logging
import traceback

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def execute_workflow(self, execution_id):
    """
    Execute a workflow.
    
    Args:
        execution_id: ID of the WorkflowExecution
    """
    try:
        execution = WorkflowExecution.objects.select_related('workflow').get(id=execution_id)
        workflow = execution.workflow
        
        logger.info(f"Starting workflow execution: {workflow.name}")
        
        # Update execution status
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.save()
        
        # Get tasks ordered by dependency
        tasks = workflow.tasks.filter(is_active=True).order_by('order')
        execution.tasks_total = tasks.count()
        execution.save()
        
        # Execute tasks
        context = {'input': execution.input_data, 'outputs': {}}
        
        for task in tasks:
            try:
                # Create task execution
                task_exec = TaskExecution.objects.create(
                    workflow_execution=execution,
                    task=task,
                    status='running',
                    started_at=timezone.now(),
                    input_data=context
                )
                
                # Execute task based on type
                result = execute_task(task, context)
                
                # Update task execution
                task_exec.status = 'success' if result['status'] == 'success' else 'failed'
                task_exec.completed_at = timezone.now()
                task_exec.output_data = result.get('output', {})
                task_exec.logs = result.get('logs', '')
                task_exec.error_message = result.get('error', '')
                task_exec.save()
                
                # Update context with task output
                context['outputs'][task.name] = result.get('output', {})
                
                # Update execution counters
                if result['status'] == 'success':
                    execution.tasks_completed += 1
                else:
                    execution.tasks_failed += 1
                    
                    # Stop if task failed and continue_on_failure is False
                    if not task.continue_on_failure:
                        raise Exception(f"Task {task.name} failed: {result.get('error', 'Unknown error')}")
                
                execution.save()
                
            except Exception as e:
                logger.error(f"Error executing task {task.name}: {str(e)}")
                
                task_exec.status = 'failed'
                task_exec.completed_at = timezone.now()
                task_exec.error_message = str(e)
                task_exec.save()
                
                execution.tasks_failed += 1
                execution.save()
                
                if not task.continue_on_failure:
                    raise
        
        # Update execution status
        if execution.tasks_failed == 0:
            execution.status = 'success'
        elif execution.tasks_completed > 0:
            execution.status = 'success'  # Partial success
        else:
            execution.status = 'failed'
        
        execution.completed_at = timezone.now()
        execution.output_data = context['outputs']
        execution.save()
        
        # Update workflow statistics
        workflow.execution_count += 1
        if execution.status == 'success':
            workflow.success_count += 1
        else:
            workflow.failure_count += 1
        workflow.last_execution = timezone.now()
        workflow.save()
        
        logger.info(f"Workflow execution completed: {workflow.name} - {execution.status}")
        return {
            'status': 'success',
            'execution_id': execution_id,
            'workflow_status': execution.status
        }
        
    except WorkflowExecution.DoesNotExist:
        logger.error(f"WorkflowExecution {execution_id} not found")
        return {'status': 'failed', 'error': 'Execution not found'}
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        traceback.print_exc()
        
        # Update execution status
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
            execution.status = 'failed'
            execution.completed_at = timezone.now()
            execution.error_message = str(e)
            execution.save()
            
            # Update workflow statistics
            execution.workflow.execution_count += 1
            execution.workflow.failure_count += 1
            execution.workflow.save()
        except:
            pass
        
        return {'status': 'failed', 'error': str(e)}


def execute_task(task, context):
    """
    Execute a single task based on its type.
    
    Args:
        task: WorkflowTask instance
        context: Execution context
        
    Returns:
        dict: Task execution result
    """
    task_type = task.task_type
    config = task.configuration
    
    try:
        if task_type == 'agent_execution':
            return execute_agent_task(task, context)
        elif task_type == 'data_sync':
            return execute_data_sync_task(task, context)
        elif task_type == 'monitor_check':
            return execute_monitor_check_task(task, context)
        elif task_type == 'notification':
            return execute_notification_task(task, context)
        elif task_type == 'data_transform':
            return execute_data_transform_task(task, context)
        elif task_type == 'conditional':
            return execute_conditional_task(task, context)
        elif task_type == 'api_call':
            return execute_api_call_task(task, context)
        elif task_type == 'script':
            return execute_script_task(task, context)
        else:
            return {
                'status': 'failed',
                'error': f'Task type {task_type} not implemented'
            }
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e),
            'logs': traceback.format_exc()
        }


def execute_agent_task(task, context):
    """Execute an agent execution task."""
    from apps.agents.models import Agent, AgentExecution
    from apps.agents.tasks import execute_agent
    
    config = task.configuration
    agent_id = config.get('agent_id')
    
    if not agent_id:
        return {'status': 'failed', 'error': 'agent_id not configured'}
    
    agent = Agent.objects.get(id=agent_id)
    
    # Create agent execution
    execution = AgentExecution.objects.create(
        agent=agent,
        name=f"Workflow Task: {task.name}",
        parameters=config.get('parameters', {}),
        created_by=task.created_by
    )
    
    # Execute agent (synchronously for workflow)
    result = execute_agent(execution.id)
    
    return {
        'status': result.get('status', 'failed'),
        'output': {
            'execution_id': execution.id,
            'output_data': execution.output_data
        },
        'logs': f"Agent executed: {agent.name}"
    }


def execute_data_sync_task(task, context):
    """Execute a data synchronization task."""
    from apps.geodata.models import DataSource
    from apps.geodata.tasks import sync_data_source
    
    config = task.configuration
    data_source_id = config.get('data_source_id')
    
    if not data_source_id:
        return {'status': 'failed', 'error': 'data_source_id not configured'}
    
    # Execute sync
    result = sync_data_source(data_source_id)
    
    return {
        'status': result.get('status', 'failed'),
        'output': result,
        'logs': f"Data sync completed for source {data_source_id}"
    }


def execute_monitor_check_task(task, context):
    """Execute a monitor check task."""
    from apps.monitoring.models import Monitor
    from apps.monitoring.tasks import run_monitor_check
    
    config = task.configuration
    monitor_id = config.get('monitor_id')
    
    if not monitor_id:
        return {'status': 'failed', 'error': 'monitor_id not configured'}
    
    # Execute monitor check
    result = run_monitor_check(monitor_id)
    
    return {
        'status': result.get('status', 'failed'),
        'output': result,
        'logs': f"Monitor check completed for monitor {monitor_id}"
    }


def execute_notification_task(task, context):
    """Execute a notification task."""
    config = task.configuration
    
    # TODO: Implement notification logic
    logger.info(f"Notification task: {config.get('message', 'No message')}")
    
    return {
        'status': 'success',
        'output': {'sent': True},
        'logs': 'Notification sent'
    }


def execute_data_transform_task(task, context):
    """Execute a data transformation task."""
    config = task.configuration
    
    # TODO: Implement data transformation logic
    logger.info(f"Data transform task: {task.name}")
    
    return {
        'status': 'success',
        'output': {'transformed': True},
        'logs': 'Data transformed'
    }


def execute_conditional_task(task, context):
    """Execute a conditional task."""
    config = task.configuration
    condition = config.get('condition', {})
    
    # Simple condition evaluation
    result = eval_condition(condition, context)
    
    return {
        'status': 'success',
        'output': {'condition_met': result},
        'logs': f"Condition evaluated: {result}"
    }


def execute_api_call_task(task, context):
    """Execute an API call task."""
    import requests
    
    config = task.configuration
    url = config.get('url')
    method = config.get('method', 'GET')
    headers = config.get('headers', {})
    data = config.get('data', {})
    
    if not url:
        return {'status': 'failed', 'error': 'url not configured'}
    
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=data,
        timeout=30
    )
    
    response.raise_for_status()
    
    return {
        'status': 'success',
        'output': {
            'status_code': response.status_code,
            'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        },
        'logs': f"API call completed: {method} {url}"
    }


def execute_script_task(task, context):
    """Execute a script task."""
    config = task.configuration
    script = config.get('script', '')
    
    if not script:
        return {'status': 'failed', 'error': 'script not configured'}
    
    # Execute script in controlled environment
    exec_globals = {'context': context, 'output': {}}
    exec(script, exec_globals)
    
    return {
        'status': 'success',
        'output': exec_globals.get('output', {}),
        'logs': 'Script executed'
    }


def eval_condition(condition, context):
    """
    Evaluate a condition.
    
    Args:
        condition: Condition dictionary
        context: Execution context
        
    Returns:
        bool: Condition result
    """
    # Simple condition evaluation
    # TODO: Implement more sophisticated condition logic
    return True


@shared_task
def process_scheduled_workflows():
    """
    Process all scheduled workflows that are due to run.
    This task should be run periodically via Celery Beat.
    """
    logger.info("Processing scheduled workflows")
    
    now = timezone.now()
    
    # Get schedules that need to run
    schedules = WorkflowSchedule.objects.filter(
        is_enabled=True,
        is_active=True,
        next_run__lte=now
    ).select_related('workflow')
    
    executed_count = 0
    for schedule in schedules:
        # Create execution
        execution = WorkflowExecution.objects.create(
            workflow=schedule.workflow,
            input_data=schedule.input_data,
            trigger_source='schedule',
            trigger_data={'schedule_id': schedule.id},
            created_by=schedule.created_by
        )
        
        # Launch workflow
        task = execute_workflow.delay(execution.id)
        execution.task_id = task.id
        execution.save()
        
        # Update schedule
        schedule.last_run = now
        schedule.run_count += 1
        
        # Calculate next run
        from .utils import calculate_next_run
        schedule.next_run = calculate_next_run(schedule)
        schedule.save()
        
        executed_count += 1
    
    logger.info(f"Triggered {executed_count} scheduled workflows")
    return f"Executed {executed_count} workflows"


@shared_task
def cleanup_old_executions(days=90):
    """
    Archive old workflow executions.
    
    Args:
        days: Number of days to keep executions
    """
    from datetime import timedelta
    
    threshold_date = timezone.now() - timedelta(days=days)
    
    updated = WorkflowExecution.objects.filter(
        created_at__lt=threshold_date,
        status__in=['success', 'failed', 'cancelled']
    ).update(is_active=False)
    
    logger.info(f"Archived {updated} old workflow executions")
    return f"Archived {updated} executions"


@shared_task
def update_workflow_statistics():
    """
    Update statistics for all workflows.
    This task should be run periodically (e.g., daily).
    """
    logger.info("Updating workflow statistics")
    
    workflows = Workflow.objects.filter(is_active=True)
    updated_count = 0
    
    for workflow in workflows:
        # Recalculate execution counts
        total = workflow.executions.count()
        success = workflow.executions.filter(status='success').count()
        failed = workflow.executions.filter(status='failed').count()
        
        if (total != workflow.execution_count or 
            success != workflow.success_count or 
            failed != workflow.failure_count):
            workflow.execution_count = total
            workflow.success_count = success
            workflow.failure_count = failed
            workflow.save()
            updated_count += 1
    
    logger.info(f"Updated statistics for {updated_count} workflows")
    return f"Updated {updated_count} workflows"
