# apps/audit/tests/test_middleware.py
"""
SMGI Backend - Tests for Audit Middleware
Sistema de Monitoreo Geoespacial Inteligente
Pruebas unitarias para el middleware de auditoría
"""
import pytest
import logging
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware

from apps.audit.middleware import AuditMiddleware
from apps.audit.models import AuditLog, AuditTrail, AuditPolicy, AuditConfiguration
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert
from apps.reports.models import Report
from apps.notifications.models import Notification, EmailNotification, WebhookNotification

logger = logging.getLogger('apps.audit.tests.middleware')


# --- Fixtures ---

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='audit_test_user',
        email='audit@test.com',
        password='testpass123'
    )

@pytest.fixture
def arcgis_service(user):
    return ArcGISService.objects.create(
        name='Audit Test Service',
        base_url='https://audittest.arcgis.com',
        service_type='featureserver',
        created_by=user
    )

@pytest.fixture
def spatial_layer(arcgis_service):
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=1,
        name='Audit Test Layer',
        geometry_type='polygon',
        created_by=arcgis_service.created_by
    )

@pytest.fixture
def monitoring_job(user, arcgis_service, spatial_layer):
    return MonitoringJob.objects.create(
        name='Audit Test Monitoring Job',
        description='Test monitoring job for audit',
        job_id='AUDIT-TEST-JOB-001',
        job_type=MonitoringJob.JOB_TYPE_FEATURE_COUNT,
        service=arcgis_service,
        layer=spatial_layer,
        assigned_to=user,
        is_active=True,
        is_scheduled=True,
        schedule_expression='0 */15 * * * *',
        max_runtime_minutes=60,
        detection_algorithm=MonitoringJob.ALGORITHM_SIMPLE_COUNT,
        change_threshold=5.0,
        alert_on_changes=True,
        alert_on_errors=True,
        alert_threshold='medium',
        last_run=timezone.now() - timedelta(minutes=10),
        last_successful_run=timezone.now() - timedelta(minutes=10),
        next_run=timezone.now() + timedelta(minutes=5),
        consecutive_failures=0,
        status=MonitoringJob.STATUS_ACTIVE,
        created_by=user
    )

@pytest.fixture
def alert(user, arcgis_service, spatial_layer):
    return Alert.objects.create(
        title='Audit Test Alert',
        description='Test alert for audit',
        alert_id='AUDIT-TEST-ALERT-001',
        category=Alert.CATEGORY_CHANGE_DETECTION,
        severity=Alert.SEVERITY_HIGH,
        service=arcgis_service,
        layer=spatial_layer,
        assigned_to=user,
        status=Alert.STATUS_ACTIVE,
        first_detected=timezone.now() - timedelta(minutes=5),
        last_updated=timezone.now() - timedelta(minutes=5),
        acknowledged_at=None,
        resolved_at=None,
        expires_at=timezone.now() + timedelta(hours=1),
        auto_resolve=False,
        auto_resolve_duration=None,
        suppress_similar=False,
        suppression_duration=30,
        notification_sent=False,
        notification_count=0,
        last_notification_sent=None,
        external_ticket_id='',
        metadata={},
        tags=[],
        created_by=user
    )

@pytest.fixture
def report(user, arcgis_service, spatial_layer):
    return Report.objects.create(
        name='Audit Test Report',
        description='Test report for audit',
        report_id='AUDIT-TEST-REPORT-001',
        report_type=Report.REPORT_TYPE_MONITORING_SUMMARY,
        format_type=Report.FORMAT_TYPE_PDF,
        service=arcgis_service,
        layer=spatial_layer,
        assigned_to=user,
        status=Report.STATUS_ACTIVE,
        is_scheduled=True,
        schedule_expression='0 2 * * *',
        max_runtime_minutes=60,
        auto_resolve=False,
        auto_resolve_duration=None,
        suppress_similar=False,
        suppression_duration=30,
        notification_sent=False,
        notification_count=0,
        last_notification_sent=None,
        external_ticket_id='',
        metadata={},
        tags=[],
        created_by=user
    )

@pytest.fixture
def notification(user, alert):
    return Notification.objects.create(
        title='Audit Test Notification',
        message='Test notification for audit',
        short_message='Test notif',
        notification_type=Notification.NOTIFICATION_TYPE_ALERT,
        priority=Notification.PRIORITY_HIGH,
        user=user,
        is_read=False,
        read_at=None,
        link='/alerts/1',
        action_text='View Alert',
        action_url='/alerts/1',
        metadata={},
        alert=alert,
        expires_at=timezone.now() + timedelta(hours=1),
        group_key='test-group',
        is_expired=False,
        should_auto_resolve=False,
        auto_resolve_duration=None,
        suppress_similar=False,
        suppression_duration=30,
        notification_sent=False,
        notification_count=0,
        last_notification_sent=None,
        external_ticket_id='',
        tags=[],
        created_by=user
    )

@pytest.fixture
def email_notification(user, alert):
    return EmailNotification.objects.create(
        subject='Audit Test Email',
        body_text='Test email for audit',
        body_html='<p>Test email for audit</p>',
        recipient_email=user.email,
        recipient_name=user.get_full_name(),
        user=user,
        status=EmailNotification.STATUS_PENDING,
        sent_at=None,
        delivered_at=None,
        opened_at=None,
        clicked_at=None,
        error_message='',
        retry_count=0,
        max_retries=3,
        next_retry_at=None,
        external_id='',
        template_name='alert_notification',
        template_context={},
        priority=EmailNotification.PRIORITY_HIGH,
        has_attachments=False,
        attachments=[],
        cc_emails=[],
        bcc_emails=[],
        metadata={},
        alert=alert,
        expires_at=timezone.now() + timedelta(hours=1),
        group_key='test-email-group',
        is_expired=False,
        should_auto_resolve=False,
        auto_resolve_duration=None,
        suppress_similar=False,
        suppression_duration=30,
        notification_sent=False,
        notification_count=0,
        last_notification_sent=None,
        external_ticket_id='',
        tags=[],
        created_by=user
    )

@pytest.fixture
def webhook_notification(alert):
    return WebhookNotification.objects.create(
        webhook_url='https://audittest.webhook.com',
        method='POST',
        headers={'Content-Type': 'application/json'},
        payload={'test': 'data'},
        auth_type='none',
        auth_credentials={},
        status=WebhookNotification.STATUS_PENDING,
        sent_at=None,
        response_status_code=None,
        response_body='',
        response_time_ms=None,
        error_message='',
        retry_count=0,
        max_retries=3,
        next_retry_at=None,
        external_id='',
        template_name='alert_webhook',
        template_context={},
        priority=WebhookNotification.PRIORITY_HIGH,
        alert=alert,
        expires_at=timezone.now() + timedelta(hours=1),
        group_key='test-webhook-group',
        is_expired=False,
        should_auto_resolve=False,
        auto_resolve_duration=None,
        suppress_similar=False,
        suppression_duration=30,
        notification_sent=False,
        notification_count=0,
        last_notification_sent=None,
        external_ticket_id='',
        tags=[],
        created_by=None # Webhook no tiene usuario asignado
    )

@pytest.fixture
def audit_log(user, alert):
    return AuditLog.objects.create(
        event_id='AUDIT-TEST-EVENT-001',
        title='Audit Test Event',
        message='Test audit event',
        short_message='Test event',
        event_type=AuditLog.EVENT_TYPE_USER_ACTION,
        severity=AuditLog.SEVERITY_MEDIUM,
        status=AuditLog.STATUS_COMPLETED,
        user=user,
        ip_address='127.0.0.1',
        user_agent='Mozilla/5.0',
        resource_type='Alert',
        resource_id=str(alert.id),
        action='create',
        description='Created test alert',
        details={},
        timestamp=timezone.now() - timedelta(minutes=1),
        duration_ms=1000,
        success=True,
        error_message='',
        metadata={},
        tags=['test'],
        related_events=[],
        parent_event=None,
        external_reference_id='',
        external_system='',
        is_archived=False,
        archived_at=None,
        archived_by=None,
        retention_policy='default',
        data_classification=AuditLog.CLASSIFICATION_INTERNAL
    )

@pytest.fixture
def audit_trail(user):
    return AuditTrail.objects.create(
        model_name='Alert',
        object_id='1',
        field_name='status',
        old_value='active',
        new_value='resolved',
        change_type=AuditTrail.CHANGE_TYPE_UPDATED,
        user=user,
        timestamp=timezone.now() - timedelta(minutes=2),
        ip_address='127.0.0.1',
        user_agent='Mozilla/5.0',
        session_key='test_session_key',
        request_id='test_request_id',
        correlation_id='test_correlation_id',
        is_archived=False,
        archived_at=None,
        archived_by=None,
        retention_policy='default',
        data_classification=AuditTrail.CLASSIFICATION_INTERNAL
    )

@pytest.fixture
def audit_policy(user):
    return AuditPolicy.objects.create(
        name='Audit Test Policy',
        description='Test audit policy',
        is_active=True,
        resource_types=['Alert', 'Report'],
        event_types=[AuditLog.EVENT_TYPE_USER_ACTION, AuditLog.EVENT_TYPE_DATA_CHANGE],
        severity_levels=[AuditLog.SEVERITY_HIGH, AuditLog.SEVERITY_CRITICAL],
        actions=['create', 'update', 'delete'],
        users=[user],
        ip_addresses=['127.0.0.1'],
        user_agents=['Mozilla/5.0'],
        retention_days=90,
        archive_after_days=30,
        notify_on_events=True,
        notification_channels=['email'],
        notification_recipients=[user],
        created_by=user,
        modified_by=user
    )

@pytest.fixture
def audit_configuration():
    return AuditConfiguration.objects.create(
        name='Audit Test Configuration',
        description='Test audit configuration',
        is_active=True,
        default_retention_days=90,
        default_archive_after_days=30,
        default_data_classification=AuditConfiguration.CLASSIFICATION_INTERNAL,
        enable_real_time_logging=True,
        enable_batch_logging=False,
        batch_size=100,
        log_level='INFO',
        exclude_sensitive_fields=['password'],
        mask_sensitive_data=True,
        encrypt_audit_logs=False,
        store_audit_trails=True,
        store_user_sessions=True,
        store_api_calls=True,
        store_external_api_calls=True,
        store_internal_api_calls=True,
        store_database_queries=True,
        store_cache_operations=True,
        store_file_operations=True,
        store_email_sending=True,
        store_sms_sending=True,
        store_webhook_sending=True,
        store_push_notification_sending=True,
        store_report_generation=True,
        store_alert_triggering=True,
        store_monitoring_job_scheduling=True,
        store_system_health_checks=True,
        store_data_validation=True,
        store_gis_service_interaction=True,
        store_authentication=True,
        store_authorization=True,
        store_error_handling=True,
        store_performance_monitoring=True,
        created_by=None, # Configuration no tiene usuario asignado
        modified_by=None # Configuration no tiene usuario asignado
    )


# --- Tests for AuditMiddleware ---

class TestAuditMiddleware:

    @pytest.fixture
    def middleware(self):
        return AuditMiddleware()

    @pytest.fixture
    def mock_request(self, user):
        request = HttpRequest()
        request.method = 'GET'
        request.path = '/api/test/'
        request.META = {
            'HTTP_HOST': 'localhost:8000',
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Test Client)',
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_X_FORWARDED_FOR': '192.168.1.100, 127.0.0.1',
            'HTTP_X_REQUEST_ID': 'test-request-id',
            'HTTP_X_CORRELATION_ID': 'test-correlation-id',
        }
        request.user = user
        request.session = MagicMock()
        request.session.session_key = 'test-session-key'
        return request

    @pytest.fixture
    def mock_response(self):
        response = HttpResponse()
        response.status_code = 200
        response.content = b'Test response content'
        return response

    def test_process_request_creates_audit_log(self, middleware, mock_request):
        """Test that process_request creates an audit log entry"""
        # --- MEJORA: Simular que la solicitud debe ser auditada ---
        with patch.object(middleware, 'should_audit_request', return_value=True):
            response = middleware.process_request(mock_request)
            
            # Verificar que no se haya cortocircuitado la solicitud
            assert response is None
            
            # Verificar que se haya creado una entrada de auditoría
            audit_log_entry = getattr(mock_request, 'audit_log_entry', None)
            assert audit_log_entry is not None
            assert audit_log_entry.event_type == AuditLog.EVENT_TYPE_API_CALL
            assert audit_log_entry.user == mock_request.user
            assert audit_log_entry.ip_address == '192.168.1.100' # IP from X-Forwarded-For
            assert audit_log_entry.user_agent == 'Mozilla/5.0 (Test Client)'
            assert audit_log_entry.resource_type == 'API'
            assert audit_log_entry.resource_id == ''
            assert audit_log_entry.action == 'GET'
            assert audit_log_entry.description == f"API call to {mock_request.path}"
            assert audit_log_entry.status == AuditLog.STATUS_PENDING
            assert audit_log_entry.success is True
            assert audit_log_entry.error_message == ''
            assert 'method' in audit_log_entry.details
            assert 'path' in audit_log_entry.details
            assert 'query_params' in audit_log_entry.details
            assert 'body' in audit_log_entry.details
            assert 'headers' in audit_log_entry.details
            assert 'session_key' in audit_log_entry.details
            assert 'csrf_token' in audit_log_entry.details
            assert 'request_id' in audit_log_entry.details
            assert 'correlation_id' in audit_log_entry.details

    def test_process_request_skips_audit_if_not_needed(self, middleware, mock_request):
        """Test that process_request skips audit if should_audit_request returns False"""
        # --- MEJORA: Simular que la solicitud NO debe ser auditada ---
        with patch.object(middleware, 'should_audit_request', return_value=False):
            response = middleware.process_request(mock_request)
            
            # Verificar que no se haya cortocircuitado la solicitud
            assert response is None
            
            # Verificar que NO se haya creado una entrada de auditoría
            audit_log_entry = getattr(mock_request, 'audit_log_entry', None)
            assert audit_log_entry is None

    def test_process_response_updates_audit_log(self, middleware, mock_request, mock_response):
        """Test that process_response updates the audit log entry"""
        # --- MEJORA: Crear una entrada de auditoría simulada en el request ---
        audit_log_entry = AuditLog(
            event_id='test-event-id',
            title='Test Event',
            message='Test audit event',
            short_message='Test event',
            event_type=AuditLog.EVENT_TYPE_API_CALL,
            severity=AuditLog.SEVERITY_LOW,
            status=AuditLog.STATUS_PENDING,
            user=mock_request.user,
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0 (Test Client)',
            resource_type='API',
            resource_id='',
            action='GET',
            description=f"API call to {mock_request.path}",
            details={},
            timestamp=timezone.now() - timedelta(milliseconds=500), # Hace 500ms
            duration_ms=0,
            success=True,
            error_message='',
            metadata={},
            tags=['api_call'],
            related_events=[],
            parent_event=None,
            external_reference_id='',
            external_system='',
            is_archived=False,
            archived_at=None,
            archived_by=None,
            retention_policy='default',
            data_classification=AuditLog.CLASSIFICATION_INTERNAL
        )
        audit_log_entry.save()
        mock_request.audit_log_entry = audit_log_entry
        
        # --- MEJORA: Simular tiempo de procesamiento ---
        with patch('django.utils.timezone.now', side_effect=[
            audit_log_entry.timestamp + timedelta(milliseconds=500), # Tiempo de inicio (ya pasado)
            audit_log_entry.timestamp + timedelta(milliseconds=1000)  # Tiempo de finalización
        ]):
            response = middleware.process_response(mock_request, mock_response)
            
            # Verificar que la respuesta sea la misma
            assert response == mock_response
            
            # Verificar que la entrada de auditoría se haya actualizado
            audit_log_entry.refresh_from_db()
            assert audit_log_entry.status == AuditLog.STATUS_COMPLETED
            assert audit_log_entry.success is True
            assert audit_log_entry.error_message == ''
            assert audit_log_entry.duration_ms == 500 # 1000ms - 500ms
            assert 'status_code' in audit_log_entry.details
            assert audit_log_entry.details['status_code'] == 200
            assert 'content_type' in audit_log_entry.details
            assert 'content_length' in audit_log_entry.details
            assert audit_log_entry.details['content_length'] == len(mock_response.content)

    def test_process_exception_logs_exception(self, middleware, mock_request):
        """Test that process_exception logs an exception"""
        # --- MEJORA: Crear una entrada de auditoría simulada en el request ---
        audit_log_entry = AuditLog(
            event_id='test-exception-event-id',
            title='Test Exception Event',
            message='Test audit exception event',
            short_message='Test exception event',
            event_type=AuditLog.EVENT_TYPE_API_CALL,
            severity=AuditLog.SEVERITY_HIGH,
            status=AuditLog.STATUS_PENDING,
            user=mock_request.user,
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0 (Test Client)',
            resource_type='API',
            resource_id='',
            action='GET',
            description=f"API call to {mock_request.path}",
            details={},
            timestamp=timezone.now() - timedelta(milliseconds=100),
            duration_ms=0,
            success=True,
            error_message='',
            metadata={},
            tags=['api_call'],
            related_events=[],
            parent_event=None,
            external_reference_id='',
            external_system='',
            is_archived=False,
            archived_at=None,
            archived_by=None,
            retention_policy='default',
            data_classification=AuditLog.CLASSIFICATION_INTERNAL
        )
        audit_log_entry.save()
        mock_request.audit_log_entry = audit_log_entry
        
        # --- MEJORA: Simular una excepción ---
        exception = Exception("Test exception")
        
        # --- MEJORA: Simular tiempo de procesamiento ---
        with patch('django.utils.timezone.now', side_effect=[
            audit_log_entry.timestamp + timedelta(milliseconds=100), # Tiempo de inicio (ya pasado)
            audit_log_entry.timestamp + timedelta(milliseconds=200)  # Tiempo de finalización
        ]):
            response = middleware.process_exception(mock_request, exception)
            
            # Verificar que no se haya cortocircuitado la solicitud
            assert response is None
            
            # Verificar que la entrada de auditoría se haya actualizado con la excepción
            audit_log_entry.refresh_from_db()
            assert audit_log_entry.status == AuditLog.STATUS_FAILED
            assert audit_log_entry.success is False
            assert "Test exception" in audit_log_entry.error_message
            assert audit_log_entry.duration_ms == 100 # 200ms - 100ms

    def test_should_audit_request_allows_valid_requests(self, middleware, mock_request):
        """Test that should_audit_request allows valid requests"""
        # --- MEJORA: Simular una configuración de auditoría activa ---
        with patch('apps.audit.middleware.AuditConfiguration') as mock_config_model:
            mock_config = MagicMock()
            mock_config.is_active = True
            mock_config.enable_real_time_logging = True
            mock_config.log_level = 'INFO'
            mock_config_model.objects.filter.return_value.first.return_value = mock_config
            
            # --- MEJORA: Verificar que la solicitud sea auditada ---
            assert middleware.should_audit_request(mock_request) is True

    def test_should_audit_request_blocks_excluded_paths(self, middleware, mock_request):
        """Test that should_audit_request blocks excluded paths"""
        # --- MEJORA: Simular una solicitud a un path excluido ---
        mock_request.path = '/health/'
        
        # --- MEJORA: Simular una configuración de auditoría activa ---
        with patch('apps.audit.middleware.AuditConfiguration') as mock_config_model:
            mock_config = MagicMock()
            mock_config.is_active = True
            mock_config.enable_real_time_logging = True
            mock_config.log_level = 'INFO'
            mock_config_model.objects.filter.return_value.first.return_value = mock_config
            
            # --- MEJORA: Verificar que la solicitud NO sea auditada ---
            assert middleware.should_audit_request(mock_request) is False

    def test_should_audit_request_blocks_excluded_methods(self, middleware, mock_request):
        """Test that should_audit_request blocks excluded methods"""
        # --- MEJORA: Simular una solicitud con un método excluido ---
        mock_request.method = 'OPTIONS'
        
        # --- MEJORA: Simular una configuración de auditoría activa ---
        with patch('apps.audit.middleware.AuditConfiguration') as mock_config_model:
            mock_config = MagicMock()
            mock_config.is_active = True
            mock_config.enable_real_time_logging = True
            mock_config.log_level = 'INFO'
            mock_config_model.objects.filter.return_value.first.return_value = mock_config
            
            # --- MEJORA: Verificar que la solicitud NO sea auditada ---
            assert middleware.should_audit_request(mock_request) is False

    def test_extract_user_info(self, middleware, user, mock_request):
        """Test that extract_user_info extracts user info correctly"""
        # --- MEJORA: Extraer información del usuario ---
        user_info = middleware.extract_user_info(mock_request)
        
        # --- MEJORA: Verificar que la información sea correcta ---
        assert user_info['user'] == user
        assert user_info['user_id'] == str(user.id)
        assert user_info['username'] == user.username
        assert user_info['email'] == user.email
        assert user_info['full_name'] == user.get_full_name()
        assert user_info['is_authenticated'] is True
        assert user_info['is_staff'] is False # Por defecto en el fixture
        assert user_info['is_superuser'] is False # Por defecto en el fixture

    def test_extract_ip_address(self, middleware, mock_request):
        """Test that extract_ip_address extracts IP correctly"""
        # --- MEJORA: Extraer dirección IP ---
        ip_address = middleware.extract_ip_address(mock_request)
        
        # --- MEJORA: Verificar que la IP sea correcta (de X-Forwarded-For) ---
        assert ip_address == '192.168.1.100'

    def test_extract_user_agent(self, middleware, mock_request):
        """Test that extract_user_agent extracts user agent correctly"""
        # --- MEJORA: Extraer user agent ---
        user_agent = middleware.extract_user_agent(mock_request)
        
        # --- MEJORA: Verificar que el user agent sea correcto ---
        assert user_agent == 'Mozilla/5.0 (Test Client)'

    def test_extract_session_info(self, middleware, mock_request):
        """Test that extract_session_info extracts session info correctly"""
        # --- MEJORA: Extraer información de sesión ---
        session_info = middleware.extract_session_info(mock_request)
        
        # --- MEJORA: Verificar que la información de sesión sea correcta ---
        assert session_info['session_key'] == 'test-session-key'
        assert isinstance(session_info['session_data'], dict)

    def test_extract_request_info(self, middleware, mock_request):
        """Test that extract_request_info extracts request info correctly"""
        # --- MEJORA: Extraer información de solicitud ---
        request_info = middleware.extract_request_info(mock_request)
        
        # --- MEJORA: Verificar que la información de solicitud sea correcta ---
        assert request_info['method'] == 'GET'
        assert request_info['path'] == '/api/test/'
        assert isinstance(request_info['query_params'], dict)
        assert isinstance(request_info['body'], dict)
        assert isinstance(request_info['headers'], dict)
        assert request_info['csrf_token'] == ''
        assert request_info['request_id'] == 'test-request-id'
        assert request_info['correlation_id'] == 'test-correlation-id'
        assert request_info['resource_type'] == 'API' # Valor por defecto
        assert request_info['resource_id'] == '' # Valor por defecto

    def test_extract_response_info(self, middleware, mock_response):
        """Test that extract_response_info extracts response info correctly"""
        # --- MEJORA: Extraer información de respuesta ---
        response_info = middleware.extract_response_info(mock_response)
        
        # --- MEJORA: Verificar que la información de respuesta sea correcta ---
        assert response_info['status_code'] == 200
        assert response_info['content_type'] == ''
        assert response_info['content_length'] == len(mock_response.content)
        assert isinstance(response_info['headers'], dict)
        assert response_info['error_message'] == ''

    def test_create_audit_log_entry(self, middleware, user, mock_request):
        """Test that create_audit_log_entry creates an audit log entry correctly"""
        # --- MEJORA: Preparar datos para crear la entrada de auditoría ---
        data = {
            'event_id': 'test-create-event-id',
            'title': 'Test Create Event',
            'message': 'Test create audit event',
            'short_message': 'Test create event',
            'event_type': AuditLog.EVENT_TYPE_API_CALL,
            'severity': AuditLog.SEVERITY_LOW,
            'status': AuditLog.STATUS_PENDING,
            'user': user,
            'ip_address': '127.0.0.1',
            'user_agent': 'Mozilla/5.0 (Test Client)',
            'resource_type': 'API',
            'resource_id': '',
            'action': 'GET',
            'description': f"API call to {mock_request.path}",
            'details': {},
            'timestamp': timezone.now(),
            'duration_ms': 0,
            'success': True,
            'error_message': '',
            'metadata': {},
            'tags': ['api_call'],
            'related_events': [],
            'parent_event': None,
            'external_reference_id': '',
            'external_system': '',
            'is_archived': False,
            'archived_at': None,
            'archived_by': None,
            'retention_policy': 'default',
            'data_classification': AuditLog.CLASSIFICATION_INTERNAL
        }
        
        # --- MEJORA: Crear la entrada de auditoría ---
        audit_log_entry = middleware.create_audit_log_entry(data)
        
        # --- MEJORA: Verificar que la entrada se haya creado correctamente ---
        assert audit_log_entry is not None
        assert audit_log_entry.event_id == 'test-create-event-id'
        assert audit_log_entry.title == 'Test Create Event'
        assert audit_log_entry.message == 'Test create audit event'
        assert audit_log_entry.short_message == 'Test create event'
        assert audit_log_entry.event_type == AuditLog.EVENT_TYPE_API_CALL
        assert audit_log_entry.severity == AuditLog.SEVERITY_LOW
        assert audit_log_entry.status == AuditLog.STATUS_PENDING
        assert audit_log_entry.user == user
        assert audit_log_entry.ip_address == '127.0.0.1'
        assert audit_log_entry.user_agent == 'Mozilla/5.0 (Test Client)'
        assert audit_log_entry.resource_type == 'API'
        assert audit_log_entry.resource_id == ''
        assert audit_log_entry.action == 'GET'
        assert audit_log_entry.description == f"API call to {mock_request.path}"
        assert isinstance(audit_log_entry.details, dict)
        assert audit_log_entry.timestamp is not None
        assert audit_log_entry.duration_ms == 0
        assert audit_log_entry.success is True
        assert audit_log_entry.error_message == ''
        assert isinstance(audit_log_entry.metadata, dict)
        assert 'api_call' in audit_log_entry.tags
        assert isinstance(audit_log_entry.related_events, list)
        assert audit_log_entry.parent_event is None
        assert audit_log_entry.external_reference_id == ''
        assert audit_log_entry.external_system == ''
        assert audit_log_entry.is_archived is False
        assert audit_log_entry.archived_at is None
        assert audit_log_entry.archived_by is None
        assert audit_log_entry.retention_policy == 'default'
        assert audit_log_entry.data_classification == AuditLog.CLASSIFICATION_INTERNAL

    def test_update_audit_log_entry(self, middleware, audit_log):
        """Test that update_audit_log_entry updates an audit log entry correctly"""
        # --- MEJORA: Preparar datos para actualizar la entrada de auditoría ---
        update_data = {
            'status': AuditLog.STATUS_COMPLETED,
            'success': True,
            'error_message': '',
            'duration_ms': 1000
        }
        
        # --- MEJORA: Actualizar la entrada de auditoría ---
        updated_audit_log = middleware.update_audit_log_entry(audit_log, update_data)
        
        # --- MEJORA: Verificar que la entrada se haya actualizado correctamente ---
        assert updated_audit_log.status == AuditLog.STATUS_COMPLETED
        assert updated_audit_log.success is True
        assert updated_audit_log.error_message == ''
        assert updated_audit_log.duration_ms == 1000

    def test_log_exception(self, middleware, audit_log):
        """Test that log_exception logs an exception correctly"""
        # --- MEJORA: Preparar una excepción para registrar ---
        exception = Exception("Test log exception")
        
        # --- MEJORA: Registrar la excepción ---
        middleware.log_exception(audit_log, exception)
        
        # --- MEJORA: Verificar que la entrada se haya actualizado con la excepción ---
        audit_log.refresh_from_db()
        assert audit_log.status == AuditLog.STATUS_FAILED
        assert audit_log.success is False
        assert "Test log exception" in audit_log.error_message
