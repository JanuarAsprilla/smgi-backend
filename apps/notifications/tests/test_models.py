# apps/notifications/tests/test_channels.py
"""
SMGI Backend - Tests for Notification Channels
Sistema de Monitoreo Geoespacial Inteligente
"""
import pytest
from unittest.mock import patch, MagicMock
from apps.notifications.channels.base_channel import BaseNotificationChannel, NotificationChannelError
from apps.notifications.channels.email_channel import EmailNotificationChannel
# from apps.notifications.channels.push_channel import PushNotificationChannel
# from apps.notifications.channels.websocket_channel import WebsocketNotificationChannel


class TestBaseNotificationChannel:

    def test_abstract_send_raises(self):
        """Test that the abstract send method raises NotImplementedError."""
        class ConcreteChannel(BaseNotificationChannel):
            def __init__(self):
                super().__init__("Test", "A test channel")

        channel = ConcreteChannel()
        with pytest.raises(NotImplementedError):
            channel.send({})

    def test_validate_data(self):
        """Test the default validate_data method."""
        class ConcreteChannel(BaseNotificationChannel):
            def __init__(self):
                super().__init__("Test", "A test channel")

            def send(self, data):
                pass # Dummy implementation

        channel = ConcreteChannel()
        # Valid data
        valid_data = {'recipient': 'test@example.com', 'title': 'Test', 'message': 'Hello'}
        channel.validate_data(valid_data) # Should not raise

        # Invalid data types
        with pytest.raises(NotificationChannelError):
            channel.validate_data("not a dict")

        # Missing required key
        with pytest.raises(NotificationChannelError):
            channel.validate_data({'title': 'Test', 'message': 'Hello'}) # Missing 'recipient'

    def test_format_message(self):
        """Test the format_message method."""
        class ConcreteChannel(BaseNotificationChannel):
            def __init__(self):
                super().__init__("Test", "A test channel")

            def send(self, data):
                pass

        channel = ConcreteChannel()
        message = "Hello {name}!"
        context = {'name': 'Alice'}
        formatted = channel.format_message(message, context)
        assert formatted == "Hello Alice!"

        # Test with no context
        formatted_no_ctx = channel.format_message(message, None)
        assert formatted_no_ctx == message

        # Test with missing key (should return original message)
        bad_context = {'other_key': 'value'}
        formatted_bad_ctx = channel.format_message(message, bad_context)
        assert formatted_bad_ctx == message # Or original message if error occurs

    def test_get_channel_identifier(self):
        """Test the default get_channel_identifier method."""
        class ConcreteChannel(BaseNotificationChannel):
            def __init__(self):
                super().__init__("Test", "A test channel")

            def send(self, data):
                pass

        channel = ConcreteChannel()
        data = {'recipient': 'test@example.com', 'title': 'Test'}
        identifier = channel.get_channel_identifier(data)
        assert identifier == 'test@example.com'


class TestEmailNotificationChannel:

    @patch('apps.notifications.channels.email_channel.EmailMultiAlternatives')
    def test_send_success(self, mock_email_class):
        """Test successful email sending."""
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        channel = EmailNotificationChannel()
        data = {
            'recipient': 'recipient@example.com',
            'title': 'Test Subject',
            'message': 'Test body text',
            'html_message': '<p>Test body HTML</p>',
            'from_email': 'sender@example.com',
            'cc': ['cc@example.com'],
            'bcc': ['bcc@example.com'],
            # 'attachments': [{'filename': 'test.txt', 'content': b'test', 'mimetype': 'text/plain'}],
            'context': {},
            'template_name': None,
            'user_id': 1,
            'alert_id': 1
        }

        result = channel.send(data)

        assert result['success'] is True
        assert result['recipient'] == 'recipient@example.com'
        mock_email_class.assert_called_once_with(
            subject='Test Subject',
            body='Test body text',
            from_email='sender@example.com',
            to=['recipient@example.com'],
            cc=['cc@example.com'],
            bcc=['bcc@example.com']
        )
        mock_email_instance.attach_alternative.assert_called_once_with('<p>Test body HTML</p>', 'text/html')
        # mock_email_instance.attach.assert_called_once() # If attachments were tested
        mock_email_instance.send.assert_called_once_with(fail_silently=False)

    def test_send_inactive_channel(self):
        """Test sending with inactive channel."""
        channel = EmailNotificationChannel(is_active=False)
        data = {'recipient': 'test@example.com', 'title': 'Test', 'message': 'Hello'}
        result = channel.send(data)
        assert result['success'] is False
        assert result['error'] == 'Channel_inactive'

    def test_send_missing_recipient(self):
        """Test sending with missing recipient."""
        channel = EmailNotificationChannel()
        data = {'title': 'Test', 'message': 'Hello'} # Missing 'recipient'
        with pytest.raises(Exception): # Or a more specific exception from validate_data
             channel.send(data)

    @patch('apps.notifications.channels.email_channel.EmailMultiAlternatives')
    def test_send_with_persistence(self, mock_email_class):
        """Test that EmailNotification object is created and updated."""
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        # Mock the EmailNotification model
        with patch('apps.notifications.channels.email_channel.EmailNotification') as mock_email_notif_model:
            mock_email_notif_instance = MagicMock()
            mock_email_notif_model.objects.create.return_value = mock_email_notif_instance

            channel = EmailNotificationChannel()
            user_id = 1
            alert_id = 1
            data = {
                'recipient': 'test@example.com',
                'title': 'Test Subject',
                'message': 'Test body',
                'user_id': user_id,
                'alert_id': alert_id
            }

            result = channel.send(data)

            assert result['success'] is True
            # Check if EmailNotification.objects.create was called
            mock_email_notif_model.objects.create.assert_called_once()
            call_kwargs = mock_email_notif_model.objects.create.call_args.kwargs
            assert call_kwargs['recipient_email'] == 'test@example.com'
            assert call_kwargs['subject'] == 'Test Subject'
            assert call_kwargs['user_id'] == user_id
            assert call_kwargs['alert_id'] == alert_id

            # Check if mark_sent was called on the instance
            mock_email_notif_instance.mark_sent.assert_called_once()

    # Tests for PushNotificationChannel and WebsocketNotificationChannel
    # would follow a similar pattern, mocking the respective libraries
    # (firebase_admin for Push, channels for Websocket) and testing
    # the send logic, validation, and interactions with models.

    # Example skeleton for PushNotificationChannel test:
    # class TestPushNotificationChannel:
    #     @patch('apps.notifications.channels.push_channel.firebase_admin.messaging') # If using FCM
    #     def test_send_success(self, mock_messaging):
    #         mock_response = MagicMock()
    #         mock_response.success = True
    #         mock_response.message_id = 'test-message-id'
    #         mock_messaging.send.return_value = mock_response
    #
    #         channel = PushNotificationChannel()
    #         data = {
    #             'recipient': 'device-token-123',
    #             'title': 'Test Push',
    #             'message': 'Hello via push!'
    #         }
    #
    #         result = channel.send(data)
    #
    #         assert result['success'] is True
    #         assert result['recipient'] == 'device-token-123'
    #         assert result['channel_message_id'] == 'test-message-id'
    #         mock_messaging.send.assert_called_once()
