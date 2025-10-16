# apps/gis_services/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.gis_services.models import (
    ArcGISService, SpatialLayer, ServiceTag, ServiceCredential, ServiceConfiguration
)

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='testpass')

@pytest.fixture
def service_tag():
    return ServiceTag.objects.create(name='TestTag', color='#FF0000', description='A test tag')

@pytest.fixture
def arcgis_service(user, service_tag):
    service = ArcGISService.objects.create(
        name='Test Service',
        base_url='https://test.arcgis.com',
        service_type='featureserver',
        created_by=user
    )
    service.tags.add(service_tag)
    return service

@pytest.fixture
def spatial_layer(arcgis_service):
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=1,
        name='Test Layer',
        geometry_type='polygon',
        created_by=arcgis_service.created_by
    )

class TestArcGISServiceModel:

    def test_str_representation(self, arcgis_service):
        assert str(arcgis_service) == f"{arcgis_service.name} ({arcgis_service.service_type})"

    def test_full_name_property(self, spatial_layer):
        expected = f"{spatial_layer.service.name}/{spatial_layer.name}"
        assert spatial_layer.full_name == expected

    def test_is_online_property(self, arcgis_service):
        arcgis_service.status = 'active'
        assert arcgis_service.is_online

        arcgis_service.status = 'error'
        assert not arcgis_service.is_online

    def test_update_status(self, arcgis_service):
        initial_failures = arcgis_service.consecutive_failures
        error_msg = "Test error"
        arcgis_service.update_status('error', error_msg)

        arcgis_service.refresh_from_db()
        assert arcgis_service.status == 'error'
        assert arcgis_service.consecutive_failures == initial_failures + 1
        assert arcgis_service.metadata.get('last_error', {}).get('message') == error_msg

    def test_needs_token_refresh(self, arcgis_service):
        # No expiry set
        assert not arcgis_service.needs_token_refresh

        # Expiry in the past
        arcgis_service.token_expires = timezone.now() - timezone.timedelta(minutes=5)
        assert arcgis_service.needs_token_refresh

        # Expiry in the future
        arcgis_service.token_expires = timezone.now() + timezone.timedelta(hours=1)
        assert not arcgis_service.needs_token_refresh

    def test_get_layers(self, arcgis_service, spatial_layer):
        layers = arcgis_service.get_layers()
        assert spatial_layer in layers

    def test_get_monitored_layers(self, arcgis_service, spatial_layer):
        # Initially not monitored
        monitored_layers = arcgis_service.get_monitored_layers()
        assert spatial_layer not in monitored_layers

        # Enable monitoring
        spatial_layer.is_monitored = True
        spatial_layer.save()
        monitored_layers = arcgis_service.get_monitored_layers()
        assert spatial_layer in monitored_layers

class TestSpatialLayerModel:

    def test_str_representation(self, spatial_layer):
        expected = f"{spatial_layer.service.name} - {spatial_layer.name} (ID: {spatial_layer.layer_id})"
        assert str(spatial_layer) == expected

    def test_should_be_monitored(self, spatial_layer):
        # All conditions met
        spatial_layer.is_monitored = True
        spatial_layer.monitoring_enabled = True
        spatial_layer.service.is_monitored = True
        spatial_layer.service.status = 'active'
        assert spatial_layer.should_be_monitored

        # One condition fails (service not active)
        spatial_layer.service.status = 'error'
        assert not spatial_layer.should_be_monitored

        # One condition fails (layer not monitored)
        spatial_layer.service.status = 'active'
        spatial_layer.is_monitored = False
        assert not spatial_layer.should_be_monitored

    def test_change_percentage(self, spatial_layer):
        spatial_layer.last_feature_count = 100
        spatial_layer.feature_count = 120
        assert spatial_layer.change_percentage == 20.0

        spatial_layer.last_feature_count = 0
        spatial_layer.feature_count = 50
        assert spatial_layer.change_percentage == 100.0 # (50-0)/0 -> 100%

        spatial_layer.last_feature_count = 50
        spatial_layer.feature_count = 0
        assert spatial_layer.change_percentage == 100.0 # (0-50)/50 -> 100%

    def test_has_significant_change(self, spatial_layer):
        spatial_layer.last_feature_count = 100
        spatial_layer.feature_count = 110 # 10% change
        spatial_layer.change_threshold = 0.05 # 5%
        assert spatial_layer.has_significant_change

        spatial_layer.change_threshold = 0.15 # 15%
        assert not spatial_layer.has_significant_change

    def test_update_feature_count(self, spatial_layer):
        old_count = spatial_layer.feature_count
        new_count = old_count + 50

        # Mock the task call or prevent it for this test
        # This requires mocking `apps.alerts.tasks.create_change_detection_alert.delay`
        # For simplicity here, we assume the task doesn't raise an exception during the test
        spatial_layer.update_feature_count(new_count)

        spatial_layer.refresh_from_db()
        assert spatial_layer.last_feature_count == old_count
        assert spatial_layer.feature_count == new_count
        assert spatial_layer.check_failures == 0 # Should reset on success

    def test_record_check_failure(self, spatial_layer):
        initial_failures = spatial_layer.check_failures
        error_msg = "Test failure"

        spatial_layer.record_check_failure(error_msg)

        spatial_layer.refresh_from_db()
        assert spatial_layer.check_failures == initial_failures + 1
        assert spatial_layer.metadata.get('last_error', {}).get('message') == error_msg

    # Tests for get_latest_snapshot and get_snapshots_in_range would require
    # the monitoring app and LayerSnapshot model to be set up in the test DB
    # and are typically integration tests.

class TestServiceTagModel:

    def test_str_representation(self, service_tag):
        assert str(service_tag) == service_tag.name

    def test_unique_name(self):
        ServiceTag.objects.create(name='UniqueTag', color='#00FF00')
        with pytest.raises(Exception): # Should raise IntegrityError
            ServiceTag.objects.create(name='UniqueTag', color='#0000FF')

# Tests for ServiceCredential and ServiceConfiguration would follow similar patterns
# checking their specific fields and relationships.
