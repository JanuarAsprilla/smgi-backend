# apps/alerts/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.alerts.models import Alert, AlertAction, AlertStatus, AlertSeverity, AlertCategory, AlertActionType

User = get_user_model()

@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', email='test@example.com', password='testpass')

@pytest.fixture
def arcgis_service(user):
    return ArcGISService.objects.create(
        name='Test Service',
        base_url='https://test.arcgis.com',
        service_type='featureserver',
        created_by=user
    )

@pytest.fixture
def spatial_layer(arcgis_service):
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=1,
        name='Test Layer',
        geometry_type='polygon',
        created_by=arcgis_service.created_by
    )

@pytest.fixture
def alert(user, arcgis_service, spatial_layer):
    return Alert.objects.create(
        title='Test Alert',
        description='This is a test alert.',
        alert_id='TEST-001',
        category=AlertCategory.CHANGE_DETECTION,
        severity=AlertSeverity.HIGH,
        service=arcgis_service,
        layer=spatial_layer,
        assigned_to=user,
        auto_resolve=True,
        auto_resolve_duration=2, # 2 hours
        suppress_similar=True,
        suppression_duration=30 # 30 minutes
    )

@pytest.fixture
def alert_action(alert, user):
    return AlertAction.objects.create(
        alert=alert,
        action_type=AlertActionType.CREATED,
        user=user,
        notes='Initial alert creation'
    )


class TestAlertModel:

    def test_str_representation(self, alert):
        expected_str = f"[{alert.get_severity_display()}] {alert.title}"
        assert str(alert) == expected_str

    def test_age_hours(self, alert):
        # Age should be very small right after creation
        assert alert.age_hours < 0.1 # Less than 6 minutes

    def test_is_expired_without_expires_at(self, alert):
        alert.expires_at = None
        assert not alert.is_expired

    def test_is_expired_with_future_expires_at(self, alert):
        alert.expires_at = timezone.now() + timedelta(hours=1)
        assert not alert.is_expired

    def test_is_expired_with_past_expires_at(self, alert):
        alert.expires_at = timezone.now() - timedelta(hours=1)
        assert alert.is_expired

    def test_should_auto_resolve_not_configured(self, alert):
        alert.auto_resolve = False
        alert.auto_resolve_duration = None
        assert not alert.should_auto_resolve

    def test_should_auto_resolve_not_yet_due(self, alert):
        alert.first_detected = timezone.now() - timedelta(hours=1) # Only 1 hour old
        alert.auto_resolve_duration = 2 # Should auto-resolve after 2 hours
        alert.save()
        assert not alert.should_auto_resolve

    def test_should_auto_resolve_due(self, alert):
        alert.first_detected = timezone.now() - timedelta(hours=3) # 3 hours old
        alert.auto_resolve_duration = 2 # Should auto-resolve after 2 hours
        alert.save()
        assert alert.should_auto_resolve

    def test_time_to_acknowledge_not_yet(self, alert):
        alert.acknowledged_at = None
        assert alert.time_to_acknowledge is None

    def test_time_to_acknowledge_calculated(self, alert):
        ack_time = alert.first_detected + timedelta(minutes=30)
        alert.acknowledged_at = ack_time
        # Simulate saving to DB to ensure consistency
        alert.save()
        alert.refresh_from_db()
        assert alert.time_to_acknowledge == 1800.0 # 30 minutes in seconds

    def test_time_to_resolve_not_yet(self, alert):
        alert.resolved_at = None
        assert alert.time_to_resolve is None

    def test_time_to_resolve_calculated(self, alert):
        res_time = alert.first_detected + timedelta(hours=1)
        alert.resolved_at = res_time
        alert.save()
        alert.refresh_from_db()
        assert alert.time_to_resolve == 3600.0 # 1 hour in seconds

    def test_acknowledge_from_active(self, alert, user):
        alert.status = AlertStatus.ACTIVE
        alert.save()
        assert alert.acknowledge(user, "Test acknowledge")
        alert.refresh_from_db()
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == user
        assert alert.acknowledged_at is not None
        # Verify an AlertAction was created
        action = AlertAction.objects.filter(alert=alert, action_type=AlertActionType.ACKNOWLEDGED).first()
        assert action is not None
        assert action.user == user
        assert action.notes == "Test acknowledge"

    def test_acknowledge_from_non_active(self, alert, user):
        alert.status = AlertStatus.RESOLVED
        alert.save()
        assert not alert.acknowledge(user, "Should not work")
        alert.refresh_from_db()
        assert alert.status == AlertStatus.RESOLVED # Status unchanged

    def test_resolve_from_active_or_acknowledged(self, alert, user):
        # Test from ACTIVE
        alert.status = AlertStatus.ACTIVE
        alert.save()
        assert alert.resolve(user, "Test resolve from active")
        alert.refresh_from_db()
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_by == user
        assert alert.resolved_at is not None

        # Test from ACKNOWLEDGED
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.resolved_at = None
        alert.resolved_by = None
        alert.save()
        assert alert.resolve(user, "Test resolve from acknowledged")
        alert.refresh_from_db()
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_by == user
        assert alert.resolved_at is not None

    def test_resolve_from_other_status(self, alert, user):
        alert.status = AlertStatus.DISMISSED
        alert.save()
        assert not alert.resolve(user, "Should not work")
        alert.refresh_from_db()
        assert alert.status == AlertStatus.DISMISSED # Status unchanged

    def test_dismiss(self, alert, user):
        alert.status = AlertStatus.ACTIVE
        alert.save()
        assert alert.dismiss(user, "Test dismiss")
        alert.refresh_from_db()
        assert alert.status == AlertStatus.DISMISSED

        # Test dismissing again (should still return True but do nothing)
        assert alert.dismiss(user, "Test dismiss again")

    def test_assign_to(self, alert, user):
        new_user = User.objects.create_user(username='assignee', email='assignee@example.com', password='pass')
        alert.assign_to(new_user, user) # user assigns to new_user
        alert.refresh_from_db()
        assert alert.assigned_to == new_user
        action = AlertAction.objects.filter(alert=alert, action_type=AlertActionType.ASSIGNED).first()
        assert action is not None
        assert f"Assigned to {new_user.get_full_name()}" in action.notes

    def test_add_comment(self, alert, user):
        comment_text = "This is a test comment."
        alert.add_comment(user, comment_text)
        action = AlertAction.objects.filter(alert=alert, action_type=AlertActionType.COMMENTED, notes=comment_text).first()
        assert action is not None
        assert action.user == user

    # Note: Testing get_similar_active_alerts and should_suppress_notifications requires
    # creating multiple alerts and manipulating timestamps, which is more complex.
    # These are good candidates for integration tests or more advanced unit tests.

    def test_increment_notification_count(self, alert):
        initial_count = alert.notification_count
        alert.increment_notification_count()
        alert.refresh_from_db()
        assert alert.notification_count == initial_count + 1
        assert alert.notification_sent is True
        assert alert.last_notification_sent is not None


class TestAlertActionModel:

    def test_str_representation(self, alert_action):
        expected_str = f"{alert_action.get_action_type_display()} - {alert_action.alert.title}"
        assert str(alert_action) == expected_str

    # Additional tests for AlertAction fields, relationships, etc. can be added here.
    # For example, testing that user can be None, notes can be blank, etc.
