# apps/audit/tests/test_models.py
"""
SMGI Backend - Tests for Audit Models
Sistema de Monitoreo Geoespacial Inteligente
Pruebas unitarias para los modelos del sistema de auditoría
"""
import pytest
import logging
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.audit.models import (
    AuditLog, AuditTrail, AuditPolicy, AuditConfiguration,
    AuditEventType, AuditEventSeverity, AuditEventStatus, DataClassification
)


logger = logging.getLogger('apps.audit.tests.models')


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
def audit_log(user, arcgis_service, spatial_layer):
    return AuditLog.objects.create(
        event_id='AUDIT-TEST-001',
        title='Test Audit Log',
        description='This is a test audit log.',
        message='Test audit log message.',
        short_message='Test audit log',
        event_type=AuditEventType.USER_ACTION,
        severity=AuditEventSeverity.MEDIUM,
        status=AuditEventStatus.PENDING,
        user=user,
        ip_address='127.0.0.1',
        user_agent='Mozilla/5.0 (Test Client)',
        resource_type='Alert',
        resource_id='ALERT-TEST-001',
        action='create',
        details={},
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
        data_classification=DataClassification.INTERNAL,
        created_by=user
    )

@pytest.fixture
def audit_trail(user, arcgis_service, spatial_layer):
    return AuditTrail.objects.create(
        model_name='Alert',
        object_id='ALERT-TEST-001',
        field_name='status',
        old_value='active',
        new_value='resolved',
        change_type='UPDATED',
        user=user,
        ip_address='127.0.0.1',
        user_agent='Mozilla/5.0 (Test Client)',
        session_key='test_session_key',
        request_id='test_request_id',
        correlation_id='test_correlation_id',
        is_archived=False,
        archived_at=None,
        archived_by=None,
        retention_policy='default',
        data_classification=DataClassification.INTERNAL,
        created_by=user
    )

@pytest.fixture
def audit_policy(user, arcgis_service, spatial_layer):
    return AuditPolicy.objects.create(
        name='Test Audit Policy',
        description='A test audit policy.',
        is_active=True,
        resource_types=['Alert', 'Report'],
        event_types=[AuditEventType.USER_ACTION, AuditEventType.DATA_CHANGE],
        severity_levels=[AuditEventSeverity.HIGH, AuditEventSeverity.CRITICAL],
        actions=['create', 'update', 'delete'],
        users=[user],
        ip_addresses=['127.0.0.1'],
        user_agents=['Mozilla/5.0 (Test Client)'],
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
        name='Test Audit Configuration',
        description='A test audit configuration.',
        is_active=True,
        default_retention_days=90,
        default_archive_after_days=30,
        default_data_classification=DataClassification.INTERNAL,
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


# --- Tests for AuditLog Model ---

class TestAuditLogModel:

    def test_str_representation(self, audit_log):
        expected_str = f"[{audit_log.get_severity_display()}] {audit_log.title}"
        assert str(audit_log) == expected_str

    def test_age_hours(self, audit_log):
        # Age should be very small right after creation
        assert audit_log.age_hours < 0.1 # Less than 6 minutes

    def test_is_expired_without_expires_at(self, audit_log):
        audit_log.expires_at = None
        assert not audit_log.is_expired

    def test_is_expired_with_future_expires_at(self, audit_log):
        audit_log.expires_at = timezone.now() + timedelta(hours=1)
        assert not audit_log.is_expired

    def test_is_expired_with_past_expires_at(self, audit_log):
        audit_log.expires_at = timezone.now() - timedelta(hours=1)
        assert audit_log.is_expired

    def test_should_auto_resolve_not_configured(self, audit_log):
        audit_log.auto_resolve = False
        audit_log.auto_resolve_duration = None
        assert not audit_log.should_auto_resolve

    def test_should_auto_resolve_not_yet_due(self, audit_log):
        audit_log.first_detected = timezone.now() - timedelta(hours=1) # Only 1 hour old
        audit_log.auto_resolve_duration = 2 # Should auto-resolve after 2 hours
        audit_log.save()
        assert not audit_log.should_auto_resolve

    def test_should_auto_resolve_due(self, audit_log):
        audit_log.first_detected = timezone.now() - timedelta(hours=3) # 3 hours old
        audit_log.auto_resolve_duration = 2 # Should auto-resolve after 2 hours
        audit_log.save()
        assert audit_log.should_auto_resolve

    def test_time_to_acknowledge_not_yet(self, audit_log):
        audit_log.acknowledged_at = None
        assert audit_log.time_to_acknowledge is None

    def test_time_to_acknowledge_calculated(self, audit_log):
        ack_time = audit_log.first_detected + timedelta(minutes=30)
        audit_log.acknowledged_at = ack_time
        # Simulate saving to DB to ensure consistency
        audit_log.save()
        audit_log.refresh_from_db()
        assert audit_log.time_to_acknowledge == 1800.0 # 30 minutes in seconds

    def test_time_to_resolve_not_yet(self, audit_log):
        audit_log.resolved_at = None
        assert audit_log.time_to_resolve is None

    def test_time_to_resolve_calculated(self, audit_log):
        res_time = audit_log.first_detected + timedelta(hours=1)
        audit_log.resolved_at = res_time
        audit_log.save()
        audit_log.refresh_from_db()
        assert audit_log.time_to_resolve == 3600.0 # 1 hour in seconds

    def test_acknowledge_from_active(self, audit_log, user):
        audit_log.status = AuditEventStatus.ACTIVE
        audit_log.save()
        assert audit_log.acknowledge(user, "Test acknowledge")
        audit_log.refresh_from_db()
        assert audit_log.status == AuditEventStatus.ACKNOWLEDGED
        assert audit_log.acknowledged_by == user
        assert audit_log.acknowledged_at is not None
        # Verify an AuditAction was created
        action = AuditAction.objects.filter(audit_log=audit_log, action_type=AuditActionType.ACKNOWLEDGED).first()
        assert action is not None
        assert action.user == user
        assert action.notes == "Test acknowledge"

    def test_acknowledge_from_non_active(self, audit_log, user):
        audit_log.status = AuditEventStatus.RESOLVED
        audit_log.save()
        assert not audit_log.acknowledge(user, "Should not work")
        audit_log.refresh_from_db()
        assert audit_log.status == AuditEventStatus.RESOLVED # Status unchanged

    def test_resolve_from_active_or_acknowledged(self, audit_log, user):
        # Test from ACTIVE
        audit_log.status = AuditEventStatus.ACTIVE
        audit_log.save()
        assert audit_log.resolve(user, "Test resolve from active")
        audit_log.refresh_from_db()
        assert audit_log.status == AuditEventStatus.RESOLVED
        assert audit_log.resolved_by == user
        assert audit_log.resolved_at is not None

        # Test from ACKNOWLEDGED
        audit_log.status = AuditEventStatus.ACKNOWLEDGED
        audit_log.resolved_at = None
        audit_log.resolved_by = None
        audit_log.save()
        assert audit_log.resolve(user, "Test resolve from acknowledged")
        audit_log.refresh_from_db()
        assert audit_log.status == AuditEventStatus.RESOLVED
        assert audit_log.resolved_by == user
        assert audit_log.resolved_at is not None

    def test_resolve_from_other_status(self, audit_log, user):
        audit_log.status = AuditEventStatus.DISMISSED
        audit_log.save()
        assert not audit_log.resolve(user, "Should not work")
        audit_log.refresh_from_db()
        assert audit_log.status == AuditEventStatus.DISMISSED # Status unchanged

    def test_dismiss(self, audit_log, user):
        audit_log.status = AuditEventStatus.ACTIVE
        audit_log.save()
        assert audit_log.dismiss(user, "Test dismiss")
        audit_log.refresh_from_db()
        assert audit_log.status == AuditEventStatus.DISMISSED

        # Test dismissing again (should still return True but do nothing)
        assert audit_log.dismiss(user, "Test dismiss again")

    def test_assign_to(self, audit_log, user):
        new_user = User.objects.create_user(username='assignee', email='assignee@example.com', password='pass')
        audit_log.assign_to(new_user, user) # user assigns to new_user
        audit_log.refresh_from_db()
        assert audit_log.assigned_to == new_user
        action = AuditAction.objects.filter(audit_log=audit_log, action_type=AuditActionType.ASSIGNED).first()
        assert action is not None
        assert f"Assigned to {new_user.get_full_name()}" in action.notes

    def test_add_comment(self, audit_log, user):
        comment_text = "This is a test comment."
        audit_log.add_comment(user, comment_text)
        action = AuditAction.objects.filter(audit_log=audit_log, action_type=AuditActionType.COMMENTED, notes=comment_text).first()
        assert action is not None
        assert action.user == user

    # Note: Testing get_similar_active_alerts and should_suppress_notifications requires
    # creating multiple alerts and manipulating timestamps, which is more complex.
    # These are good candidates for integration tests or more advanced unit tests.

    def test_increment_notification_count(self, audit_log):
        initial_count = audit_log.notification_count
        audit_log.increment_notification_count()
        audit_log.refresh_from_db()
        assert audit_log.notification_count == initial_count + 1
        assert audit_log.notification_sent is True
        assert audit_log.last_notification_sent is not None


# --- Tests for AuditTrail Model ---

class TestAuditTrailModel:

    def test_str_representation(self, audit_trail):
        expected_str = f"{audit_trail.get_change_type_display()} - {audit_trail.model_name} #{audit_trail.object_id} - {audit_trail.field_name}"
        assert str(audit_trail) == expected_str

    def test_mark_as_read(self, audit_trail):
        assert not audit_trail.is_read
        assert audit_trail.read_at is None

        audit_trail.mark_as_read()
        assert audit_trail.is_read
        assert audit_trail.read_at is not None

    def test_mark_as_unread(self, audit_trail):
        audit_trail.is_read = True
        audit_trail.read_at = timezone.now()
        audit_trail.save()

        audit_trail.mark_as_unread()
        assert not audit_trail.is_read
        assert audit_trail.read_at is None

    def test_is_read(self, audit_trail):
        audit_trail.is_read = True
        audit_trail.read_at = timezone.now()
        audit_trail.save()
        assert audit_trail.is_read

        audit_trail.is_read = False
        audit_trail.read_at = None
        audit_trail.save()
        assert not audit_trail.is_read

    def test_is_unread(self, audit_trail):
        audit_trail.is_read = False
        audit_trail.read_at = None
        audit_trail.save()
        assert audit_trail.is_unread

        audit_trail.is_read = True
        audit_trail.read_at = timezone.now()
        audit_trail.save()
        assert not audit_trail.is_unread

    # Note: Testing get_related_notifications and get_notification_actions requires
    # creating related Notification objects, which is more complex.
    # These are good candidates for integration tests or more advanced unit tests.

    def test_get_related_notifications(self, audit_trail):
        # This test requires creating related Notification objects
        # For now, we'll just test that it doesn't crash
        try:
            notifications = audit_trail.get_related_notifications()
            assert isinstance(notifications, list) # Or queryset
        except Exception as e:
            pytest.fail(f"get_related_notifications raised an exception: {e}")

    def test_get_notification_actions(self, audit_trail):
        # This test requires creating related NotificationAction objects
        # For now, we'll just test that it doesn't crash
        try:
            actions = audit_trail.get_notification_actions()
            assert isinstance(actions, list) # Or queryset
        except Exception as e:
            pytest.fail(f"get_notification_actions raised an exception: {e}")


# --- Tests for AuditPolicy Model ---

class TestAuditPolicyModel:

    def test_str_representation(self, audit_policy):
        expected_str = f"{audit_policy.name} ({'Active' if audit_policy.is_active else 'Inactive'})"
        assert str(audit_policy) == expected_str

    def test_is_active(self, audit_policy):
        assert audit_policy.is_active is True

        audit_policy.is_active = False
        audit_policy.save()
        assert audit_policy.is_active is False

    def test_is_expired(self, audit_policy):
        # Policy without expiration
        audit_policy.expires_at = None
        assert not audit_policy.is_expired

        # Policy with future expiration
        audit_policy.expires_at = timezone.now() + timedelta(days=1)
        assert not audit_policy.is_expired

        # Policy with past expiration
        audit_policy.expires_at = timezone.now() - timedelta(days=1)
        assert audit_policy.is_expired

    def test_enable(self, audit_policy):
        audit_policy.is_active = False
        audit_policy.save()
        assert not audit_policy.is_active

        audit_policy.enable()
        assert audit_policy.is_active is True

    def test_disable(self, audit_policy):
        audit_policy.is_active = True
        audit_policy.save()
        assert audit_policy.is_active is True

        audit_policy.disable()
        assert audit_policy.is_active is False

    def test_activate(self, audit_policy):
        audit_policy.is_active = False
        audit_policy.save()
        assert not audit_policy.is_active

        audit_policy.activate()
        assert audit_policy.is_active is True

    def test_deactivate(self, audit_policy):
        audit_policy.is_active = True
        audit_policy.save()
        assert audit_policy.is_active is True

        audit_policy.deactivate()
        assert audit_policy.is_active is False

    def test_calculate_next_run_simple_interval(self, audit_policy):
        audit_policy.schedule_expression = '30m' # Every 30 minutes
        next_run = audit_policy.calculate_next_run()
        expected_time = timezone.now() + timedelta(minutes=30)
        # Permitir un pequeño margen de error por tiempo de ejecución
        assert abs((next_run - expected_time).total_seconds()) < 2

        audit_policy.schedule_expression = '2h' # Every 2 hours
        next_run = audit_policy.calculate_next_run()
        expected_time = timezone.now() + timedelta(hours=2)
        assert abs((next_run - expected_time).total_seconds()) < 2

    def test_calculate_next_run_invalid_cron_uses_fallback(self, audit_policy):
        audit_policy.schedule_expression = 'invalid_cron'
        next_run = audit_policy.calculate_next_run()
        expected_time = timezone.now() + timedelta(hours=1)
        assert abs((next_run - expected_time).total_seconds()) < 2

    # Tests for record_execution can require mocks of AuditPolicyExecution.objects.create
    # or a transaction of database.
    @patch('apps.audit.models.AuditPolicyExecution.objects.create')
    def test_record_execution_success(self, mock_create, audit_policy, user):
        mock_execution = MagicMock()
        mock_create.return_value = mock_execution

        audit_policy.record_execution(success=True, error_message=None)

        audit_policy.refresh_from_db()
        assert audit_policy.last_run is not None
        assert audit_policy.last_successful_run is not None
        assert audit_policy.consecutive_failures == 0
        mock_create.assert_called_once()

    @patch('apps.audit.models.AuditPolicyExecution.objects.create')
    def test_record_execution_failure(self, mock_create, audit_policy, user):
        mock_execution = MagicMock()
        mock_create.return_value = mock_execution

        initial_failures = audit_policy.consecutive_failures
        error_msg = "Test execution error"
        audit_policy.record_execution(success=False, error_message=error_msg)

        audit_policy.refresh_from_db()
        assert audit_policy.last_run is not None
        assert audit_policy.last_successful_run is None # No cambia
        assert audit_policy.consecutive_failures == initial_failures + 1
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1]['error_message'] == error_msg


# --- Tests for AuditConfiguration Model ---

class TestAuditConfigurationModel:

    def test_str_representation(self, audit_configuration):
        expected_str = f"{audit_configuration.name} ({'Active' if audit_configuration.is_active else 'Inactive'})"
        assert str(audit_configuration) == expected_str

    def test_is_active(self, audit_configuration):
        assert audit_configuration.is_active is True

        audit_configuration.is_active = False
        audit_configuration.save()
        assert audit_configuration.is_active is False

    def test_is_overdue(self, audit_configuration):
        # No debería estar vencido si no tiene next_run o no está activo
        assert not audit_configuration.is_overdue

        # Establecer un next_run en el pasado
        audit_configuration.next_run = timezone.now() - timedelta(minutes=1)
        audit_configuration.is_active = True
        audit_configuration.save()
        assert audit_configuration.is_overdue

        # Establecer un next_run en el futuro
        audit_configuration.next_run = timezone.now() + timedelta(minutes=1)
        audit_configuration.save()
        assert not audit_configuration.is_overdue

    def test_toggle_active(self, audit_configuration):
        audit_configuration.is_active = False
        audit_configuration.save()
        assert not audit_configuration.is_active

        audit_configuration.toggle_active()
        assert audit_configuration.is_active is True

        audit_configuration.toggle_active()
        assert audit_configuration.is_active is False

    def test_assign_to(self, audit_configuration, user):
        new_user = User.objects.create_user(username='assignee_config', email='assignee_config@example.com', password='pass')
        audit_configuration.assign_to(new_user, user) # user assigns to new_user
        audit_configuration.refresh_from_db()
        assert audit_configuration.assigned_to == new_user
        action = AuditAction.objects.filter(audit_configuration=audit_configuration, action_type=AuditActionType.ASSIGNED).first()
        assert action is not None
        assert f"Assigned to {new_user.get_full_name()}" in action.notes

    def test_total_layers(self, audit_configuration, spatial_layer):
        # Ya tiene una capa de la fixture
        assert audit_configuration.total_layers == 1
        # Añadir otra capa
        other_layer = SpatialLayer.objects.create(
            service=spatial_layer.service,
            layer_id=2,
            name='Other Layer',
            geometry_type='point',
            created_by=spatial_layer.created_by
        )
        audit_configuration.layers.add(other_layer)
        assert audit_configuration.total_layers == 2

    def test_total_services(self, audit_configuration, arcgis_service):
        # Ya tiene un servicio de la fixture
        assert audit_configuration.total_services == 1
        # Añadir otro servicio
        other_service = ArcGISService.objects.create(
            name='Other Service',
            base_url='https://otherservice.arcgis.com',
            service_type='featureserver',
            created_by=arcgis_service.created_by
        )
        audit_configuration.services.add(other_service)
        assert audit_configuration.total_services == 2

    def test_get_latest_snapshot(self, audit_configuration, spatial_layer):
        # Crear snapshots
        snapshot1 = LayerSnapshot.objects.create(
            layer=spatial_layer,
            snapshot_hash='snap1_config',
            feature_count=100,
            is_valid=True
        )
        snapshot2 = LayerSnapshot.objects.create(
            layer=spatial_layer,
            snapshot_hash='snap2_config',
            feature_count=150, # 50% increase
            is_valid=True
        )
        # Asegurar orden
        snapshot1.created = timezone.now() - timedelta(hours=2)
        snapshot1.save()
        snapshot2.created = timezone.now() - timedelta(hours=1)
        snapshot2.save()

        latest = audit_configuration.get_latest_snapshot()
        assert latest == snapshot2

    def test_get_snapshots_in_range(self, audit_configuration, spatial_layer):
        # Crear snapshots en diferentes momentos
        now = timezone.now()
        snapshot1 = LayerSnapshot.objects.create(
            layer=spatial_layer,
            snapshot_hash='snap1_range',
            feature_count=100,
            is_valid=True,
            created=now - timedelta(days=2)
        )
        snapshot2 = LayerSnapshot.objects.create(
            layer=spatial_layer,
            snapshot_hash='snap2_range',
            feature_count=150,
            is_valid=True,
            created=now - timedelta(days=1)
        )
        snapshot3 = LayerSnapshot.objects.create(
            layer=spatial_layer,
            snapshot_hash='snap3_range',
            feature_count=200,
            is_valid=True,
            created=now
        )

        # Obtener snapshots en rango
        start_date = now - timedelta(days=1.5)
        end_date = now - timedelta(hours=12)
        snapshots_in_range = audit_configuration.get_snapshots_in_range(start_date, end_date)

        assert snapshot2 in snapshots_in_range
        assert snapshot1 not in snapshots_in_range
        assert snapshot3 not in snapshots_in_range
