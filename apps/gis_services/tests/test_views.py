# apps/gis_services/tests/test_views.py
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.gis_services.models import ArcGISService, SpatialLayer, ServiceTag

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='testpass')

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

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

class TestArcGISServiceViewSet:

    def test_list_services_authenticated(self, authenticated_client, arcgis_service):
        url = reverse('service-list') # Asumiendo que el basename es 'service'
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1 # Puede haber otros servicios

    def test_list_services_unauthenticated(self, api_client):
        url = reverse('service-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_service_authenticated(self, authenticated_client, user, service_tag):
        url = reverse('service-list')
        data = {
            'name': 'New Test Service',
            'base_url': 'https://newtest.arcgis.com',
            'service_type': 'mapserver',
            'tag_ids': [service_tag.id]
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert ArcGISService.objects.filter(name='New Test Service').exists()
        service = ArcGISService.objects.get(name='New Test Service')
        assert service.created_by == user
        assert service_tag in service.tags.all()

    def test_retrieve_service(self, authenticated_client, arcgis_service):
        url = reverse('service-detail', kwargs={'pk': arcgis_service.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == arcgis_service.name

    def test_update_service(self, authenticated_client, arcgis_service):
        url = reverse('service-detail', kwargs={'pk': arcgis_service.id})
        data = {'name': 'Updated Test Service'}
        response = authenticated_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        arcgis_service.refresh_from_db()
        assert arcgis_service.name == 'Updated Test Service'

    def test_delete_service(self, authenticated_client, arcgis_service):
        url = reverse('service-detail', kwargs={'pk': arcgis_service.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Verificar que el servicio no fue eliminado físicamente, sino marcado como is_removed=True
        # (si se usa SoftDeletableModel)
        arcgis_service.refresh_from_db()
        assert arcgis_service.is_removed # Asumiendo que el modelo usa soft delete

    # Tests for custom actions like test_connection, sync_layers, health, metrics
    # would require mocking the ArcGISClient and Celery tasks.
    # Example for test_connection (requires mocking):
    # @patch('apps.gis_services.clients.arcgis_client.ArcGISClient')
    # def test_test_connection_action(self, mock_client_class, authenticated_client, arcgis_service):
    #     mock_client_instance = MagicMock()
    #     mock_client_instance.test_connection.return_value = (True, "Success")
    #     mock_client_instance.get_service_info.return_value = {'name': 'Mocked Service'}
    #     mock_client_class.return_value = mock_client_instance
    #
    #     url = reverse('service-test-connection', kwargs={'pk': arcgis_service.id})
    #     response = authenticated_client.post(url)
    #     assert response.status_code == status.HTTP_200_OK
    #     assert response.data['success'] is True
    #     # Check if update_status was called on the service
    #     arcgis_service.refresh_from_db()
    #     assert arcgis_service.status == 'active'


class TestSpatialLayerViewSet:

    def test_list_layers_authenticated(self, authenticated_client, spatial_layer):
        url = reverse('layer-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_list_layers_unauthenticated(self, api_client):
        url = reverse('layer-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_layer_authenticated(self, authenticated_client, arcgis_service):
        url = reverse('layer-list')
        data = {
            'service': arcgis_service.id,
            'layer_id': 999,
            'name': 'New Test Layer',
            'geometry_type': 'point',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert SpatialLayer.objects.filter(name='New Test Layer').exists()
        layer = SpatialLayer.objects.get(name='New Test Layer')
        assert layer.created_by == arcgis_service.created_by

    def test_retrieve_layer(self, authenticated_client, spatial_layer):
        url = reverse('layer-detail', kwargs={'pk': spatial_layer.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == spatial_layer.name

    # Tests for custom actions like monitor_now, feature_count, snapshots, toggle_monitoring, needs_attention
    # would also require mocking Celery tasks and potentially the ArcGISClient.

# Tests for ServiceTagViewSet and ServiceEndpointViewSet would follow similar patterns.
# Example for ServiceTagViewSet:
class TestServiceTagViewSet:

    def test_list_tags_authenticated(self, authenticated_client, service_tag):
        url = reverse('tag-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_create_tag_authenticated(self, authenticated_client):
        url = reverse('tag-list')
        data = {
            'name': 'New Test Tag',
            'color': '#0000FF',
            'description': 'A new tag'
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert ServiceTag.objects.filter(name='New Test Tag').exists()

    def test_create_tag_unauthenticated(self, api_client):
        url = reverse('tag-list')
        data = {
            'name': 'New Unauth Tag',
            'color': '#00FFFF',
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
