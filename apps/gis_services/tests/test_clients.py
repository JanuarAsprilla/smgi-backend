# apps/gis_services/tests/test_clients.py
import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException
from apps.gis_services.clients.arcgis_client import ArcGISClient, ArcGISClientError, ArcGISAuthenticationError, ArcGISConnectionError
from apps.gis_services.clients.base_client import BaseGISClient
from apps.gis_services.models import ArcGISService, ServiceCredential, ServiceConfiguration

# --- Tests para BaseGISClient ---
# BaseGISClient es abstracto, por lo que probamos sus métodos comunes
# y que no se pueda instanciar directamente.

def test_base_client_abstract_instantiation():
    with pytest.raises(TypeError):
        BaseGISClient(service=MagicMock())

# No podemos probar directamente _get_config_value o _get_cache_key
# sin instanciar una subclase. Se probarían indirectamente a través de ArcGISClient.

# --- Tests para ArcGISClient ---

@pytest.fixture
def mock_service():
    service = MagicMock(spec=ArcGISService)
    service.base_url = 'https://test.arcgis.com'
    service.timeout_seconds = 30
    service.requires_authentication = False
    service.token = None
    service.needs_token_refresh = False
    service.id = 1
    # Mock de la relación OneToOne con ServiceConfiguration
    service.configuration = None
    return service

@pytest.fixture
def mock_service_with_config(mock_service):
    config = MagicMock(spec=ServiceConfiguration)
    config.max_retries = 5
    config.retry_delay = 2
    config.backoff_factor = 3.0
    config.cache_duration = 600
    config.headers = {'Custom-Header': 'Test'}
    config.query_parameters = {'custom_param': 'value'}
    mock_service.configuration = config
    return mock_service

@pytest.fixture
def arcgis_client(mock_service):
    return ArcGISClient(service=mock_service)

class TestArcGISClientInstantiation:

    def test_initialization_with_service(self, mock_service):
        client = ArcGISClient(service=mock_service)
        assert client.service == mock_service
        assert client.base_url == mock_service.base_url
        assert client.timeout == mock_service.timeout_seconds

    def test_initialization_with_custom_timeout(self, mock_service):
        client = ArcGISClient(service=mock_service, timeout=60)
        assert client.timeout == 60

    def test_initialization_with_config(self, mock_service_with_config):
        client = ArcGISClient(service=mock_service_with_config)
        # La sesión se crea en _create_session, que usa la config
        # Podríamos verificar que los valores se pasan correctamente allí
        # Por ahora, asumimos que _create_session maneja la config correctamente
        # basado en el código revisado previamente.
        assert client.service_config == mock_service_with_config.configuration

class TestArcGISClientMakeRequest:

    @patch('apps.gis_services.clients.arcgis_client.requests.Session')
    def test_make_request_success_get(self, mock_session_class, arcgis_client):
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': 'success'}
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        result = arcgis_client._make_request('GET', 'https://test.arcgis.com/rest/info')

        assert result == {'result': 'success'}
        mock_session_instance.get.assert_called_once()

    @patch('apps.gis_services.clients.arcgis_client.requests.Session')
    def test_make_request_connection_error(self, mock_session_class, arcgis_client):
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = RequestException("Connection failed")
        mock_session_class.return_value = mock_session_instance

        with pytest.raises(ArcGISConnectionError):
            arcgis_client._make_request('GET', 'https://test.arcgis.com/rest/info')

    @patch('apps.gis_services.clients.arcgis_client.requests.Session')
    def test_make_request_arcgis_error(self, mock_session_class, arcgis_client):
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200 # Status HTTP OK
        mock_response.json.return_value = {'error': {'code': 400, 'message': 'Bad Request'}}
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        with pytest.raises(ArcGISClientError):
            arcgis_client._make_request('GET', 'https://test.arcgis.com/rest/info')

    # Test para _authenticate, test_connection, etc., requieren
    # mocks más complejos de ServiceCredential, ArcGIS API responses, etc.
    # y probablemente sean más adecuados como pruebas de integración
    # o pruebas unitarias con fixtures de respuesta simuladas.

# --- Tests para GeoServerClient (si se implementa) ---
# Se seguiría un patrón similar, probando sus métodos específicos
# y asegurando que hereda correctamente de BaseGISClient.
# Dado que nuestra implementación de GeoServerClient es esquelética,
# los tests serían principalmente para verificar la estructura
# y la integración con la base, no la lógica de negocio completa de GeoServer.
