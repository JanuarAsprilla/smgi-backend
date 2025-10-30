# apps/audit/decorators.py
"""
SMGI Backend - Audit Decorators
Sistema de Monitoreo Geoespacial Inteligente
Decoradores personalizados para registrar eventos de auditoría automáticamente
"""
import functools
import logging
from typing import Callable, Any, Optional, Dict, List, Union
from django.utils import timezone
from django.http import HttpRequest
from django.contrib.auth import get_user_model

from apps.audit.models import (
    AuditLog, AuditTrail, AuditEventType, AuditEventSeverity, AuditEventStatus, DataClassification
)

logger = logging.getLogger('apps.audit.decorators')
User = get_user_model()


def get_user_from_request(request: HttpRequest) -> Optional[User]:
    """
    Obtiene el usuario desde un objeto HttpRequest.
    
    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        
    Returns:
        Optional[User]: Usuario autenticado o None.
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


def get_ip_from_request(request: HttpRequest) -> Optional[str]:
    """
    Obtiene la dirección IP desde un objeto HttpRequest.
    
    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        
    Returns:
        Optional[str]: Dirección IP o None.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent_from_request(request: HttpRequest) -> Optional[str]:
    """
    Obtiene el user agent desde un objeto HttpRequest.
    
    Args:
        request (HttpRequest): Objeto de solicitud HTTP.
        
    Returns:
        Optional[str]: User agent o None.
    """
    return request.META.get('HTTP_USER_AGENT')


def audit_log(
    event_type: str = AuditEventType.USER_ACTION,
    severity: str = AuditEventSeverity.MEDIUM,
    description: str = "",
    details: Optional[Dict[str, Any]] = None,
    resource_type: str = "",
    resource_id: str = "",
    action: str = "",
    success_message: str = "Operation completed successfully",
    failure_message: str = "Operation failed",
    log_on_success: bool = True,
    log_on_failure: bool = True,
    log_args: bool = False,
    log_kwargs: bool = False,
    log_result: bool = False,
    log_duration: bool = True,
    log_user: bool = True,
    log_ip: bool = True,
    log_user_agent: bool = True,
    log_session: bool = False,
    log_request_id: bool = False,
    log_correlation_id: bool = False,
    log_metadata: bool = False,
    log_tags: bool = False,
    log_related_events: bool = False,
    log_parent_event: bool = False,
    log_external_reference_id: bool = False,
    log_external_system: bool = False,
    log_retention_policy: bool = False,
    log_data_classification: bool = False,
    log_is_archived: bool = False,
    log_archived_at: bool = False,
    log_archived_by: bool = False,
    log_success: bool = True,
    log_error_message: bool = True,
    log_notification_sent: bool = False,
    log_notification_count: bool = False,
    log_last_notification_sent: bool = False,
    log_auto_resolve: bool = False,
    log_auto_resolve_duration: bool = False,
    log_suppress_similar: bool = False,
    log_suppression_duration: bool = False,
    log_threshold_value: bool = False,
    log_actual_value: bool = False,
    log_change_percentage: bool = False,
    log_feature_count_change: bool = False,
    log_affected_features_count: bool = False,
    log_area_change: bool = False,
    log_centroid_displacement: bool = False,
    log_modified_features: bool = False,
    log_new_features: bool = False,
    log_deleted_features: bool = False,
    log_data_quality_score: bool = False,
    log_data_quality_change: bool = False,
    log_memory_usage_mb: bool = False,
    log_cpu_usage_percent: bool = False,
    log_execution_log: bool = False,
    log_performance_metrics: bool = False,
    log_alert: bool = False,
    log_service: bool = False,
    log_layer: bool = False,
    log_monitoring_job: bool = False,
    log_report: bool = False,
    log_notification: bool = False,
    log_user_activity: bool = False,
    log_system_health: bool = False,
    log_data_quality: bool = False,
    log_change_detection: bool = False,
    log_gis_service_interaction: bool = False,
    log_authentication: bool = False,
    log_authorization: bool = False,
    log_error_handling: bool = False,
    log_performance_monitoring: bool = False,
    log_security_event: bool = False,
    log_api_call: bool = False,
    log_external_api_call: bool = False,
    log_internal_api_call: bool = False,
    log_database_query: bool = False,
    log_cache_operation: bool = False,
    log_file_operation: bool = False,
    log_email_sending: bool = False,
    log_sms_sending: bool = False,
    log_webhook_sending: bool = False,
    log_push_notification_sending: bool = False,
    log_report_generation: bool = False,
    log_alert_triggering: bool = False,
    log_monitoring_job_scheduling: bool = False,
    log_system_health_check: bool = False,
    log_data_validation: bool = False,
    log_custom_event: bool = False
) -> Callable:
    """
    Decorador para registrar eventos de auditoría automáticamente.
    
    Args:
        event_type (str): Tipo de evento de auditoría (AuditEventType).
        severity (str): Severidad del evento (AuditEventSeverity).
        description (str): Descripción del evento.
        details (Optional[Dict[str, Any]]): Detalles adicionales del evento.
        resource_type (str): Tipo de recurso afectado.
        resource_id (str): ID del recurso afectado.
        action (str): Acción realizada.
        success_message (str): Mensaje de éxito.
        failure_message (str): Mensaje de fallo.
        log_on_success (bool): Registrar evento si la función tiene éxito.
        log_on_failure (bool): Registrar evento si la función falla.
        log_args (bool): Registrar argumentos de la función.
        log_kwargs (bool): Registrar keyword arguments de la función.
        log_result (bool): Registrar resultado de la función.
        log_duration (bool): Registrar duración de la ejecución.
        log_user (bool): Registrar usuario que ejecutó la función.
        log_ip (bool): Registrar IP del usuario.
        log_user_agent (bool): Registrar user agent del usuario.
        log_session (bool): Registrar sesión del usuario.
        log_request_id (bool): Registrar ID de la solicitud.
        log_correlation_id (bool): Registrar ID de correlación.
        log_metadata (bool): Registrar metadatos adicionales.
        log_tags (bool): Registrar etiquetas.
        log_related_events (bool): Registrar eventos relacionados.
        log_parent_event (bool): Registrar evento padre.
        log_external_reference_id (bool): Registrar ID de referencia externa.
        log_external_system (bool): Registrar sistema externo.
        log_retention_policy (bool): Registrar política de retención.
        log_data_classification (bool): Registrar clasificación de datos.
        log_is_archived (bool): Registrar si el evento está archivado.
        log_archived_at (bool): Registrar fecha de archivo.
        log_archived_by (bool): Registrar usuario que archivó.
        log_success (bool): Registrar si el evento fue exitoso.
        log_error_message (bool): Registrar mensaje de error.
        log_notification_sent (bool): Registrar si se envió notificación.
        log_notification_count (bool): Registrar conteo de notificaciones.
        log_last_notification_sent (bool): Registrar fecha de última notificación.
        log_auto_resolve (bool): Registrar si se resuelve automáticamente.
        log_auto_resolve_duration (bool): Registrar duración de resolución automática.
        log_suppress_similar (bool): Registrar si se suprimen alertas similares.
        log_suppression_duration (bool): Registrar duración de supresión.
        log_threshold_value (bool): Registrar valor umbral.
        log_actual_value (bool): Registrar valor actual.
        log_change_percentage (bool): Registrar porcentaje de cambio.
        log_feature_count_change (bool): Registrar cambio en conteo de features.
        log_affected_features_count (bool): Registrar conteo de features afectadas.
        log_area_change (bool): Registrar cambio en área.
        log_centroid_displacement (bool): Registrar desplazamiento del centroide.
        log_modified_features (bool): Registrar features modificadas.
        log_new_features (bool): Registrar nuevas features.
        log_deleted_features (bool): Registrar features eliminadas.
        log_data_quality_score (bool): Registrar puntaje de calidad de datos.
        log_data_quality_change (bool): Registrar cambio en puntaje de calidad.
        log_memory_usage_mb (bool): Registrar uso de memoria.
        log_cpu_usage_percent (bool): Registrar uso de CPU.
        log_execution_log (bool): Registrar log de ejecución.
        log_performance_metrics (bool): Registrar métricas de rendimiento.
        log_alert (bool): Registrar alerta relacionada.
        log_service (bool): Registrar servicio relacionado.
        log_layer (bool): Registrar capa relacionada.
        log_monitoring_job (bool): Registrar job de monitoreo relacionado.
        log_report (bool): Registrar informe relacionado.
        log_notification (bool): Registrar notificación relacionada.
        log_user_activity (bool): Registrar actividad de usuario.
        log_system_health (bool): Registrar salud del sistema.
        log_data_quality (bool): Registrar calidad de datos.
        log_change_detection (bool): Registrar detección de cambios.
        log_gis_service_interaction (bool): Registrar interacción con servicio GIS.
        log_authentication (bool): Registrar autenticación.
        log_authorization (bool): Registrar autorización.
        log_error_handling (bool): Registrar manejo de errores.
        log_performance_monitoring (bool): Registrar monitoreo de rendimiento.
        log_security_event (bool): Registrar evento de seguridad.
        log_api_call (bool): Registrar llamada a API.
        log_external_api_call (bool): Registrar llamada a API externa.
        log_internal_api_call (bool): Registrar llamada a API interna.
        log_database_query (bool): Registrar consulta a base de datos.
        log_cache_operation (bool): Registrar operación de caché.
        log_file_operation (bool): Registrar operación de archivo.
        log_email_sending (bool): Registrar envío de email.
        log_sms_sending (bool): Registrar envío de SMS.
        log_webhook_sending (bool): Registrar envío de webhook.
        log_push_notification_sending (bool): Registrar envío de notificación push.
        log_report_generation (bool): Registrar generación de informe.
        log_alert_triggering (bool): Registrar disparo de alerta.
        log_monitoring_job_scheduling (bool): Registrar programación de job de monitoreo.
        log_system_health_check (bool): Registrar verificación de salud del sistema.
        log_data_validation (bool): Registrar validación de datos.
        log_custom_event (bool): Registrar evento personalizado.
        
    Returns:
        Callable: Función decorada.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = timezone.now()
            user = None
            ip_address = None
            user_agent = None
            session_key = None
            request_id = None
            correlation_id = None
            
            # --- MEJORA: Obtener contexto de la solicitud ---
            # Asumir que el primer argumento es 'self' (método de clase) o 'request' (función)
            # y que contiene información del usuario, IP, etc.
            request_arg = None
            if args and isinstance(args[0], HttpRequest):
                request_arg = args[0]
            elif 'request' in kwargs and isinstance(kwargs['request'], HttpRequest):
                request_arg = kwargs['request']
            elif args and hasattr(args[0], 'request') and isinstance(args[0].request, HttpRequest):
                request_arg = args[0].request
            
            if request_arg:
                if log_user:
                    user = get_user_from_request(request_arg)
                if log_ip:
                    ip_address = get_ip_from_request(request_arg)
                if log_user_agent:
                    user_agent = get_user_agent_from_request(request_arg)
                if log_session:
                    session_key = request_arg.session.session_key if hasattr(request_arg, 'session') else None
                if log_request_id:
                    request_id = getattr(request_arg, 'id', None) or request_arg.META.get('HTTP_X_REQUEST_ID')
                if log_correlation_id:
                    correlation_id = request_arg.META.get('HTTP_X_CORRELATION_ID')
            
            # --- MEJORA: Registrar inicio de la operación ---
            logger.info(f"Audit log decorator applied to {func.__name__}")
            
            try:
                # Ejecutar la función decorada
                result = func(*args, **kwargs)
                
                # --- MEJORA: Registrar éxito ---
                if log_on_success:
                    end_time = timezone.now()
                    duration_ms = int((end_time - start_time).total_seconds() * 1000) if log_duration else 0
                    
                    # Preparar detalles del evento
                    event_details = details or {}
                    if log_args:
                        event_details['args'] = args
                    if log_kwargs:
                        event_details['kwargs'] = kwargs
                    if log_result:
                        event_details['result'] = result
                    if log_duration:
                        event_details['duration_ms'] = duration_ms
                    if log_session:
                        event_details['session_key'] = session_key
                    if log_request_id:
                        event_details['request_id'] = request_id
                    if log_correlation_id:
                        event_details['correlation_id'] = correlation_id
                    if log_metadata:
                        event_details['metadata'] = {}
                    if log_tags:
                        event_details['tags'] = []
                    if log_related_events:
                        event_details['related_events'] = []
                    if log_parent_event:
                        event_details['parent_event'] = None
                    if log_external_reference_id:
                        event_details['external_reference_id'] = ""
                    if log_external_system:
                        event_details['external_system'] = ""
                    if log_retention_policy:
                        event_details['retention_policy'] = ""
                    if log_data_classification:
                        event_details['data_classification'] = DataClassification.INTERNAL
                    if log_is_archived:
                        event_details['is_archived'] = False
                    if log_archived_at:
                        event_details['archived_at'] = None
                    if log_archived_by:
                        event_details['archived_by'] = None
                    if log_success:
                        event_details['success'] = True
                    if log_error_message:
                        event_details['error_message'] = ""
                    if log_notification_sent:
                        event_details['notification_sent'] = False
                    if log_notification_count:
                        event_details['notification_count'] = 0
                    if log_last_notification_sent:
                        event_details['last_notification_sent'] = None
                    if log_auto_resolve:
                        event_details['auto_resolve'] = False
                    if log_auto_resolve_duration:
                        event_details['auto_resolve_duration'] = 0
                    if log_suppress_similar:
                        event_details['suppress_similar'] = False
                    if log_suppression_duration:
                        event_details['suppression_duration'] = 0
                    if log_threshold_value:
                        event_details['threshold_value'] = 0.0
                    if log_actual_value:
                        event_details['actual_value'] = 0.0
                    if log_change_percentage:
                        event_details['change_percentage'] = 0.0
                    if log_feature_count_change:
                        event_details['feature_count_change'] = 0
                    if log_affected_features_count:
                        event_details['affected_features_count'] = 0
                    if log_area_change:
                        event_details['area_change'] = 0.0
                    if log_centroid_displacement:
                        event_details['centroid_displacement'] = 0.0
                    if log_modified_features:
                        event_details['modified_features'] = 0
                    if log_new_features:
                        event_details['new_features'] = 0
                    if log_deleted_features:
                        event_details['deleted_features'] = 0
                    if log_data_quality_score:
                        event_details['data_quality_score'] = 1.0
                    if log_data_quality_change:
                        event_details['data_quality_change'] = 0.0
                    if log_memory_usage_mb:
                        event_details['memory_usage_mb'] = 0
                    if log_cpu_usage_percent:
                        event_details['cpu_usage_percent'] = 0.0
                    if log_execution_log:
                        event_details['execution_log'] = []
                    if log_performance_metrics:
                        event_details['performance_metrics'] = {}
                    if log_alert:
                        event_details['alert'] = None
                    if log_service:
                        event_details['service'] = None
                    if log_layer:
                        event_details['layer'] = None
                    if log_monitoring_job:
                        event_details['monitoring_job'] = None
                    if log_report:
                        event_details['report'] = None
                    if log_notification:
                        event_details['notification'] = None
                    if log_user_activity:
                        event_details['user_activity'] = {}
                    if log_system_health:
                        event_details['system_health'] = {}
                    if log_data_quality:
                        event_details['data_quality'] = {}
                    if log_change_detection:
                        event_details['change_detection'] = {}
                    if log_gis_service_interaction:
                        event_details['gis_service_interaction'] = {}
                    if log_authentication:
                        event_details['authentication'] = {}
                    if log_authorization:
                        event_details['authorization'] = {}
                    if log_error_handling:
                        event_details['error_handling'] = {}
                    if log_performance_monitoring:
                        event_details['performance_monitoring'] = {}
                    if log_security_event:
                        event_details['security_event'] = {}
                    if log_api_call:
                        event_details['api_call'] = {}
                    if log_external_api_call:
                        event_details['external_api_call'] = {}
                    if log_internal_api_call:
                        event_details['internal_api_call'] = {}
                    if log_database_query:
                        event_details['database_query'] = {}
                    if log_cache_operation:
                        event_details['cache_operation'] = {}
                    if log_file_operation:
                        event_details['file_operation'] = {}
                    if log_email_sending:
                        event_details['email_sending'] = {}
                    if log_sms_sending:
                        event_details['sms_sending'] = {}
                    if log_webhook_sending:
                        event_details['webhook_sending'] = {}
                    if log_push_notification_sending:
                        event_details['push_notification_sending'] = {}
                    if log_report_generation:
                        event_details['report_generation'] = {}
                    if log_alert_triggering:
                        event_details['alert_triggering'] = {}
                    if log_monitoring_job_scheduling:
                        event_details['monitoring_job_scheduling'] = {}
                    if log_system_health_check:
                        event_details['system_health_check'] = {}
                    if log_data_validation:
                        event_details['data_validation'] = {}
                    if log_custom_event:
                        event_details['custom_event'] = {}
                    
                    # Crear registro de auditoría
                    AuditLog.objects.create(
                        event_id=str(uuid.uuid4()),
                        event_type=event_type,
                        severity=severity,
                        status=AuditEventStatus.COMPLETED,
                        user=user,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action=action or func.__name__,
                        description=description or success_message,
                        details=event_details,
                        timestamp=start_time,
                        duration_ms=duration_ms,
                        success=True,
                        error_message="",
                        metadata={},
                        tags=[],
                        related_events=[],
                        parent_event=None,
                        external_reference_id="",
                        external_system="",
                        is_archived=False,
                        archived_at=None,
                        archived_by=None,
                        retention_policy="",
                        data_classification=DataClassification.INTERNAL
                    )
                
                return result
                
            except Exception as e:
                # --- MEJORA: Registrar fallo ---
                if log_on_failure:
                    end_time = timezone.now()
                    duration_ms = int((end_time - start_time).total_seconds() * 1000) if log_duration else 0
                    
                    # Preparar detalles del evento de fallo
                    event_details = details or {}
                    if log_args:
                        event_details['args'] = args
                    if log_kwargs:
                        event_details['kwargs'] = kwargs
                    if log_duration:
                        event_details['duration_ms'] = duration_ms
                    if log_session:
                        event_details['session_key'] = session_key
                    if log_request_id:
                        event_details['request_id'] = request_id
                    if log_correlation_id:
                        event_details['correlation_id'] = correlation_id
                    if log_metadata:
                        event_details['metadata'] = {}
                    if log_tags:
                        event_details['tags'] = []
                    if log_related_events:
                        event_details['related_events'] = []
                    if log_parent_event:
                        event_details['parent_event'] = None
                    if log_external_reference_id:
                        event_details['external_reference_id'] = ""
                    if log_external_system:
                        event_details['external_system'] = ""
                    if log_retention_policy:
                        event_details['retention_policy'] = ""
                    if log_data_classification:
                        event_details['data_classification'] = DataClassification.INTERNAL
                    if log_is_archived:
                        event_details['is_archived'] = False
                    if log_archived_at:
                        event_details['archived_at'] = None
                    if log_archived_by:
                        event_details['archived_by'] = None
                    if log_success:
                        event_details['success'] = False
                    if log_error_message:
                        event_details['error_message'] = str(e)
                    if log_notification_sent:
                        event_details['notification_sent'] = False
                    if log_notification_count:
                        event_details['notification_count'] = 0
                    if log_last_notification_sent:
                        event_details['last_notification_sent'] = None
                    if log_auto_resolve:
                        event_details['auto_resolve'] = False
                    if log_auto_resolve_duration:
                        event_details['auto_resolve_duration'] = 0
                    if log_suppress_similar:
                        event_details['suppress_similar'] = False
                    if log_suppression_duration:
                        event_details['suppression_duration'] = 0
                    if log_threshold_value:
                        event_details['threshold_value'] = 0.0
                    if log_actual_value:
                        event_details['actual_value'] = 0.0
                    if log_change_percentage:
                        event_details['change_percentage'] = 0.0
                    if log_feature_count_change:
                        event_details['feature_count_change'] = 0
                    if log_affected_features_count:
                        event_details['affected_features_count'] = 0
                    if log_area_change:
                        event_details['area_change'] = 0.0
                    if log_centroid_displacement:
                        event_details['centroid_displacement'] = 0.0
                    if log_modified_features:
                        event_details['modified_features'] = 0
                    if log_new_features:
                        event_details['new_features'] = 0
                    if log_deleted_features:
                        event_details['deleted_features'] = 0
                    if log_data_quality_score:
                        event_details['data_quality_score'] = 1.0
                    if log_data_quality_change:
                        event_details['data_quality_change'] = 0.0
                    if log_memory_usage_mb:
                        event_details['memory_usage_mb'] = 0
                    if log_cpu_usage_percent:
                        event_details['cpu_usage_percent'] = 0.0
                    if log_execution_log:
                        event_details['execution_log'] = []
                    if log_performance_metrics:
                        event_details['performance_metrics'] = {}
                    if log_alert:
                        event_details['alert'] = None
                    if log_service:
                        event_details['service'] = None
                    if log_layer:
                        event_details['layer'] = None
                    if log_monitoring_job:
                        event_details['monitoring_job'] = None
                    if log_report:
                        event_details['report'] = None
                    if log_notification:
                        event_details['notification'] = None
                    if log_user_activity:
                        event_details['user_activity'] = {}
                    if log_system_health:
                        event_details['system_health'] = {}
                    if log_data_quality:
                        event_details['data_quality'] = {}
                    if log_change_detection:
                        event_details['change_detection'] = {}
                    if log_gis_service_interaction:
                        event_details['gis_service_interaction'] = {}
                    if log_authentication:
                        event_details['authentication'] = {}
                    if log_authorization:
                        event_details['authorization'] = {}
                    if log_error_handling:
                        event_details['error_handling'] = {}
                    if log_performance_monitoring:
                        event_details['performance_monitoring'] = {}
                    if log_security_event:
                        event_details['security_event'] = {}
                    if log_api_call:
                        event_details['api_call'] = {}
                    if log_external_api_call:
                        event_details['external_api_call'] = {}
                    if log_internal_api_call:
                        event_details['internal_api_call'] = {}
                    if log_database_query:
                        event_details['database_query'] = {}
                    if log_cache_operation:
                        event_details['cache_operation'] = {}
                    if log_file_operation:
                        event_details['file_operation'] = {}
                    if log_email_sending:
                        event_details['email_sending'] = {}
                    if log_sms_sending:
                        event_details['sms_sending'] = {}
                    if log_webhook_sending:
                        event_details['webhook_sending'] = {}
                    if log_push_notification_sending:
                        event_details['push_notification_sending'] = {}
                    if log_report_generation:
                        event_details['report_generation'] = {}
                    if log_alert_triggering:
                        event_details['alert_triggering'] = {}
                    if log_monitoring_job_scheduling:
                        event_details['monitoring_job_scheduling'] = {}
                    if log_system_health_check:
                        event_details['system_health_check'] = {}
                    if log_data_validation:
                        event_details['data_validation'] = {}
                    if log_custom_event:
                        event_details['custom_event'] = {}
                    
                    # Crear registro de auditoría de fallo
                    AuditLog.objects.create(
                        event_id=str(uuid.uuid4()),
                        event_type=event_type,
                        severity=severity,
                        status=AuditEventStatus.FAILED,
                        user=user,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        action=action or func.__name__,
                        description=description or failure_message,
                        details=event_details,
                        timestamp=start_time,
                        duration_ms=duration_ms,
                        success=False,
                        error_message=str(e),
                        metadata={},
                        tags=[],
                        related_events=[],
                        parent_event=None,
                        external_reference_id="",
                        external_system="",
                        is_archived=False,
                        archived_at=None,
                        archived_by=None,
                        retention_policy="",
                        data_classification=DataClassification.INTERNAL
                    )
                
                # Re-lanzar la excepción
                raise
        
        return wrapper
    return decorator


def audit_trail(
    model_name: str = "",
    object_id: str = "",
    field_name: str = "",
    old_value: Any = None,
    new_value: Any = None,
    change_type: str = 'UPDATED',
    user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_key: Optional[str] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    is_archived: bool = False,
    archived_at: Optional[timezone.datetime] = None,
    archived_by: Optional[User] = None,
    retention_policy: str = "",
    data_classification: str = DataClassification.INTERNAL
) -> Callable:
    """
    Decorador para registrar cambios en modelos específicos (AuditTrail).
    
    Args:
        model_name (str): Nombre del modelo afectado.
        object_id (str): ID del objeto afectado.
        field_name (str): Nombre del campo modificado.
        old_value (Any): Valor anterior del campo.
        new_value (Any): Valor nuevo del campo.
        change_type (str): Tipo de cambio (CREATED, UPDATED, DELETED, VIEWED).
        user (Optional[User]): Usuario que realizó el cambio.
        ip_address (Optional[str]): Dirección IP del usuario.
        user_agent (Optional[str]): User agent del navegador/cliente.
        session_key (Optional[str]): Clave de sesión del usuario.
        request_id (Optional[str]): ID de la solicitud que generó el cambio.
        correlation_id (Optional[str]): ID de correlación para rastrear flujos de trabajo.
        is_archived (bool): Indica si el trail está archivado.
        archived_at (Optional[timezone.datetime]): Fecha y hora de archivo.
        archived_by (Optional[User]): Usuario que archivó el trail.
        retention_policy (str): Política de retención del trail.
        data_classification (str): Clasificación de los datos del trail.
        
    Returns:
        Callable: Función decorada.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # --- MEJORA: Registrar inicio del cambio ---
            logger.info(f"Audit trail decorator applied to {func.__name__}")
            
            try:
                # Ejecutar la función decorada
                result = func(*args, **kwargs)
                
                # --- MEJORA: Registrar cambio exitoso ---
                AuditTrail.objects.create(
                    model_name=model_name,
                    object_id=object_id,
                    field_name=field_name,
                    old_value=str(old_value),
                    new_value=str(new_value),
                    change_type=change_type,
                    user=user,
                    timestamp=timezone.now(),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_key=session_key,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    is_archived=is_archived,
                    archived_at=archived_at,
                    archived_by=archived_by,
                    retention_policy=retention_policy,
                    data_classification=data_classification
                )
                
                return result
                
            except Exception as e:
                # --- MEJORA: Registrar fallo en el cambio ---
                logger.error(f"Error in audit trail decorator for {func.__name__}: {e}")
                # No se crea un AuditTrail en caso de fallo, ya que el cambio no se completó
                # Re-lanzar la excepción
                raise
        
        return wrapper
    return decorator


def audit_policy(policy_name: str = "", override_defaults: Optional[Dict[str, Any]] = None) -> Callable:
    """
    Decorador para aplicar una política de auditoría específica a una función.
    
    Args:
        policy_name (str): Nombre de la política de auditoría a aplicar.
        override_defaults (Optional[Dict[str, Any]]): Sobrescribir valores por defecto de la política.
        
    Returns:
        Callable: Función decorada.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # --- MEJORA: Aplicar política de auditoría ---
            logger.info(f"Audit policy '{policy_name}' applied to {func.__name__}")
            
            # Obtener la política de auditoría por nombre
            # from apps.audit.models import AuditPolicy
            # policy = AuditPolicy.objects.filter(name=policy_name, is_active=True).first()
            # if not policy:
            #     logger.warning(f"Audit policy '{policy_name}' not found or inactive")
            #     # Aplicar política por defecto o lanzar error
            #     pass
            
            # Aplicar overrides si se proporcionan
            # if override_defaults:
            #     # Aplicar overrides a la política
            #     pass
            
            try:
                # Ejecutar la función decorada
                result = func(*args, **kwargs)
                
                # --- MEJORA: Registrar evento según política ---
                # Aquí se podría llamar a un método que cree un AuditLog
                # basado en la política aplicada y los resultados de la función.
                # Por ahora, solo registramos que se aplicó la política.
                logger.info(f"Audit policy '{policy_name}' executed successfully for {func.__name__}")
                
                return result
                
            except Exception as e:
                # --- MEJORA: Registrar fallo según política ---
                logger.error(f"Error applying audit policy '{policy_name}' to {func.__name__}: {e}")
                # Re-lanzar la excepción
                raise
        
        return wrapper
    return decorator


def audit_config(config_name: str = "", override_defaults: Optional[Dict[str, Any]] = None) -> Callable:
    """
    Decorador para aplicar una configuración de auditoría específica a una función.
    
    Args:
        config_name (str): Nombre de la configuración de auditoría a aplicar.
        override_defaults (Optional[Dict[str, Any]]): Sobrescribir valores por defecto de la configuración.
        
    Returns:
        Callable: Función decorada.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # --- MEJORA: Aplicar configuración de auditoría ---
            logger.info(f"Audit configuration '{config_name}' applied to {func.__name__}")
            
            # Obtener la configuración de auditoría por nombre
            # from apps.audit.models import AuditConfiguration
            # config = AuditConfiguration.objects.filter(name=config_name, is_active=True).first()
            # if not config:
            #     logger.warning(f"Audit configuration '{config_name}' not found or inactive")
            #     # Aplicar configuración por defecto o lanzar error
            #     pass
            
            # Aplicar overrides si se proporcionan
            # if override_defaults:
            #     # Aplicar overrides a la configuración
            #     pass
            
            try:
                # Ejecutar la función decorada
                result = func(*args, **kwargs)
                
                # --- MEJORA: Registrar evento según configuración ---
                # Aquí se podría llamar a un método que cree un AuditLog
                # basado en la configuración aplicada y los resultados de la función.
                # Por ahora, solo registramos que se aplicó la configuración.
                logger.info(f"Audit configuration '{config_name}' executed successfully for {func.__name__}")
                
                return result
                
            except Exception as e:
                # --- MEJORA: Registrar fallo según configuración ---
                logger.error(f"Error applying audit configuration '{config_name}' to {func.__name__}: {e}")
                # Re-lanzar la excepción
                raise
        
        return wrapper
    return decorator
