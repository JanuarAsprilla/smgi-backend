"""
Celery tasks for Agents app.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import Agent, AgentExecution, AgentSchedule
import logging
import sys
import traceback
from io import StringIO
import json

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def execute_agent(self, execution_id):
    """
    Execute an agent.
    
    Args:
        execution_id: ID of the AgentExecution
    """
    try:
        execution = AgentExecution.objects.select_related('agent').get(id=execution_id)
        agent = execution.agent
        
        logger.info(f"Starting execution {execution_id} for agent {agent.name}")
        
        # Update execution status
        execution.status = AgentExecution.Status.RUNNING
        execution.started_at = timezone.now()
        execution.save()
        
        # Prepare execution environment
        execution_globals = {
            'execution_id': execution_id,
            'parameters': execution.parameters,
            'input_layers': list(execution.input_layers.all()),
            'input_datasets': list(execution.input_datasets.all()),
            'output_data': {},
            'output_layers': [],
        }
        
        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = StringIO()
        redirected_error = StringIO()
        sys.stdout = redirected_output
        sys.stderr = redirected_error
        
        try:
            # Execute agent code
            exec(agent.code, execution_globals)
            
            # Get results
            output_data = execution_globals.get('output_data', {})
            output_layers = execution_globals.get('output_layers', [])
            
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            # Get logs
            logs = redirected_output.getvalue()
            errors = redirected_error.getvalue()
            
            if errors:
                logs += "\n\nErrors:\n" + errors
            
            # Update execution with results
            execution.status = AgentExecution.Status.SUCCESS
            execution.completed_at = timezone.now()
            execution.output_data = output_data
            execution.output_layers = output_layers
            execution.logs = logs
            execution.processing_time = (execution.completed_at - execution.started_at).total_seconds()
            execution.save()
            
            # Update agent statistics
            agent.execution_count += 1
            agent.success_count += 1
            agent.save()
            
            logger.info(f"Execution {execution_id} completed successfully")
            return {
                'status': 'success',
                'execution_id': execution_id,
                'output_data': output_data
            }
            
        except Exception as e:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            # Get logs and error
            logs = redirected_output.getvalue()
            error_traceback = traceback.format_exc()
            
            # Update execution with error
            execution.status = AgentExecution.Status.FAILED
            execution.completed_at = timezone.now()
            execution.logs = logs
            execution.error_message = f"{str(e)}\n\n{error_traceback}"
            execution.processing_time = (execution.completed_at - execution.started_at).total_seconds()
            execution.save()
            
            # Update agent statistics
            agent.execution_count += 1
            agent.failure_count += 1
            agent.save()
            
            logger.error(f"Execution {execution_id} failed: {str(e)}")
            return {
                'status': 'failed',
                'execution_id': execution_id,
                'error': str(e)
            }
            
    except AgentExecution.DoesNotExist:
        logger.error(f"AgentExecution {execution_id} not found")
        return {'status': 'failed', 'error': 'Execution not found'}
    except Exception as e:
        logger.error(f"Unexpected error executing agent: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def schedule_agent_execution(schedule_id):
    """
    Execute a scheduled agent.
    
    Args:
        schedule_id: ID of the AgentSchedule
    """
    try:
        schedule = AgentSchedule.objects.select_related('agent').get(id=schedule_id)
        
        if not schedule.is_enabled or not schedule.is_active:
            logger.info(f"Schedule {schedule_id} is disabled, skipping execution")
            return {'status': 'skipped', 'reason': 'Schedule is disabled'}
        
        logger.info(f"Executing scheduled agent: {schedule.agent.name}")
        
        # Create execution
        execution = AgentExecution.objects.create(
            agent=schedule.agent,
            name=f"{schedule.name} (Programado)",
            parameters=schedule.parameters,
            created_by=schedule.created_by
        )
        
        # Set input layers and datasets
        execution.input_layers.set(schedule.input_layers.all())
        execution.input_datasets.set(schedule.input_datasets.all())
        
        # Launch execution
        task = execute_agent.delay(execution.id)
        execution.task_id = task.id
        execution.save()
        
        # Update schedule
        schedule.last_run = timezone.now()
        schedule.run_count += 1
        
        # Calculate next run
        from .utils import calculate_next_run
        schedule.next_run = calculate_next_run(schedule)
        schedule.save()
        
        logger.info(f"Scheduled execution {execution.id} started")
        return {
            'status': 'success',
            'execution_id': execution.id,
            'task_id': task.id
        }
        
    except AgentSchedule.DoesNotExist:
        logger.error(f"AgentSchedule {schedule_id} not found")
        return {'status': 'failed', 'error': 'Schedule not found'}
    except Exception as e:
        logger.error(f"Error executing scheduled agent: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def process_scheduled_agents():
    """
    Process all scheduled agents that are due to run.
    This task should be run periodically via Celery Beat (e.g., every minute).
    """
    logger.info("Processing scheduled agents")
    
    now = timezone.now()
    
    # Get schedules that need to run
    schedules = AgentSchedule.objects.filter(
        is_enabled=True,
        is_active=True,
        next_run__lte=now
    )
    
    executed_count = 0
    for schedule in schedules:
        schedule_agent_execution.delay(schedule.id)
        executed_count += 1
    
    logger.info(f"Triggered {executed_count} scheduled agent executions")
    return f"Triggered {executed_count} executions"


@shared_task
def cleanup_old_executions(days=30):
    """
    Delete old agent executions.
    
    Args:
        days: Number of days to keep executions
    """
    from datetime import timedelta
    
    threshold_date = timezone.now() - timedelta(days=days)
    deleted = AgentExecution.objects.filter(
        created_at__lt=threshold_date,
        status__in=['success', 'failed', 'cancelled']
    ).delete()
    
    logger.info(f"Deleted {deleted[0]} old agent executions")
    return f"Deleted {deleted[0]} executions"


@shared_task
def update_agent_statistics():
    """
    Update statistics for all agents.
    This task should be run periodically (e.g., daily).
    """
    logger.info("Updating agent statistics")
    
    agents = Agent.objects.all()
    updated_count = 0
    
    for agent in agents:
        # Recalculate execution counts
        total = agent.executions.count()
        success = agent.executions.filter(status='success').count()
        failed = agent.executions.filter(status='failed').count()
        
        if total != agent.execution_count or success != agent.success_count or failed != agent.failure_count:
            agent.execution_count = total
            agent.success_count = success
            agent.failure_count = failed
            agent.save()
            updated_count += 1
    
    logger.info(f"Updated statistics for {updated_count} agents")
    return f"Updated {updated_count} agents"


@shared_task
def calculate_agent_ratings():
    """
    Recalculate average ratings for all agents.
    This task should be run periodically (e.g., hourly).
    """
    from django.db.models import Avg
    
    logger.info("Recalculating agent ratings")
    
    agents = Agent.objects.filter(is_active=True)
    updated_count = 0
    
    for agent in agents:
        avg_rating = agent.ratings.aggregate(Avg('rating'))['rating__avg']
        new_rating = round(avg_rating, 2) if avg_rating else 0.0
        
        if agent.rating != new_rating:
            agent.rating = new_rating
            agent.save()
            updated_count += 1
    
    logger.info(f"Updated ratings for {updated_count} agents")
    return f"Updated {updated_count} ratings"


@shared_task
def notify_execution_completion(execution_id):
    """
    Send notification when an execution completes.
    
    Args:
        execution_id: ID of the AgentExecution
    """
    try:
        execution = AgentExecution.objects.select_related('agent', 'created_by').get(id=execution_id)
        
        if not execution.created_by or not execution.created_by.email:
            return {'status': 'skipped', 'reason': 'No user email'}
        
        # Send email and in-app notification
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            subject = f"Ejecución de Agente {'Completada' if execution.status == 'success' else 'Fallida'}"
            
            if execution.status == 'success':
                message = f"""Hola {execution.created_by.get_full_name() or execution.created_by.username},

Tu ejecución del agente '{execution.agent.name}' ha sido completada exitosamente.

Detalles:
- Nombre: {execution.name}
- Tiempo de procesamiento: {execution.processing_time:.2f} segundos
- Fecha: {execution.completed_at.strftime('%Y-%m-%d %H:%M:%S')}

Puedes ver los resultados en: {settings.FRONTEND_URL}/agents/executions/{execution.id}

Saludos,
Equipo SMGI
"""
            else:
                message = f"""Hola {execution.created_by.get_full_name() or execution.created_by.username},

Tu ejecución del agente '{execution.agent.name}' ha fallado.

Detalles:
- Nombre: {execution.name}
- Error: {execution.error_message[:200]}...
- Fecha: {execution.completed_at.strftime('%Y-%m-%d %H:%M:%S')}

Puedes revisar los logs en: {settings.FRONTEND_URL}/agents/executions/{execution.id}

Saludos,
Equipo SMGI
"""
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [execution.created_by.email],
                fail_silently=True,
            )
            
            # Also send in-app notification
            try:
                from apps.notifications.services import NotificationService
                NotificationService.notify_user(
                    user_id=execution.created_by.id,
                    title=subject,
                    message=f"Ejecución del agente '{execution.agent.name}': {execution.status}",
                    notification_type=f"execution_{execution.status}",
                    related_object_id=execution.id,
                    related_object_type="agent_execution"
                )
            except ImportError:
                pass
            
            logger.info(f"Notification sent to {execution.created_by.email} for execution {execution_id}")
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
        
        return {'status': 'success', 'message': 'Notification sent'}
        
    except AgentExecution.DoesNotExist:
        logger.error(f"AgentExecution {execution_id} not found")
        return {'status': 'failed', 'error': 'Execution not found'}
