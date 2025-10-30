# apps/audit/middleware.py
"""
SMGI Backend - Audit Middleware
Sistema de Monitoreo Geoespacial Inteligente
Middleware personalizado para registrar eventos de auditoría automáticamente
"""
import logging
import uuid
import json
from typing import Dict, Any, Optional, Union
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext_lazy as _
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt

from apps.audit.models import (
    AuditLog, AuditTrail, AuditPolicy, AuditConfiguration,
    AuditEventType, AuditEventSeverity, AuditEventStatus, DataClassification
)
# Importar modelos relacionados
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert
from apps.reports.models import Report
from apps.notifications.models import Notification, EmailNotification, WebhookNotification

logger = logging.getLogger('apps.audit.middleware')


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware personalizado para registrar eventos de auditoría automáticamente.
    Intercepta solicitudes y respuestas HTTP para crear registros en AuditLog.
    """

    def __init__(self, get_response=None):
        """
        Inicializa el middleware de auditoría.

        Args:
            get_response (callable): Callable para obtener la respuesta.
        """
        super().__init__(get_response)
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        self.logger.info("AuditMiddleware initialized")

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Procesa la solicitud entrante y registra el inicio de la auditoría.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.

        Returns:
            Optional[HttpResponse]: None para continuar con la vista, o HttpResponse para cortocircuitar.
        """
        # --- MEJORA: Registrar inicio de la solicitud ---
        self.logger.debug(f"Processing request: {request.method} {request.path}")

        # Verificar si la solicitud debe ser auditada
        if not self.should_audit_request(request):
            self.logger.debug(f"Skipping audit for request: {request.method} {request.path}")
            return None # No auditar, continuar con la vista

        # Extraer información de la solicitud
        user_info = self.extract_user_info(request)
        ip_address = self.extract_ip_address(request)
        user_agent = self.extract_user_agent(request)
        session_info = self.extract_session_info(request)
        request_info = self.extract_request_info(request)

        # Crear entrada de auditoría inicial
        audit_log_entry = AuditLog.objects.create(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.API_CALL,
            severity=AuditEventSeverity.LOW, # Ajustar según el endpoint
            status=AuditEventStatus.PENDING,
            user=user_info.get('user'),
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=request_info.get('resource_type', 'API'),
            resource_id=request_info.get('resource_id', ''),
            action=request.method,
            description=f"API call to {request.path}",
            details={
                'method': request.method,
                'path': request.path,
                'query_params': request_info.get('query_params', {}),
                'body': request_info.get('body', {}),
                'headers': request_info.get('headers', {}),
                'session_key': session_info.get('session_key', ''),
                'csrf_token': request_info.get('csrf_token', ''),
                'request_id': request_info.get('request_id', ''),
                'correlation_id': request_info.get('correlation_id', ''),
            },
            timestamp=timezone.now(),
            duration_ms=0, # Se actualizará en process_response
            success=True, # Asumir éxito hasta que se demuestre lo contrario
            error_message='',
            metadata={
                'middleware_version': '1.0.0',
                'audit_middleware': True,
            },
            tags=['api_call', 'http_request'],
            related_events=[],
            parent_event=None,
            external_reference_id='',
            external_system='',
            is_archived=False,
            archived_at=None,
            archived_by=None,
            retention_policy='default',
            data_classification=DataClassification.INTERNAL
        )

        # Almacenar la entrada de auditoría en el request para usarla en process_response
        request.audit_log_entry = audit_log_entry

        self.logger.info(f"Audit log entry created for request: {request.method} {request.path} - ID: {audit_log_entry.event_id}")
        return None # Continuar con la vista

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Procesa la respuesta saliente y actualiza la auditoría.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.
            response (HttpResponse): Objeto de respuesta HTTP.

        Returns:
            HttpResponse: Objeto de respuesta HTTP actualizado.
        """
        # --- MEJORA: Registrar finalización de la solicitud ---
        self.logger.debug(f"Processing response for request: {request.method} {request.path}")

        # Verificar si hay una entrada de auditoría asociada
        audit_log_entry = getattr(request, 'audit_log_entry', None)
        if not audit_log_entry:
            self.logger.debug(f"No audit log entry found for response: {request.method} {request.path}")
            return response # No hay auditoría, devolver respuesta original

        # Extraer información de la respuesta
        response_info = self.extract_response_info(response)

        # Calcular duración
        duration_ms = int((timezone.now() - audit_log_entry.timestamp).total_seconds() * 1000)

        # Actualizar entrada de auditoría
        audit_log_entry.duration_ms = duration_ms
        audit_log_entry.status = AuditEventStatus.COMPLETED
        audit_log_entry.success = response.status_code < 400
        audit_log_entry.error_message = response_info.get('error_message', '')
        
        # Actualizar detalles con información de la respuesta
        audit_log_entry.details.update({
            'status_code': response.status_code,
            'content_type': response_info.get('content_type', ''),
            'content_length': response_info.get('content_length', 0),
            'response_headers': response_info.get('headers', {}),
            'duration_ms': duration_ms,
        })
        
        # Ajustar severidad según el código de estado
        if response.status_code >= 500:
            audit_log_entry.severity = AuditEventSeverity.CRITICAL
        elif response.status_code >= 400:
            audit_log_entry.severity = AuditEventSeverity.HIGH
        elif response.status_code >= 300:
            audit_log_entry.severity = AuditEventSeverity.MEDIUM
        else:
            audit_log_entry.severity = AuditEventSeverity.LOW

        # Guardar cambios
        audit_log_entry.save(update_fields=[
            'duration_ms', 'status', 'success', 'error_message', 'details', 'severity'
        ])

        self.logger.info(f"Audit log entry updated for response: {request.method} {request.path} - Status: {response.status_code}, Duration: {duration_ms}ms")
        return response # Devolver respuesta original

    def process_exception(self, request: HttpRequest, exception: Exception) -> Optional[HttpResponse]:
        """
        Procesa excepciones no manejadas durante la solicitud.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.
            exception (Exception): Excepción no manejada.

        Returns:
            Optional[HttpResponse]: None para usar el manejador de excepciones por defecto.
        """
        # --- MEJORA: Registrar excepción no manejada ---
        self.logger.error(f"Unhandled exception in request: {request.method} {request.path} - {exception}")

        # Verificar si hay una entrada de auditoría asociada
        audit_log_entry = getattr(request, 'audit_log_entry', None)
        if not audit_log_entry:
            self.logger.debug(f"No audit log entry found for exception: {request.method} {request.path}")
            return None # No hay auditoría, usar manejador por defecto

        # Registrar la excepción en la entrada de auditoría
        self.log_exception(audit_log_entry, exception)

        # No devolver una respuesta aquí para que Django use su manejador de excepciones por defecto
        return None

    # --- MÉTODOS AUXILIARES ---

    def should_audit_request(self, request: HttpRequest) -> bool:
        """
        Determina si la solicitud actual debe ser auditada.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.

        Returns:
            bool: True si la solicitud debe ser auditada, False en caso contrario.
        """
        # --- MEJORA: Lógica de decisión basada en configuración y políticas ---
        
        # 1. Obtener configuración de auditoría activa
        # En una implementación real, se podría tener una configuración por defecto
        # o buscar la más específica según el entorno o usuario.
        # Por ahora, asumimos una configuración global.
        audit_config = AuditConfiguration.objects.filter(is_active=True).first()
        if not audit_config:
            self.logger.warning("No active audit configuration found. Using defaults.")
            # Asumir valores por defecto razonables
            audit_config = AuditConfiguration(
                name='default',
                is_active=True,
                enable_real_time_logging=True,
                log_level='INFO'
            )
        
        # 2. Verificar si el logging en tiempo real está habilitado
        if not audit_config.enable_real_time_logging:
            self.logger.debug("Real-time logging is disabled in audit configuration.")
            return False
        
        # 3. Verificar nivel de log
        log_level = audit_config.log_level
        if log_level == 'CRITICAL':
            # Solo auditar solicitudes que generen errores críticos
            # Esto se maneja mejor en process_exception
            pass # Permitir auditoría inicial para todas
        elif log_level == 'ERROR':
            # Solo auditar solicitudes que generen errores
            # Esto se maneja mejor en process_exception
            pass # Permitir auditoría inicial para todas
        elif log_level == 'WARNING':
            # Solo auditar solicitudes que generen advertencias o errores
            # Esto se maneja mejor en process_exception
            pass # Permitir auditoría inicial para todas
        elif log_level == 'INFO':
            # Auditar todas las solicitudes informativas y superiores
            pass # Permitir auditoría inicial para todas
        elif log_level == 'DEBUG':
            # Auditar todas las solicitudes, incluso las de depuración
            pass # Permitir auditoría inicial para todas
        
        # 4. Verificar políticas de auditoría
        # En una implementación real, se podrían aplicar políticas específicas
        # basadas en el usuario, IP, path, método, etc.
        # Por ahora, asumimos que todas las solicitudes deben ser auditadas
        # si la configuración lo permite.
        
        # 5. Excluir ciertos paths o métodos (ej: health checks, static files)
        excluded_paths = ['/health/', '/static/', '/media/']
        excluded_methods = ['OPTIONS', 'HEAD'] # Métodos que no modifican estado
        
        if request.path in excluded_paths:
            self.logger.debug(f"Excluded path: {request.path}")
            return False
        
        if request.method in excluded_methods:
            self.logger.debug(f"Excluded method: {request.method}")
            return False
        
        # 6. Verificar si el usuario está autenticado (opcional)
        # Si se requiere que solo usuarios autenticados sean auditados
        # if not request.user.is_authenticated:
        #     self.logger.debug("Unauthenticated request excluded from audit.")
        #     return False
        
        # 7. Verificar si el usuario tiene permisos para ser auditado
        # En una implementación real, se podría verificar si el usuario
        # está en una lista blanca o negra definida en la política.
        # if request.user and not audit_config.should_audit_user(request.user):
        #     self.logger.debug(f"User {request.user.email} excluded from audit by policy.")
        #     return False
        
        # 8. Verificar si la IP está en una lista blanca o negra
        # ip_address = self.extract_ip_address(request)
        # if ip_address and not audit_config.should_audit_ip(ip_address):
        #     self.logger.debug(f"IP {ip_address} excluded from audit by policy.")
        #     return False
        
        # 9. Verificar si el user agent está en una lista blanca o negra
        # user_agent = self.extract_user_agent(request)
        # if user_agent and not audit_config.should_audit_user_agent(user_agent):
        #     self.logger.debug(f"User agent excluded from audit by policy.")
        #     return False
        
        # 10. Verificar si el path coincide con algún patrón excluido
        # excluded_path_patterns = audit_config.excluded_path_patterns
        # if excluded_path_patterns:
        #     import re
        #     for pattern in excluded_path_patterns:
        #         if re.match(pattern, request.path):
        #             self.logger.debug(f"Path {request.path} matches excluded pattern {pattern}.")
        #             return False
        
        # Si pasa todas las verificaciones, auditar la solicitud
        self.logger.debug(f"Request should be audited: {request.method} {request.path}")
        return True

    def extract_user_info(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Extrae información del usuario autenticado desde request.user.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.

        Returns:
            Dict[str, Any]: Diccionario con información del usuario.
        """
        user_info = {
            'user': None,
            'user_id': None,
            'username': '',
            'email': '',
            'full_name': '',
            'is_authenticated': False,
            'is_staff': False,
            'is_superuser': False,
        }
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            user_info.update({
                'user': user,
                'user_id': str(user.id) if user.id else None,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name(),
                'is_authenticated': True,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            })
        
        self.logger.debug(f"Extracted user info: {user_info}")
        return user_info

    def extract_ip_address(self, request: HttpRequest) -> Optional[str]:
        """
        Extrae la dirección IP del cliente desde request.META.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.

        Returns:
            Optional[str]: Dirección IP del cliente o None.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        self.logger.debug(f"Extracted IP address: {ip}")
        return ip

    def extract_user_agent(self, request: HttpRequest) -> Optional[str]:
        """
        Extrae el user agent del cliente desde request.META.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.

        Returns:
            Optional[str]: User agent del cliente o None.
        """
        user_agent = request.META.get('HTTP_USER_AGENT')
        self.logger.debug(f"Extracted user agent: {user_agent}")
        return user_agent

    def extract_session_info(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Extrae información de la sesión desde request.session.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.

        Returns:
            Dict[str, Any]: Diccionario con información de la sesión.
        """
        session_info = {
            'session_key': '',
            'session_data': {},
        }
        
        if hasattr(request, 'session'):
            session_info.update({
                'session_key': request.session.session_key or '',
                'session_data': dict(request.session.items()),
            })
        
        self.logger.debug(f"Extracted session info: {session_info}")
        return session_info

    def extract_request_info(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Extrae información detallada de la solicitud HTTP.

        Args:
            request (HttpRequest): Objeto de solicitud HTTP.

        Returns:
            Dict[str, Any]: Diccionario con información detallada de la solicitud.
        """
        request_info = {
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET.items()),
            'body': {},
            'headers': dict(request.META.items()),
            'csrf_token': request.META.get('CSRF_COOKIE', ''),
            'request_id': request.META.get('HTTP_X_REQUEST_ID', ''),
            'correlation_id': request.META.get('HTTP_X_CORRELATION_ID', ''),
            'resource_type': 'API', # Valor por defecto
            'resource_id': '', # Valor por defecto
        }
        
        # Intentar extraer body (solo para POST/PUT/PATCH)
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.content_type == 'application/json':
                    request_info['body'] = json.loads(request.body.decode('utf-8'))
                else:
                    # Para formularios, usar request.POST
                    request_info['body'] = dict(request.POST.items())
            except Exception as e:
                self.logger.warning(f"Could not parse request body: {e}")
                request_info['body'] = {'error': 'Could not parse request body'}
        
        # Intentar identificar el tipo de recurso y su ID desde el path
        # Ej: /api/gis/services/123/ -> resource_type='gis_service', resource_id='123'
        # Ej: /api/monitoring/jobs/456/ -> resource_type='monitoring_job', resource_id='456'
        # Ej: /api/alerts/alerts/789/ -> resource_type='alert', resource_id='789'
        # Ej: /api/notifications/notifications/abc/ -> resource_type='notification', resource_id='abc'
        # Ej: /api/reports/reports/def/ -> resource_type='report', resource_id='def'
        # Esta lógica puede volverse compleja, por ahora usamos un enfoque simple.
        path_parts = request.path.strip('/').split('/')
        if len(path_parts) >= 3:
            # Asumir que el path tiene la forma /api/resource_type/resource_id/
            # o /api/resource_type/resource_id/action/
            resource_type_candidate = path_parts[1] # 'gis', 'monitoring', 'alerts', 'notifications', 'reports'
            resource_id_candidate = path_parts[2] # '123', 'abc', etc.
            
            # Mapear resource_type_candidate a un nombre más descriptivo
            resource_type_map = {
                'gis': 'gis_service',
                'monitoring': 'monitoring_job',
                'alerts': 'alert',
                'notifications': 'notification',
                'reports': 'report',
                'auth': 'authentication',
                'users': 'user',
                'admin': 'administration',
                'health': 'system_health',
                'stats': 'statistics',
            }
            
            mapped_resource_type = resource_type_map.get(resource_type_candidate, resource_type_candidate)
            request_info['resource_type'] = mapped_resource_type
            request_info['resource_id'] = resource_id_candidate
        
        self.logger.debug(f"Extracted request info: {request_info}")
        return request_info

    def extract_response_info(self, response: HttpResponse) -> Dict[str, Any]:
        """
        Extrae información detallada de la respuesta HTTP.

        Args:
            response (HttpResponse): Objeto de respuesta HTTP.

        Returns:
            Dict[str, Any]: Diccionario con información detallada de la respuesta.
        """
        response_info = {
            'status_code': response.status_code,
            'content_type': response.get('Content-Type', ''),
            'content_length': len(response.content) if hasattr(response, 'content') else 0,
            'headers': dict(response.items()),
            'error_message': '',
        }
        
        # Intentar extraer mensaje de error del cuerpo de la respuesta
        if response.status_code >= 400:
            try:
                if response.get('Content-Type', '').startswith('application/json'):
                    response_data = json.loads(response.content.decode('utf-8'))
                    response_info['error_message'] = response_data.get('detail', '') or response_data.get('error', '') or ''
                else:
                    response_info['error_message'] = response.content.decode('utf-8')[:200] # Limitar longitud
            except Exception as e:
                self.logger.warning(f"Could not parse response error message: {e}")
                response_info['error_message'] = 'Could not parse response error message'
        
        self.logger.debug(f"Extracted response info: {response_info}")
        return response_info

    def create_audit_log_entry(self,  Dict[str, Any]) -> AuditLog:
        """
        Crea una entrada en AuditLog con la información proporcionada.

        Args:
            data (Dict[str, Any]): Diccionario con información de la auditoría.

        Returns:
            AuditLog: Instancia de AuditLog creada.
        """
        # --- MEJORA: Crear entrada de auditoría con datos proporcionados ---
        self.logger.info(f"Creating audit log entry: {data}")
        
        try:
            audit_log_entry = AuditLog.objects.create(**data)
            self.logger.info(f"Audit log entry created successfully: {audit_log_entry.event_id}")
            return audit_log_entry
            
        except Exception as e:
            self.logger.error(f"Error creating audit log entry: {e}")
            # Re-lanzar la excepción para que sea manejada por el caller
            raise

    def update_audit_log_entry(self, audit_log_entry: AuditLog,  Dict[str, Any]) -> AuditLog:
        """
        Actualiza una entrada en AuditLog con la información proporcionada.

        Args:
            audit_log_entry (AuditLog): Instancia de AuditLog a actualizar.
            data (Dict[str, Any]): Diccionario con información de actualización.

        Returns:
            AuditLog: Instancia de AuditLog actualizada.
        """
        # --- MEJORA: Actualizar entrada de auditoría con datos proporcionados ---
        self.logger.info(f"Updating audit log entry: {audit_log_entry.event_id}")
        
        try:
            for key, value in data.items():
                setattr(audit_log_entry, key, value)
            audit_log_entry.save(update_fields=list(data.keys()))
            self.logger.info(f"Audit log entry updated successfully: {audit_log_entry.event_id}")
            return audit_log_entry
            
        except Exception as e:
            self.logger.error(f"Error updating audit log entry {audit_log_entry.event_id}: {e}")
            # Re-lanzar la excepción para que sea manejada por el caller
            raise

    def log_exception(self, audit_log_entry: AuditLog, exception: Exception) -> None:
        """
        Registra una excepción en una entrada de AuditLog.

        Args:
            audit_log_entry (AuditLog): Instancia de AuditLog donde registrar la excepción.
            exception (Exception): Excepción a registrar.
        """
        # --- MEJORA: Registrar excepción en la entrada de auditoría ---
        self.logger.error(f"Logging exception for audit log entry {audit_log_entry.event_id}: {exception}")
        
        try:
            # Actualizar entrada de auditoría con información de la excepción
            audit_log_entry.status = AuditEventStatus.FAILED
            audit_log_entry.success = False
            audit_log_entry.error_message = str(exception)
            audit_log_entry.save(update_fields=['status', 'success', 'error_message'])
            
            self.logger.info(f"Exception logged for audit log entry: {audit_log_entry.event_id}")
            
        except Exception as e:
            self.logger.error(f"Error logging exception for audit log entry {audit_log_entry.event_id}: {e}")
