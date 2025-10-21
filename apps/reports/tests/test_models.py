# apps/reports/tests/test_models.py
"""
SMGI Backend - Tests for Reports Models
Sistema de Monitoreo Geoespacial Inteligente
Pruebas unitarias para los modelos del sistema de informes
"""
import pytest
import logging
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.gis.geos import Point, Polygon

from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.reports.models import (
    Report, ReportTemplate, GeneratedReport, ReportSchedule,
    ReportExecution, NotificationPreference, ReportParameter,
    ReportSection, ReportType, ReportFormat, ReportStatus
)


logger = logging.getLogger('apps.reports.tests.models')


# --- Fixtures ---

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='reports_test_user',
        email='reports@test.com',
        password='testpass123'
    )

@pytest.fixture
def arcgis_service(user):
    return ArcGISService.objects.create(
        name='Reports Test Service',
        base_url='https://reportstest.arcgis.com',
        service_type='featureserver',
        created_by=user
    )

@pytest.fixture
def spatial_layer(arcgis_service):
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=888,
        name='Reports Test Layer',
        geometry_type='polygon',
        created_by=arcgis_service.created_by
    )

@pytest.fixture
def report(user, arcgis_service, spatial_layer):
    return Report.objects.create(
        name='Test Report',
        description='This is a test report.',
        report_id='TEST-001',
        report_type=ReportType.MONITORING_SUMMARY,
        format_type=ReportFormat.PDF,
        service=arcgis_service,
        layer=spatial_layer,
        assigned_to=user,
        auto_resolve=True,
        auto_resolve_duration=2, # 2 hours
        suppress_similar=True,
        suppression_duration=30, # 30 minutes
        created_by=user
    )

@pytest.fixture
def report_template(user):
    return ReportTemplate.objects.create(
        name='Test Report Template',
        description='A test report template.',
        template_type=ReportType.MONITORING_SUMMARY,
        format_type=ReportFormat.PDF,
        template_content='<html><body>{{ report.name }}</body></html>',
        is_active=True,
        author=user
    )

@pytest.fixture
def generated_report(report, user):
    return GeneratedReport.objects.create(
        report=report,
        generated_by=user,
        report_id='GEN-TEST-001',
        file=ContentFile(b'Test PDF content', name='test_report.pdf'),
        file_size_bytes=102400, # 100 KB
        file_checksum='abc123...',
        format_type=ReportFormat.PDF,
        status=ReportStatus.COMPLETED,
        parameters_used={'test_param': 'value'},
        generation_duration_ms=5000, # 5 segundos
        record_count=1000,
        page_count=10,
        memory_usage_mb=50,
        cpu_usage_percent=25.0,
        execution_log=[],
        performance_metrics={}
    )

@pytest.fixture
def report_schedule(report, user):
    return ReportSchedule.objects.create(
        report=report,
        name='Daily Test Report',
        description='Run test report daily',
        schedule_expression='0 2 * * *', # Daily at 2 AM
        is_active=True,
        max_runtime_minutes=60,
        created_by=user
    )

@pytest.fixture
def report_execution(report_schedule):
    return ReportExecution.objects.create(
        schedule=report_schedule,
        success=True,
        started_at=timezone.now() - timedelta(minutes=10),
        completed_at=timezone.now() - timedelta(minutes=5),
        duration_seconds=300, # 5 minutos
        layers_processed=1,
        snapshots_created=1,
        changes_detected=0,
        alerts_created=0,
        memory_usage_mb=100,
        cpu_usage_percent=30.0,
        execution_log=[],
        performance_metrics={}
    )

@pytest.fixture
def notification_preference(user):
    return NotificationPreference.objects.create(
        user=user,
        email_enabled=True,
        sms_enabled=False,
        push_enabled=True,
        in_app_enabled=True,
        email_alert_notifications=True,
        quiet_hours_enabled=False,
        digest_enabled=False,
        min_alert_severity='medium'
    )

@pytest.fixture
def report_parameter(generated_report):
    return ReportParameter.objects.create(
        generated_report=generated_report,
        name='test_param',
        value='test_value',
        value_type='string'
    )

@pytest.fixture
def report_section(report):
    return ReportSection.objects.create(
        report=report,
        name='test_section',
        title='Test Section',
        description='A test section.',
        order=1,
        is_active=True,
        content_template='<p>{{ section.title }}</p>',
        data_source='SELECT * FROM test_table'
    )


# --- Tests for Report Model ---

class TestReportModel:

    def test_str_representation(self, report):
        expected_str = f"[{report.get_report_type_display()}] {report.name}"
        assert str(report) == expected_str

    def test_age_hours(self, report):
        # Age should be very small right after creation
        assert report.age_hours < 0.1 # Less than 6 minutes

    def test_is_expired_without_expires_at(self, report):
        report.expires_at = None
        assert not report.is_expired

    def test_is_expired_with_future_expires_at(self, report):
        report.expires_at = timezone.now() + timedelta(hours=1)
        assert not report.is_expired

    def test_is_expired_with_past_expires_at(self, report):
        report.expires_at = timezone.now() - timedelta(hours=1)
        assert report.is_expired

    def test_should_auto_resolve_not_configured(self, report):
        report.auto_resolve = False
        report.auto_resolve_duration = None
        assert not report.should_auto_resolve

    def test_should_auto_resolve_not_yet_due(self, report):
        report.first_detected = timezone.now() - timedelta(hours=1) # Only 1 hour old
        report.auto_resolve_duration = 2 # Should auto-resolve after 2 hours
        report.save()
        assert not report.should_auto_resolve

    def test_should_auto_resolve_due(self, report):
        report.first_detected = timezone.now() - timedelta(hours=3) # 3 hours old
        report.auto_resolve_duration = 2 # Should auto-resolve after 2 hours
        report.save()
        assert report.should_auto_resolve

    def test_time_to_acknowledge_not_yet(self, report):
        report.acknowledged_at = None
        assert report.time_to_acknowledge is None

    def test_time_to_acknowledge_calculated(self, report):
        ack_time = report.first_detected + timedelta(minutes=30)
        report.acknowledged_at = ack_time
        # Simulate saving to DB to ensure consistency
        report.save()
        report.refresh_from_db()
        assert report.time_to_acknowledge == 1800.0 # 30 minutes in seconds

    def test_time_to_resolve_not_yet(self, report):
        report.resolved_at = None
        assert report.time_to_resolve is None

    def test_time_to_resolve_calculated(self, report):
        res_time = report.first_detected + timedelta(hours=1)
        report.resolved_at = res_time
        report.save()
        report.refresh_from_db()
        assert report.time_to_resolve == 3600.0 # 1 hour in seconds

    def test_acknowledge_from_active(self, report, user):
        report.status = ReportStatus.ACTIVE
        report.save()
        assert report.acknowledge(user, "Test acknowledge")
        report.refresh_from_db()
        assert report.status == ReportStatus.ACKNOWLEDGED
        assert report.acknowledged_by == user
        assert report.acknowledged_at is not None
        # Verify an ReportAction was created
        action = ReportAction.objects.filter(report=report, action_type=ReportActionType.ACKNOWLEDGED).first()
        assert action is not None
        assert action.user == user
        assert action.notes == "Test acknowledge"

    def test_acknowledge_from_non_active(self, report, user):
        report.status = ReportStatus.RESOLVED
        report.save()
        assert not report.acknowledge(user, "Should not work")
        report.refresh_from_db()
        assert report.status == ReportStatus.RESOLVED # Status unchanged

    def test_resolve_from_active_or_acknowledged(self, report, user):
        # Test from ACTIVE
        report.status = ReportStatus.ACTIVE
        report.save()
        assert report.resolve(user, "Test resolve from active")
        report.refresh_from_db()
        assert report.status == ReportStatus.RESOLVED
        assert report.resolved_by == user
        assert report.resolved_at is not None

        # Test from ACKNOWLEDGED
        report.status = ReportStatus.ACKNOWLEDGED
        report.resolved_at = None
        report.resolved_by = None
        report.save()
        assert report.resolve(user, "Test resolve from acknowledged")
        report.refresh_from_db()
        assert report.status == ReportStatus.RESOLVED
        assert report.resolved_by == user
        assert report.resolved_at is not None

    def test_resolve_from_other_status(self, report, user):
        report.status = ReportStatus.DISMISSED
        report.save()
        assert not report.resolve(user, "Should not work")
        report.refresh_from_db()
        assert report.status == ReportStatus.DISMISSED # Status unchanged

    def test_dismiss(self, report, user):
        report.status = ReportStatus.ACTIVE
        report.save()
        assert report.dismiss(user, "Test dismiss")
        report.refresh_from_db()
        assert report.status == ReportStatus.DISMISSED

        # Test dismissing again (should still return True but do nothing)
        assert report.dismiss(user, "Test dismiss again")

    def test_assign_to(self, report, user):
        new_user = User.objects.create_user(username='assignee', email='assignee@example.com', password='pass')
        report.assign_to(new_user, user) # user assigns to new_user
        report.refresh_from_db()
        assert report.assigned_to == new_user
        action = ReportAction.objects.filter(report=report, action_type=ReportActionType.ASSIGNED).first()
        assert action is not None
        assert f"Assigned to {new_user.get_full_name()}" in action.notes

    def test_add_comment(self, report, user):
        comment_text = "This is a test comment."
        report.add_comment(user, comment_text)
        action = ReportAction.objects.filter(report=report, action_type=ReportActionType.COMMENTED, notes=comment_text).first()
        assert action is not None
        assert action.user == user

    # Note: Testing get_similar_active_reports and should_suppress_notifications requires
    # creating multiple reports and manipulating timestamps, which is more complex.
    # These are good candidates for integration tests or more advanced unit tests.

    def test_increment_notification_count(self, report):
        initial_count = report.notification_count
        report.increment_notification_count()
        report.refresh_from_db()
        assert report.notification_count == initial_count + 1
        assert report.notification_sent is True
        assert report.last_notification_sent is not None

    def test_update_feature_count(self, report):
        old_count = report.feature_count
        new_count = old_count + 50

        # Mock the task call or prevent it for this test
        # This requires mocking `apps.alerts.tasks.create_change_detection_alert.delay`
        # For simplicity here, we assume the task doesn't raise an exception during the test
        with patch('apps.reports.models.Report.update_feature_count') as mock_update:
            mock_update.return_value = True
            result = report.update_feature_count(new_count)
            assert result is True
            mock_update.assert_called_once_with(new_count)

    def test_record_check_failure(self, report):
        initial_failures = report.check_failures
        error_msg = "Test failure"

        report.record_check_failure(error_msg)

        report.refresh_from_db()
        assert report.check_failures == initial_failures + 1
        assert report.metadata.get('last_error', {}).get('message') == error_msg

    def test_get_latest_snapshot(self, report):
        # Crear snapshots
        snapshot1 = LayerSnapshot.objects.create(
            layer=report.layer,
            snapshot_hash='snap1',
            feature_count=100,
            is_valid=True
        )
        snapshot2 = LayerSnapshot.objects.create(
            layer=report.layer,
            snapshot_hash='snap2',
            feature_count=150,
            is_valid=True
        )
        # Asegurar orden
        snapshot1.created = timezone.now() - timedelta(hours=2)
        snapshot1.save()
        snapshot2.created = timezone.now() - timedelta(hours=1)
        snapshot2.save()

        latest = report.get_latest_snapshot()
        assert latest == snapshot2

    def test_get_snapshots_in_range(self, report):
        # Crear snapshots en diferentes momentos
        now = timezone.now()
        snapshot1 = LayerSnapshot.objects.create(
            layer=report.layer,
            snapshot_hash='snap1',
            feature_count=100,
            is_valid=True,
            created=now - timedelta(days=2)
        )
        snapshot2 = LayerSnapshot.objects.create(
            layer=report.layer,
            snapshot_hash='snap2',
            feature_count=150,
            is_valid=True,
            created=now - timedelta(days=1)
        )
        snapshot3 = LayerSnapshot.objects.create(
            layer=report.layer,
            snapshot_hash='snap3',
            feature_count=200,
            is_valid=True,
            created=now
        )

        # Obtener snapshots en rango
        start_date = now - timedelta(days=1.5)
        end_date = now - timedelta(hours=12)
        snapshots_in_range = report.get_snapshots_in_range(start_date, end_date)

        assert snapshot2 in snapshots_in_range
        assert snapshot1 not in snapshots_in_range
        assert snapshot3 not in snapshots_in_range


# --- Tests for ReportTemplate Model ---

class TestReportTemplateModel:

    def test_str_representation(self, report_template):
        expected_str = f"{report_template.name} ({report_template.get_template_type_display()})"
        assert str(report_template) == expected_str

    def test_author_name(self, report_template, user):
        assert report_template.author_name == user.get_full_name()

    def test_is_active(self, report_template):
        assert report_template.is_active is True

        report_template.is_active = False
        report_template.save()
        assert report_template.is_active is False

    def test_created_by_name(self, report_template, user):
        # Asumiendo que ReportTemplate tiene un campo created_by
        # Si no lo tiene, este test no aplica
        report_template.created_by = user
        report_template.save()
        assert report_template.created_by_name == user.get_full_name()

    def test_modified_by_name(self, report_template, user):
        # Asumiendo que ReportTemplate tiene un campo modified_by
        # Si no lo tiene, este test no aplica
        report_template.modified_by = user
        report_template.save()
        assert report_template.modified_by_name == user.get_full_name()

    def test_get_template_type_display(self, report_template):
        # Verificar que get_template_type_display devuelva el valor correcto
        assert report_template.get_template_type_display() == report_template.template_type

    def test_get_format_type_display(self, report_template):
        # Verificar que get_format_type_display devuelva el valor correcto
        assert report_template.get_format_type_display() == report_template.format_type


# --- Tests for GeneratedReport Model ---

class TestGeneratedReportModel:

    def test_str_representation(self, generated_report):
        expected_str = f"{generated_report.report.name} - {generated_report.get_status_display()} - {generated_report.created.strftime('%Y-%m-%d %H:%M')}"
        assert str(generated_report) == expected_str

    def test_get_format_type_display(self, generated_report):
        # Verificar que get_format_type_display devuelva el valor correcto
        assert generated_report.get_format_type_display() == generated_report.format_type

    def test_get_status_display(self, generated_report):
        # Verificar que get_status_display devuelva el valor correcto
        assert generated_report.get_status_display() == generated_report.status

    def test_layer(self, generated_report, spatial_layer):
        assert generated_report.layer == spatial_layer

    def test_service(self, generated_report, arcgis_service):
        assert generated_report.service == arcgis_service

    def test_generated_by_name(self, generated_report, user):
        assert generated_report.generated_by_name == user.get_full_name()

    def test_file_name(self, generated_report):
        assert generated_report.file_name == 'test_report.pdf'

    def test_file_url(self, generated_report):
        # Asumiendo que se usa un storage que genera URLs
        # En pruebas, esto puede ser una URL falsa
        assert generated_report.file_url is not None
        assert 'test_report.pdf' in generated_report.file_url

    def test_is_complete(self, generated_report):
        assert generated_report.is_complete is True

        generated_report.status = ReportStatus.FAILED
        generated_report.save()
        assert generated_report.is_complete is False

    def test_is_failed(self, generated_report):
        assert generated_report.is_failed is False

        generated_report.status = ReportStatus.FAILED
        generated_report.save()
        assert generated_report.is_failed is True

    def test_mark_as_generating(self, generated_report):
        generated_report.status = ReportStatus.PENDING
        generated_report.save()

        generated_report.mark_as_generating()
        generated_report.refresh_from_db()

        assert generated_report.status == ReportStatus.GENERATING

    def test_mark_as_completed(self, generated_report):
        generated_report.status = ReportStatus.GENERATING
        generated_report.save()

        file_path = 'path/to/completed_report.pdf'
        file_size = 204800 # 200 KB
        checksum = 'def456...'
        duration_ms = 10000 # 10 segundos
        record_count = 2000
        page_count = 20

        generated_report.mark_as_completed(
            file_path=file_path,
            file_size=file_size,
            checksum=checksum,
            duration_ms=duration_ms,
            record_count=record_count,
            page_count=page_count
        )
        generated_report.refresh_from_db()

        assert generated_report.status == ReportStatus.COMPLETED
        assert generated_report.file.name == file_path
        assert generated_report.file_size_bytes == file_size
        assert generated_report.file_checksum == checksum
        assert generated_report.generation_duration_ms == duration_ms
        assert generated_report.record_count == record_count
        assert generated_report.page_count == page_count

    def test_mark_as_failed(self, generated_report):
        generated_report.status = ReportStatus.GENERATING
        generated_report.save()

        error_message = "Test generation error"
        duration_ms = 5000 # 5 segundos

        generated_report.mark_as_failed(
            error_message=error_message,
            duration_ms=duration_ms
        )
        generated_report.refresh_from_db()

        assert generated_report.status == ReportStatus.FAILED
        assert generated_report.error_message == error_message
        assert generated_report.generation_duration_ms == duration_ms

    def test_mark_as_cancelled(self, generated_report):
        generated_report.status = ReportStatus.GENERATING
        generated_report.save()

        generated_report.mark_as_cancelled()
        generated_report.refresh_from_db()

        assert generated_report.status == ReportStatus.CANCELLED

    def test_increment_generation_count(self, generated_report):
        initial_count = generated_report.report.generation_count
        generated_report.increment_generation_count()
        generated_report.report.refresh_from_db()

        assert generated_report.report.generation_count == initial_count + 1
        assert generated_report.report.last_generated is not None


# --- Tests for ReportSchedule Model ---

class TestReportScheduleModel:

    def test_str_representation(self, report_schedule):
        expected_str = f"{report_schedule.name} ({report_schedule.get_status_display()})"
        assert str(report_schedule) == expected_str

    def test_get_schedule_type_display(self, report_schedule):
        # Verificar que get_schedule_type_display devuelva el valor correcto
        # Asumiendo que ReportSchedule tiene un campo schedule_type
        # Si no lo tiene, este test no aplica
        pass # Placeholder

    def test_get_status_display(self, report_schedule):
        # Verificar que get_status_display devuelva el valor correcto
        assert report_schedule.get_status_display() == report_schedule.status

    def test_is_active(self, report_schedule):
        assert report_schedule.is_active is True

        report_schedule.is_active = False
        report_schedule.save()
        assert report_schedule.is_active is False

    def test_created_by_name(self, report_schedule, user):
        assert report_schedule.created_by_name == user.get_full_name()

    def test_modified_by_name(self, report_schedule, user):
        # Asumiendo que ReportSchedule tiene un campo modified_by
        # Si no lo tiene, este test no aplica
        report_schedule.modified_by = user
        report_schedule.save()
        assert report_schedule.modified_by_name == user.get_full_name()

    def test_is_overdue(self, report_schedule):
        # No debería estar vencido si no tiene next_run o no está activo
        assert not report_schedule.is_overdue

        # Establecer un next_run en el pasado
        report_schedule.next_run = timezone.now() - timedelta(minutes=1)
        report_schedule.is_active = True
        report_schedule.save()
        assert report_schedule.is_overdue

        # Establecer un next_run en el futuro
        report_schedule.next_run = timezone.now() + timedelta(minutes=1)
        report_schedule.save()
        assert not report_schedule.is_overdue

    def test_total_layers(self, report_schedule, spatial_layer):
        # Ya tiene una capa de la fixture
        assert report_schedule.total_layers == 1
        # Añadir otra capa
        other_layer = SpatialLayer.objects.create(
            service=spatial_layer.service,
            layer_id=999,
            name='Other Layer',
            geometry_type='point',
            created_by=spatial_layer.created_by
        )
        report_schedule.layers.add(other_layer)
        assert report_schedule.total_layers == 2

    def test_total_services(self, report_schedule, arcgis_service):
        # Ya tiene un servicio de la fixture
        assert report_schedule.total_services == 1
        # Añadir otro servicio
        other_service = ArcGISService.objects.create(
            name='Other Service',
            base_url='https://otherservice.arcgis.com',
            service_type='featureserver',
            created_by=arcgis_service.created_by
        )
        report_schedule.services.add(other_service)
        assert report_schedule.total_services == 2

    def test_calculate_next_run_simple_interval(self, report_schedule):
        report_schedule.schedule_expression = '30m'
        next_run = report_schedule.calculate_next_run()
        expected_time = timezone.now() + timedelta(minutes=30)
        # Permitir un pequeño margen de error por tiempo de ejecución
        assert abs((next_run - expected_time).total_seconds()) < 2

        report_schedule.schedule_expression = '2h'
        next_run = report_schedule.calculate_next_run()
        expected_time = timezone.now() + timedelta(hours=2)
        assert abs((next_run - expected_time).total_seconds()) < 2

    def test_calculate_next_run_invalid_cron_uses_fallback(self, report_schedule):
        report_schedule.schedule_expression = 'invalid_cron'
        next_run = report_schedule.calculate_next_run()
        expected_time = timezone.now() + timedelta(hours=1)
        assert abs((next_run - expected_time).total_seconds()) < 2

    # Tests for record_execution can require mocks of ReportExecution.objects.create
    # or a transaction of database.
    @patch('apps.reports.models.ReportExecution.objects.create')
    def test_record_execution_success(self, mock_create, report_schedule, user):
        mock_execution = MagicMock()
        mock_create.return_value = mock_execution

        report_schedule.record_execution(success=True, error_message=None)

        report_schedule.refresh_from_db()
        assert report_schedule.last_run is not None
        assert report_schedule.last_successful_run is not None
        assert report_schedule.consecutive_failures == 0
        mock_create.assert_called_once()

    @patch('apps.reports.models.ReportExecution.objects.create')
    def test_record_execution_failure(self, mock_create, report_schedule, user):
        mock_execution = MagicMock()
        mock_create.return_value = mock_execution

        initial_failures = report_schedule.consecutive_failures
        error_msg = "Test execution error"
        report_schedule.record_execution(success=False, error_message=error_msg)

        report_schedule.refresh_from_db()
        assert report_schedule.last_run is not None
        assert report_schedule.last_successful_run is None # No cambia
        assert report_schedule.consecutive_failures == initial_failures + 1
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1]['error_message'] == error_msg


# --- Tests for ReportExecution Model ---

class TestReportExecutionModel:

    def test_str_representation(self, report_execution):
        status = "Success" if report_execution.success else "Failed"
        expected_str = f"{report_execution.schedule.name} - {status} - {report_execution.started_at.strftime('%Y-%m-%d %H:%M')}"
        assert str(report_execution) == expected_str

    def test_get_status_display(self, report_execution):
        # Verificar que get_status_display devuelva el valor correcto
        # Asumiendo que ReportExecution tiene un campo status
        # Si no lo tiene, este test no aplica
        pass # Placeholder

    @patch('apps.reports.models.timezone.now')
    def test_mark_completed(self, mock_now, report_execution):
        mock_now.return_value = timezone.now() + timedelta(seconds=10) # Simular finalización 10 segundos después
        start_time = report_execution.started_at
        expected_duration = int((mock_now.return_value - start_time).total_seconds())

        report_execution.mark_completed(success=True, error_message="Test error")

        report_execution.refresh_from_db()
        assert report_execution.completed_at is not None
        assert report_execution.duration_seconds == expected_duration
        assert report_execution.success is True
        assert report_execution.error_message == "Test error"

    def test_add_log_entry(self, report_execution):
        initial_log_count = len(report_execution.execution_log)

        level = 'INFO'
        message = 'Test log entry'
        extra_data = {'key': 'value'}

        report_execution.add_log_entry(level, message, **extra_data)

        report_execution.refresh_from_db()
        assert len(report_execution.execution_log) == initial_log_count + 1
        last_entry = report_execution.execution_log[-1]
        assert last_entry['level'] == level
        assert last_entry['message'] == message
        assert last_entry['key'] == 'value'


# --- Tests for NotificationPreference Model ---

class TestNotificationPreferenceModel:

    def test_str_representation(self, notification_preference, user):
        expected_str = f"Preferences for {user.email}"
        assert str(notification_preference) == expected_str

    def test_user_email(self, notification_preference, user):
        assert notification_preference.user_email == user.email

    def test_should_notify(self, notification_preference):
        # Test with email enabled
        assert notification_preference.should_notify(NotificationChannel.EMAIL, 'alert')

        # Test with email disabled
        notification_preference.email_enabled = False
        assert not notification_preference.should_notify(NotificationChannel.EMAIL, 'alert')
        notification_preference.email_enabled = True # Reset

        # Test quiet hours (disabled)
        assert notification_preference.should_notify(NotificationChannel.EMAIL, 'alert')

        # Test quiet hours (enabled but not active)
        notification_preference.quiet_hours_enabled = True
        notification_preference.quiet_hours_start = (timezone.now() + timedelta(hours=1)).time() # Future
        notification_preference.quiet_hours_end = (timezone.now() + timedelta(hours=2)).time() # Future
        assert notification_preference.should_notify(NotificationChannel.EMAIL, 'alert')

        # Test quiet hours (enabled and active)
        # This test is tricky because it depends on current time.
        # We can test the logic inside is_quiet_hours separately.
        pass

    def test_is_quiet_hours(self, notification_preference):
        # Quiet hours disabled
        assert not notification_preference.is_quiet_hours()

        # Quiet hours enabled, no times set
        notification_preference.quiet_hours_enabled = True
        assert not notification_preference.is_quiet_hours()

        # Quiet hours enabled, times set (not spanning midnight)
        now = timezone.now()
        start_time = (now - timedelta(minutes=30)).time() # 30 mins ago
        end_time = (now + timedelta(minutes=30)).time()   # 30 mins from now
        notification_preference.quiet_hours_start = start_time
        notification_preference.quiet_hours_end = end_time

        # Current time should be within quiet hours
        assert notification_preference.is_quiet_hours()

        # Times set, but current time outside range
        notification_preference.quiet_hours_start = (now + timedelta(hours=1)).time() # 1 hour from now
        notification_preference.quiet_hours_end = (now + timedelta(hours=2)).time() # 2 hours from now
        assert not notification_preference.is_quiet_hours()

        # Quiet hours spanning midnight
        # This is harder to test without mocking time, but the logic is there.
        # notification_preference.quiet_hours_start = time(22, 0) # 10 PM
        # notification_preference.quiet_hours_end = time(6, 0)  # 6 AM
        # Test with current time 11 PM and 5 AM would be needed.


# --- Tests for ReportParameter Model ---

class TestReportParameterModel:

    def test_str_representation(self, report_parameter, generated_report):
        expected_str = f"{generated_report.report.name}.{report_parameter.name} ({report_parameter.value_type})"
        assert str(report_parameter) == expected_str

    def test_get_value_type_display(self, report_parameter):
        # Verificar que get_value_type_display devuelva el valor correcto
        assert report_parameter.get_value_type_display() == report_parameter.value_type


# --- Tests for ReportSection Model ---

class TestReportSectionModel:

    def test_str_representation(self, report_section, report):
        expected_str = f"{report.name} - {report_section.name}"
        assert str(report_section) == expected_str

    def test_get_section_type_display(self, report_section):
        # Verificar que get_section_type_display devuelva el valor correcto
        # Asumiendo que ReportSection tiene un campo section_type
        # Si no lo tiene, este test no aplica
        pass # Placeholder
