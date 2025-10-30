# apps/common/exceptions.py
"""
SMGI Backend - Common Exceptions
Sistema de Monitoreo Geoespacial Inteligente
Excepciones personalizadas para el sistema SMGI Backend
"""
import logging
import uuid
from typing import Optional, Dict, Any
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


logger = logging.getLogger('apps.common.exceptions')


class SMGIBaseException(APIException):
    """
    Excepción base para todas las excepciones personalizadas del SMGI Backend.
    Hereda de APIException para integración con DRF.
    """
    
    def __init__(self, message: str = "SMGI Backend error", error_code: str = "SMGI_BACKEND_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
        logger.error(f"SMGIBaseException: {self.message} (Error Code: {self.error_code})")


# --- Excepciones de Autenticación ---

class SMGIAuthenticationError(SMGIBaseException):
    """Excepción para errores de autenticación"""
    
    def __init__(self, message: str = "Authentication failed", auth_type: Optional[str] = None, auth_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHENTICATION_ERROR", details)
        self.auth_type = auth_type
        self.auth_error = auth_error
        logger.error(f"SMGIAuthenticationError: {self.message} (Auth Type: {self.auth_type}, Auth Error: {self.auth_error})")


class SMGIAuthorizationError(SMGIBaseException):
    """Excepción para errores de autorización"""
    
    def __init__(self, message: str = "Authorization denied", resource: Optional[str] = None, permission: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHORIZATION_DENIED", details)
        self.resource = resource
        self.permission = permission
        logger.error(f"SMGIAuthorizationError: {self.message} (Resource: {self.resource}, Permission: {self.permission})")


class SMGIResourceNotFoundError(SMGIBaseException):
    """Excepción para recursos no encontrados"""
    
    def __init__(self, message: str = "Resource not found", resource_type: Optional[str] = None, resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RESOURCE_NOT_FOUND", details)
        self.resource_type = resource_type
        self.resource_id = resource_id
        logger.error(f"SMGIResourceNotFoundError: {self.message} (Resource Type: {self.resource_type}, Resource ID: {self.resource_id})")


# --- Excepciones de Datos ---

class SMGIAttributeError(SMGIBaseException):
    """Excepción para errores de atributos de modelos"""
    
    def __init__(self, message: str = "Attribute error", attribute_name: Optional[str] = None, attribute_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "ATTRIBUTE_ERROR", details)
        self.attribute_name = attribute_name
        self.attribute_error = attribute_error
        logger.error(f"SMGIAttributeError: {self.message} (Attribute Name: {self.attribute_name}, Attribute Error: {self.attribute_error})")


class SMGIQueryError(SMGIBaseException):
    """Excepción para errores de consultas GIS"""
    
    def __init__(self, message: str = "Query error", query_type: Optional[str] = None, query_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "QUERY_ERROR", details)
        self.query_type = query_type
        self.query_error = query_error
        logger.error(f"SMGIQueryError: {self.message} (Query Type: {self.query_type}, Query Error: {self.query_error})")


class SMGIConflictError(SMGIBaseException):
    """Excepción para conflictos de datos"""
    
    def __init__(self, message: str = "Data conflict", conflict_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATA_CONFLICT", details)
        self.conflict_type = conflict_type
        logger.error(f"SMGIConflictError: {self.message} (Conflict Type: {self.conflict_type})")


class SMGIBadRequestError(SMGIBaseException):
    """Excepción para solicitudes HTTP mal formadas"""
    
    def __init__(self, message: str = "Bad request", field: Optional[str] = None, value: Optional[Any] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "BAD_REQUEST", details)
        self.field = field
        self.value = value
        logger.error(f"SMGIBadRequestError: {self.message} (Field: {self.field}, Value: {self.value})")


class SMGIDataIntegrityError(SMGIBaseException):
    """Excepción para errores de integridad de datos"""
    
    def __init__(self, message: str = "Data integrity error", constraint: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATA_INTEGRITY_ERROR", details)
        self.constraint = constraint
        logger.error(f"SMGIDataIntegrityError: {self.message} (Constraint: {self.constraint})")


# --- Excepciones de Red y Servicios ---

class SMGINetworkError(SMGIBaseException):
    """Excepción para errores de red"""
    
    def __init__(self, message: str = "Network error", url: Optional[str] = None, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "NETWORK_ERROR", details)
        self.url = url
        self.status_code = status_code
        logger.error(f"SMGINetworkError: {self.message} (URL: {self.url}, Status Code: {self.status_code})")


class SMGIServiceUnavailableError(SMGIBaseException):
    """Excepción para servicios no disponibles"""
    
    def __init__(self, message: str = "Service unavailable", service_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SERVICE_UNAVAILABLE", details)
        self.service_name = service_name
        logger.error(f"SMGIServiceUnavailableError: {self.message} (Service: {self.service_name})")


class SMGITimeoutError(SMGIBaseException):
    """Excepción para errores de timeout"""
    
    def __init__(self, message: str = "Timeout error", operation: Optional[str] = None, timeout: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "TIMEOUT_ERROR", details)
        self.operation = operation
        self.timeout = timeout
        logger.error(f"SMGITimeoutError: {self.message} (Operation: {self.operation}, Timeout: {self.timeout})")


# --- Excepciones de Configuración ---

class SMGIConfigurationError(SMGIBaseException):
    """Excepción para errores de configuración"""
    
    def __init__(self, message: str = "Configuration error", config_key: Optional[str] = None, config_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key
        self.config_error = config_error
        logger.error(f"SMGIConfigurationError: {self.message} (Config Key: {self.config_key}, Config Error: {self.config_error})")


# --- Excepciones de Cache ---

class SMGICacheError(SMGIBaseException):
    """Excepción para errores de caché"""
    
    def __init__(self, message: str = "Cache error", key: Optional[str] = None, cache_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CACHE_ERROR", details)
        self.key = key
        self.cache_error = cache_error
        logger.error(f"SMGICacheError: {self.message} (Key: {self.key}, Cache Error: {self.cache_error})")


# --- Excepciones de Colas ---

class SMGIQueueError(SMGIBaseException):
    """Excepción para errores de colas de mensajes"""
    
    def __init__(self, message: str = "Queue error", queue_name: Optional[str] = None, queue_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "QUEUE_ERROR", details)
        self.queue_name = queue_name
        self.queue_error = queue_error
        logger.error(f"SMGIQueueError: {self.message} (Queue: {self.queue_name}, Queue Error: {self.queue_error})")


# --- Excepciones de Tareas ---

class SMGITaskError(SMGIBaseException):
    """Excepción para errores de tareas Celery"""
    
    def __init__(self, message: str = "Task error", task_name: Optional[str] = None, task_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "TASK_ERROR", details)
        self.task_name = task_name
        self.task_error = task_error
        logger.error(f"SMGITaskError: {self.message} (Task: {self.task_name}, Task Error: {self.task_error})")


# --- Excepciones de Handlers ---

class SMGIHandlerError(SMGIBaseException):
    """Excepción para errores de handlers de notificaciones"""
    
    def __init__(self, message: str = "Handler error", handler_name: Optional[str] = None, handler_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "HANDLER_ERROR", details)
        self.handler_name = handler_name
        self.handler_error = handler_error
        logger.error(f"SMGIHandlerError: {self.message} (Handler: {self.handler_name}, Handler Error: {self.handler_error})")


# --- Excepciones de Analytics ---

class SMGIAnalyticsError(SMGIBaseException):
    """Excepción para errores de análisis estadístico"""
    
    def __init__(self, message: str = "Analytics error", analytics_type: Optional[str] = None, analytics_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "ANALYTICS_ERROR", details)
        self.analytics_type = analytics_type
        self.analytics_error = analytics_error
        logger.error(f"SMGIAnalyticsError: {self.message} (Analytics Type: {self.analytics_type}, Analytics Error: {self.analytics_error})")


# --- Excepciones de Schedulers ---

class SMGISchedulerError(SMGIBaseException):
    """Excepción para errores de programadores de tareas"""
    
    def __init__(self, message: str = "Scheduler error", scheduler_name: Optional[str] = None, scheduler_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SCHEDULER_ERROR", details)
        self.scheduler_name = scheduler_name
        self.scheduler_error = scheduler_error
        logger.error(f"SMGISchedulerError: {self.message} (Scheduler: {self.scheduler_name}, Scheduler Error: {self.scheduler_error})")


# --- Excepciones de Templates ---

class SMGITemplateError(SMGIBaseException):
    """Excepción para errores de plantillas"""
    
    def __init__(self, message: str = "Template error", template_name: Optional[str] = None, template_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "TEMPLATE_ERROR", details)
        self.template_name = template_name
        self.template_error = template_error
        logger.error(f"SMGITemplateError: {self.message} (Template: {self.template_name}, Template Error: {self.template_error})")


# --- Excepciones de Tests ---

class SMGITestError(SMGIBaseException):
    """Excepción para errores de pruebas unitarias"""
    
    def __init__(self, message: str = "Test error", test_name: Optional[str] = None, test_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "TEST_ERROR", details)
        self.test_name = test_name
        self.test_error = test_error
        logger.error(f"SMGITestError: {self.message} (Test: {self.test_name}, Test Error: {self.test_error})")


# --- Excepciones de Audit ---

class SMGIAuditError(SMGIBaseException):
    """Excepción para errores de auditoría"""
    
    def __init__(self, message: str = "Audit error", audit_type: Optional[str] = None, audit_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUDIT_ERROR", details)
        self.audit_type = audit_type
        self.audit_error = audit_error
        logger.error(f"SMGIAuditError: {self.message} (Audit Type: {self.audit_type}, Audit Error: {self.audit_error})")


# --- Excepciones de Monitoring ---

class SMGIMonitoringError(SMGIBaseException):
    """Excepción para errores de monitoreo"""
    
    def __init__(self, message: str = "Monitoring error", monitoring_type: Optional[str] = None, monitoring_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "MONITORING_ERROR", details)
        self.monitoring_type = monitoring_type
        self.monitoring_error = monitoring_error
        logger.error(f"SMGIMonitoringError: {self.message} (Monitoring Type: {self.monitoring_type}, Monitoring Error: {self.monitoring_error})")


# --- Excepciones de Políticas de Datos ---

class SMGIDataMaskingPolicyError(SMGIBaseException):
    """Excepción para errores de políticas de enmascaramiento de datos"""
    
    def __init__(self, message: str = "Data masking policy error", masking_type: Optional[str] = None, masking_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATA_MASKING_POLICY_ERROR", details)
        self.masking_type = masking_type
        self.masking_error = masking_error
        logger.error(f"SMGIDataMaskingPolicyError: {self.message} (Masking Type: {self.masking_type}, Masking Error: {self.masking_error})")


class SMGIDataAnonymizationPolicyError(SMGIBaseException):
    """Excepción para errores de políticas de anonimización de datos"""
    
    def __init__(self, message: str = "Data anonymization policy error", anonymization_type: Optional[str] = None, anonymization_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATA_ANONYMIZATION_POLICY_ERROR", details)
        self.anonymization_type = anonymization_type
        self.anonymization_error = anonymization_error
        logger.error(f"SMGIDataAnonymizationPolicyError: {self.message} (Anonymization Type: {self.anonymization_type}, Anonymization Error: {self.anonymization_error})")


class SMGIDataSecurityPolicyError(SMGIBaseException):
    """Excepción para errores de políticas de seguridad de datos"""
    
    def __init__(self, message: str = "Data security policy error", security_type: Optional[str] = None, security_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATA_SECURITY_POLICY_ERROR", details)
        self.security_type = security_type
        self.security_error = security_error
        logger.error(f"SMGIDataSecurityPolicyError: {self.message} (Security Type: {self.security_type}, Security Error: {self.security_error})")


class SMGIDataCompliancePolicyError(SMGIBaseException):
    """Excepción para errores de políticas de cumplimiento de datos"""
    
    def __init__(self, message: str = "Data compliance policy error", compliance_type: Optional[str] = None, compliance_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATA_COMPLIANCE_POLICY_ERROR", details)
        self.compliance_type = compliance_type
        self.compliance_error = compliance_error
        logger.error(f"SMGIDataCompliancePolicyError: {self.message} (Compliance Type: {self.compliance_type}, Compliance Error: {self.compliance_error})")


class SMGIDataEncryptionPolicyError(SMGIBaseException):
    """Excepción para errores de políticas de cifrado de datos"""
    
    def __init__(self, message: str = "Data encryption policy error", encryption_type: Optional[str] = None, encryption_error: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATA_ENCRYPTION_POLICY_ERROR", details)
        self.encryption_type = encryption_type
        self.encryption_error = encryption_error
        logger.error(f"SMGIDataEncryptionPolicyError: {self.message} (Encryption Type: {self.encryption_type}, Encryption Error: {self.encryption_error})")

