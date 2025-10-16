"""
SMGI Backend - Task Manager for Monitoring
Sistema de Monitoreo Geoespacial Inteligente
Clase/servicio para gestionar dinámicamente tareas de Celery relacionadas con el monitoreo.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from celery import current_app
from celery.exceptions import NotRegistered
from django.utils import timezone

from apps.monitoring.models import MonitoringJob
from apps.monitoring.tasks import (
    monitor_layer, monitor_all_active_layers, process_monitoring_job,
    system_health_check, run_data_quality_checks, cleanup_old_snapshots
)

logger = logging.getLogger('apps.monitoring.schedulers.task_manager')

class MonitoringTaskManager:
    """
    Clase para gestionar tareas de Celery relacionadas con el monitoreo.
    Permite programar, cancelar e inspeccionar tareas dinámicamente.
    """

    @staticmethod
    def schedule_monitor_layer(layer_id: str, eta: Optional[datetime] = None, priority: int = 6) -> Optional[str]:
        """
        Programa una tarea para monitorear una capa específica en un momento dado (o inmediatamente).

        Args:
            layer_id: ID de la capa a monitorear.
            eta: Fecha y hora específica para ejecutar la tarea. Si es None, se ejecuta ASAP.
            priority: Prioridad de la tarea (0-9, 6 por defecto es alta).

        Returns:
            Task ID de la tarea programada, o None si falla.
        """
        try:
            if eta and eta < timezone.now():
                logger.warning(f"ETA {eta} is in the past for layer {layer_id}. Scheduling immediately.")
                eta = None

            # Preparar kwargs para la tarea
            task_kwargs = {'layer_id': layer_id}
            # Opciones para la tarea
            task_options = {'priority': priority}

            # Enviar la tarea
            if eta:
                result = monitor_layer.apply_async(
                    kwargs=task_kwargs,
                    eta=eta,
                    **task_options
                )
            else:
                result = monitor_layer.apply_async(
                    kwargs=task_kwargs,
                    **task_options
                )

            logger.info(f"Scheduled monitor_layer task {result.id} for layer {layer_id} (ETA: {eta})")
            return result.id

        except NotRegistered:
            logger.error(f"Task 'monitor_layer' is not registered with Celery.")
            return None
        except Exception as e:
            logger.error(f"Error scheduling monitor_layer task for layer {layer_id}: {e}")
            return None

    @staticmethod
    def schedule_monitoring_job(job_id: str, eta: Optional[datetime] = None, priority: int = 6) -> Optional[str]:
        """
        Programa una tarea para ejecutar un MonitoringJob específico en un momento dado (o inmediatamente).

        Args:
            job_id: ID del job a ejecutar.
            eta: Fecha y hora específica para ejecutar la tarea. Si es None, se ejecuta ASAP.
            priority: Prioridad de la tarea (0-9).

        Returns:
            Task ID de la tarea programada, o None si falla.
        """
        try:
            if eta and eta < timezone.now():
                logger.warning(f"ETA {eta} is in the past for job {job_id}. Scheduling immediately.")
                eta = None

            task_kwargs = {'job_id': job_id}
            task_options = {'priority': priority}

            if eta:
                result = process_monitoring_job.apply_async(
                    kwargs=task_kwargs,
                    eta=eta,
                    **task_options
                )
            else:
                result = process_monitoring_job.apply_async(
                    kwargs=task_kwargs,
                    **task_options
                )

            logger.info(f"Scheduled process_monitoring_job task {result.id} for job {job_id} (ETA: {eta})")
            return result.id

        except NotRegistered:
            logger.error(f"Task 'process_monitoring_job' is not registered with Celery.")
            return None
        except Exception as e:
            logger.error(f"Error scheduling process_monitoring_job task for job {job_id}: {e}")
            return None

    @staticmethod
    def schedule_system_health_check(eta: Optional[datetime] = None, priority: int = 5) -> Optional[str]:
        """
        Programa una tarea para verificar la salud del sistema en un momento dado (o inmediatamente).

        Args:
            eta: Fecha y hora específica para ejecutar la tarea. Si es None, se ejecuta ASAP.
            priority: Prioridad de la tarea (0-9).

        Returns:
            Task ID de la tarea programada, o None si falla.
        """
        try:
            if eta and eta < timezone.now():
                logger.warning(f"ETA {eta} is in the past for health check. Scheduling immediately.")
                eta = None

            task_options = {'priority': priority}

            if eta:
                result = system_health_check.apply_async(eta=eta, **task_options)
            else:
                result = system_health_check.apply_async(**task_options)

            logger.info(f"Scheduled system_health_check task {result.id} (ETA: {eta})")
            return result.id

        except NotRegistered:
            logger.error(f"Task 'system_health_check' is not registered with Celery.")
            return None
        except Exception as e:
            logger.error(f"Error scheduling system_health_check task: {e}")
            return None

    @staticmethod
    def schedule_data_quality_check(eta: Optional[datetime] = None, priority: int = 4) -> Optional[str]:
        """
        Programa una tarea para ejecutar verificaciones de calidad de datos en un momento dado (o inmediatamente).

        Args:
            eta: Fecha y hora específica para ejecutar la tarea. Si es None, se ejecuta ASAP.
            priority: Prioridad de la tarea (0-9).

        Returns:
            Task ID de la tarea programada, o None si falla.
        """
        try:
            if eta and eta < timezone.now():
                logger.warning(f"ETA {eta} is in the past for data quality check. Scheduling immediately.")
                eta = None

            task_options = {'priority': priority}

            if eta:
                result = run_data_quality_checks.apply_async(eta=eta, **task_options)
            else:
                result = run_data_quality_checks.apply_async(**task_options)

            logger.info(f"Scheduled run_data_quality_checks task {result.id} (ETA: {eta})")
            return result.id

        except NotRegistered:
            logger.error(f"Task 'run_data_quality_checks' is not registered with Celery.")
            return None
        except Exception as e:
            logger.error(f"Error scheduling run_data_quality_checks task: {e}")
            return None

    @staticmethod
    def schedule_cleanup_old_snapshots(eta: Optional[datetime] = None, days_to_keep: int = 30, priority: int = 3) -> Optional[str]:
        """
        Programa una tarea para limpiar snapshots antiguos en un momento dado (o inmediatamente).

        Args:
            eta: Fecha y hora específica para ejecutar la tarea. Si es None, se ejecuta ASAP.
            days_to_keep: Número de días de snapshots a mantener.
            priority: Prioridad de la tarea (0-9).

        Returns:
            Task ID de la tarea programada, o None si falla.
        """
        try:
            if eta and eta < timezone.now():
                logger.warning(f"ETA {eta} is in the past for cleanup. Scheduling immediately.")
                eta = None

            task_kwargs = {'days_to_keep': days_to_keep}
            task_options = {'priority': priority}

            if eta:
                result = cleanup_old_snapshots.apply_async(
                    kwargs=task_kwargs,
                    eta=eta,
                    **task_options
                )
            else:
                result = cleanup_old_snapshots.apply_async(
                    kwargs=task_kwargs,
                    **task_options
                )

            logger.info(f"Scheduled cleanup_old_snapshots task {result.id} (ETA: {eta}, days_to_keep: {days_to_keep})")
            return result.id

        except NotRegistered:
            logger.error(f"Task 'cleanup_old_snapshots' is not registered with Celery.")
            return None
        except Exception as e:
            logger.error(f"Error scheduling cleanup_old_snapshots task: {e}")
            return None

    @staticmethod
    def cancel_task(task_id: str) -> bool:
        """
        Cancela una tarea Celery activa o programada.

        Args:
            task_id: ID de la tarea a cancelar.

        Returns:
            True si se canceló (o ya había terminado), False si no se encontró o hubo error.
        """
        try:
            current_app.control.revoke(task_id, terminate=True, signal='SIGKILL')
            logger.info(f"Task {task_id} revoked (terminated).")
            return True
        except Exception as e:
            logger.error(f"Error revoking task {task_id}: {e}")
            return False

    @staticmethod
    def inspect_scheduled_tasks() -> Dict[str, Any]:
        """
        Obtiene una vista general de las tareas programadas en Celery Beat.

        Returns:
            Diccionario con información sobre tareas programadas.
        """
        try:
            inspect = current_app.control.inspect()
            scheduled = inspect.scheduled() # Tareas en la cola 'scheduled' (para Beat)
            if scheduled is None:
                logger.warning("Could not inspect scheduled tasks. Is Celery Beat running?")
                return {}
            return scheduled
        except Exception as e:
            logger.error(f"Error inspecting scheduled tasks: {e}")
            return {}

    @staticmethod
    def inspect_active_tasks() -> Dict[str, Any]:
        """
        Obtiene una vista general de las tareas activas (siendo ejecutadas) en Celery Workers.

        Returns:
            Diccionario con información sobre tareas activas.
        """
        try:
            inspect = current_app.control.inspect()
            active = inspect.active()
            if active is None:
                logger.warning("Could not inspect active tasks. Are Celery Workers running?")
                return {}
            return active
        except Exception as e:
            logger.error(f"Error inspecting active tasks: {e}")
            return {}

    @staticmethod
    def get_task_status(task_id: str) -> Optional[str]:
        """
        Obtiene el estado de una tarea específica.

        Args:
            task_id: ID de la tarea.

        Returns:
            Estado de la tarea (e.g., 'PENDING', 'STARTED', 'SUCCESS', 'FAILURE', 'REVOKED'), o None si no se encuentra.
        """
        try:
            from celery.result import AsyncResult
            result = AsyncResult(task_id, app=current_app)
            return result.state
        except Exception as e:
            logger.error(f"Error getting status for task {task_id}: {e}")
            return None

    @staticmethod
    def schedule_job_based_on_model(monitoring_job: MonitoringJob) -> Optional[str]:
        """
        Programa una ejecución de un MonitoringJob basado en su configuración de modelo.
        Esta función toma la expresión de cron o intervalo del modelo y la convierte en una ETA
        para programar la tarea vía el TaskManager.

        Args:
            monitoring_job: Instancia del modelo MonitoringJob.

        Returns:
            Task ID de la tarea programada, o None si falla.
        """
        # NOTA: Esto duplica parte de la lógica de MonitoringJob.calculate_next_run,
        # pero la convierte en una ETA para apply_async.
        # Para integración real con Beat, se usaría PERIODIC_TASKS.
        try:
            next_run = monitoring_job.calculate_next_run()
            if not next_run:
                logger.error(f"Could not calculate next run for job {monitoring_job.id}")
                return None

            # Aquí podríamos decidir la prioridad basada en la configuración del job
            priority = 6 # Valor por defecto, podría ser dinámico

            return MonitoringTaskManager.schedule_monitoring_job(
                job_id=str(monitoring_job.id),
                eta=next_run,
                priority=priority
            )

        except Exception as e:
            logger.error(f"Error scheduling job {monitoring_job.id} from model: {e}")
            return None

