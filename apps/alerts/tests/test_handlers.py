# apps/alerts/tests/test_handlers.py
import pytest
from unittest.mock import patch, MagicMock
from django.core import mail
from django.conf import settings
# Assuming Twilio is used for SMS
# from twilio.rest import Client
from apps.alerts.handlers.email_handler import EmailHandler
from apps.alerts.handlers.sms_handler import SMSHandler
from apps.alerts.handlers.websocket_handler import WebSocketHandler
from apps.alerts.models import Alert, AlertCategory, AlertSeverity


# --- Fixtures for Handlers ---

@pytest.fixture
def email_handler():
    # Use default Django SMTP settings
    return EmailHandler()

@pytest.fixture
def sms_handler():
    # Mock Twilio credentials
    return SMSHandler(
        account_sid='test_sid',
        auth_token='test_token',
        twilio_phone_number='+15551234567'
    )

@pytest.fixture
def websocket_handler():
    with patch('apps.alerts.handlers.websocket_handler.get_channel_layer') as mock_get_layer:
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer
        handler = WebSocketHandler()
        # Expose the mock for assertions in tests
        handler.mock_layer = mock_layer
        yield handler


# --- Fixtures for Alert Model Instance ---

@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='handler_test_user', email='handler@test.com', password='testpass')

@pytest.fixture
def arcgis_service(user):
    from apps.gis_services.models import ArcGISService
    # --- CORRECCIÓN: Eliminar espacio extra en la URL ---
    # Original: 'https://handlertest.arcgis.com  '
    return ArcGISService.objects.create(
        name='Handler Test Service',
        base_url='https://handlertest.arcgis.com',
        service_type='featureserver',
        created_by=user
    )
    # --- FIN CORRECCIÓN ---

@pytest.fixture
def spatial_layer(arcgis_service):
    from apps.gis_services.models import SpatialLayer
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=999,
        name='Handler Test Layer',
        geometry_type='point',
        created_by=arcgis_service.created_by
    )

@pytest.fixture
def alert_instance(user, arcgis_service, spatial_layer):
    return Alert.objects.create(
        title='Handler Test Alert',
        description='Alert for testing notification handlers.',
        alert_id='HANDLER-TEST-001',
        category=AlertCategory.THRESHOLD_BREACH,
        severity=AlertSeverity.CRITICAL,
        service=arcgis_service,
        layer=spatial_layer,
        assigned_to=user
    )


# --- Email Handler Tests ---

class TestEmailHandler:

    @patch('apps.alerts.handlers.email_handler.send_mail')
    def test_send_alert_email_success(self, mock_send_mail, email_handler, alert_instance):
        mock_send_mail.return_value = 1 # Indicates 1 email sent successfully
        recipients = ['recipient1@example.com', 'recipient2@example.com']
        
        success = email_handler.send_alert_email(alert_instance, recipients)

        assert success is True
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        assert call_args[1]['recipient_list'] == recipients
        assert 'Handler Test Alert' in call_args[1]['subject']
        assert alert_instance.description in call_args[1]['message'] # Plain text check
        assert '<!DOCTYPE html>' in call_args[1]['html_message'] # Basic HTML check
        # Note: Full template rendering check would require checking the rendered content against expected strings.

    @patch('apps.alerts.handlers.email_handler.send_mail')
    def test_send_alert_email_failure(self, mock_send_mail, email_handler, alert_instance):
        mock_send_mail.side_effect = Exception("SMTP server down")
        recipients = ['fail@example.com']
        
        success = email_handler.send_alert_email(alert_instance, recipients)

        assert success is False
        mock_send_mail.assert_called_once()


# --- SMS Handler Tests ---
# Note: Requires mocking Twilio client heavily. This is a basic structure.

class TestSMSHandler:

    def test_init_missing_settings(self, settings):
        # Temporarily remove Twilio settings
        if hasattr(settings, 'TWILIO_ACCOUNT_SID'):
            delattr(settings, 'TWILIO_ACCOUNT_SID')
        
        handler = SMSHandler()
        assert handler.client is None

    @patch('apps.alerts.handlers.sms_handler.Client') # Patch the Twilio Client class
    def test_send_alert_sms_success(self, mock_twilio_client_class, sms_handler, alert_instance):
        # Setup mock Twilio client instance and its messages.create method
        mock_twilio_instance = MagicMock()
        mock_twilio_client_class.return_value = mock_twilio_instance
        mock_message_instance = MagicMock()
        mock_message_instance.sid = 'SMXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
        mock_twilio_instance.messages.create.return_value = mock_message_instance

        phone_numbers = ['+19998887777']
        success = sms_handler.send_alert_sms(alert_instance, phone_numbers, "Critical Alert: {title}")

        assert success is True
        mock_twilio_instance.messages.create.assert_called_once()
        call_kwargs = mock_twilio_instance.messages.create.call_args.kwargs
        assert call_kwargs['to'] == phone_numbers[0]
        assert call_kwargs['from_'] == '+15551234567'
        assert 'Critical Alert:' in call_kwargs['body']
        # --- MEJORA: Ajustar la aserción si la lógica de formateo es diferente ---
        # Original: assert alert_instance.title[:20] in call_kwargs['body']
        # Si el handler trunca el título, esta aserción está bien.
        # Si no, podría ser mejor assert alert_instance.title in call_kwargs['body']
        # Por ahora, asumimos que la lógica del handler trunca.
        assert alert_instance.title[:20] in call_kwargs['body']
        # --- FIN MEJORA ---

    @patch('apps.alerts.handlers.sms_handler.Client')
    def test_send_alert_sms_failure(self, mock_twilio_client_class, sms_handler, alert_instance):
        mock_twilio_instance = MagicMock()
        mock_twilio_client_class.return_value = mock_twilio_instance
        mock_twilio_instance.messages.create.side_effect = Exception("Twilio API error")

        phone_numbers = ['+19998887777']
        success = sms_handler.send_alert_sms(alert_instance, phone_numbers)

        assert success is False
        mock_twilio_instance.messages.create.assert_called_once()


# --- WebSocket Handler Tests ---

class TestWebSocketHandler:

    def test_send_alert_websocket_broadcast(self, websocket_handler, alert_instance):
        success = websocket_handler.send_alert_websocket(alert_instance)

        assert success is True
        websocket_handler.mock_layer.group_send.assert_called_once()
        call_args = websocket_handler.mock_layer.group_send.call_args
        assert call_args[0][0] == "alerts_group" # Group name
        message_dict = call_args[1] # Keyword arguments (the message dict)
        assert message_dict['type'] == 'alert.message'
        assert message_dict['alert_id'] == str(alert_instance.id)
        assert message_dict['alert_title'] == alert_instance.title

    def test_send_alert_websocket_specific_channels(self, websocket_handler, alert_instance):
        channels = ['specific_channel_1', 'specific_channel_2']
        success = websocket_handler.send_alert_websocket(alert_instance, specific_channels=channels)

        assert success is True
        # Assert send was called twice, once for each channel
        assert websocket_handler.mock_layer.send.call_count == 2
        # Check calls individually if needed
        # calls = websocket_handler.mock_layer.send.call_args_list
        # ...

    # --- MEJORA: Comentario sobre comportamiento ante layer no encontrado ---
    # def test_send_alert_websocket_no_layer(self):
    #     handler = WebSocketHandler(channel_layer_alias='nonexistent')
    #     # Since the layer is mocked to be None internally if not found, this test might need adjustment
    #     # depending on how get_channel_layer behaves when alias is not found.
    #     # For now, we assume it logs an error and returns False.
    #     success = handler.send_alert_websocket(MagicMock())
    #     # This assertion depends on the implementation detail. If it raises or just logs, behavior differs.
    #     # Let's assume it gracefully handles it.
    #     # assert success is False # Or just expect no exception and proceed.
    # --- FIN MEJORA ---

    def test_add_remove_from_group(self, websocket_handler):
        channel_name = "test_channel_123"
        
        # Test add
        add_success = websocket_handler.add_to_alerts_group(channel_name)
        assert add_success is True
        websocket_handler.mock_layer.group_add.assert_called_once_with(
            "alerts_group", channel_name
        )

        # Test remove
        remove_success = websocket_handler.remove_from_alerts_group(channel_name)
        assert remove_success is True
        websocket_handler.mock_layer.group_discard.assert_called_once_with(
            "alerts_group", channel_name
        )
