# apps/notifications/tests/test_tasks.py
"""
SMGI Backend - Tests for Notification Tasks
Sistema de Monitoreo Geoespacial Inteligente
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from apps.notifications.tasks import (
    send_email_notification, cleanup_old_notifications,
    retry_failed_emails # , send_alert_email, send_webhook_notification, etc.
)
from apps.notifications.models import EmailNotification, Notification


@pytest.fixture
def email_notification(db):
    return EmailNotification.objects.create(
        subject='Test Email',
        body_text='This is a test email body.',
        recipient_email='test@example.com',
        status='pending',
        priority='normal'
    )


class TestSendEmailNotificationTask:

    @patch('apps.notifications.tasks.EmailMultiAlternatives')
    def test_send_email_success(self, mock_email_class, email_notification):
        """Test successful email sending task."""
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance

        # Call the task
        result = send_email_notification(email_notification.id)

        # Assertions
        assert result['success'] is True
        assert result['email_id'] == str(email_notification.id)
        assert result['recipient'] == 'test@example.com'

        mock_email_class.assert_called_once()
        mock_email_instance.send.assert_called_once_with(fail_silently=False)

        # Check that the email object was updated
        email_notification.refresh_from_db()
        assert email_notification.status == 'sent'
        assert email_notification.sent_at is not None

    def test_send_email_not_found(self):
        """Test task with non-existent email notification ID."""
        fake_id = '00000000-0000-0000-0000-000000000000'
        result = send_email_notification(fake_id)
        assert result['success'] is False
        assert 'not found' in result['error']

    @patch('apps.notifications.tasks.EmailMultiAlternatives')
    def test_send_email_already_sent(self, mock_email_class, email_notification):
        """Test task skips sending if email is already sent."""
        email_notification.status = 'sent'
        email_notification.save()

        result = send_email_notification(email_notification.id)

        assert result['success'] is True
        assert result['already_sent'] is True
        mock_email_class.assert_not_called() # Should not have been called

    @patch('apps.notifications.tasks.EmailMultiAlternatives')
    def test_send_email_failure_and_retry(self, mock_email_class, email_notification):
        """Test email sending failure and retry logic."""
        mock_email_instance = MagicMock()
        mock_email_class.return_value = mock_email_instance
        mock_email_instance.send.side_effect = Exception("SMTP Error")

        # Patch the task's retry mechanism
        with patch.object(send_email_notification, 'retry') as mock_retry:
            # Mock the task request to simulate retries
            send_email_notification.request = MagicMock(retries=0)

            with pytest.raises(Exception): # The task should re-raise or handle the retry
                send_email_notification(email_notification.id)

            # Check if retry was called
            mock_retry.assert_called_once()
            assert 'exc' in mock_retry.call_args.kwargs
            assert 'countdown' in mock_retry.call_args.kwargs

            # Check that the email object was updated to 'failed'
            email_notification.refresh_from_db()
            assert email_notification.status == 'failed'
            assert 'SMTP Error' in email_notification.error_message


class TestCleanupOldNotificationsTask:

    @pytest.fixture
    def old_read_notification(self, user):
        return Notification.objects.create(
            user=user,
            title='Old Read Notification',
            message='This notification is old and read.',
            is_read=True,
            created=timezone.now() - timedelta(days=100)
        )

    @pytest.fixture
    def old_unread_notification(self, user):
        return Notification.objects.create(
            user=user,
            title='Old Unread Notification',
            message='This notification is old but unread.',
            is_read=False,
            created=timezone.now() - timedelta(days=100)
        )

    @pytest.fixture
    def recent_notification(self, user):
        return Notification.objects.create(
            user=user,
            title='Recent Notification',
            message='This notification is recent.',
            is_read=False,
            created=timezone.now() - timedelta(days=10)
        )

    def test_cleanup_old_notifications(self, old_read_notification, old_unread_notification, recent_notification):
        """Test cleanup of old read notifications."""
        # Ensure we have 3 notifications before cleanup
        initial_count = Notification.objects.count()
        assert initial_count >= 3

        # Run cleanup task for notifications older than 90 days
        result = cleanup_old_notifications(days_to_keep=90)

        assert result['success'] is True
        # Only the old read notification should be deleted
        assert result['deleted_in_app'] == 1
        # Check that the correct notification was deleted
        assert not Notification.objects.filter(id=old_read_notification.id).exists()
        # Check that others still exist
        assert Notification.objects.filter(id=old_unread_notification.id).exists()
        assert Notification.objects.filter(id=recent_notification.id).exists()

        # Final count should be initial - 1
        final_count = Notification.objects.count()
        assert final_count == initial_count - 1


class TestRetryFailedEmailsTask:

    @pytest.fixture
    def failed_email_ready(self):
        """A failed email that is ready for retry."""
        return EmailNotification.objects.create(
            subject='Failed Email Ready',
            body_text='This email failed and is ready for retry.',
            recipient_email='ready@example.com',
            status='failed',
            retry_count=1,
            max_retries=3,
            next_retry_at=timezone.now() - timedelta(minutes=5) # In the past
        )

    @pytest.fixture
    def failed_email_not_ready(self):
        """A failed email that is not yet ready for retry."""
        return EmailNotification.objects.create(
            subject='Failed Email Not Ready',
            body_text='This email failed but is not ready for retry.',
            recipient_email='notready@example.com',
            status='failed',
            retry_count=1,
            max_retries=3,
            next_retry_at=timezone.now() + timedelta(minutes=5) # In the future
        )

    @pytest.fixture
    def failed_email_max_retries(self):
        """A failed email that has reached max retries."""
        return EmailNotification.objects.create(
            subject='Failed Email Max Retries',
            body_text='This email failed and reached max retries.',
            recipient_email='maxretries@example.com',
            status='failed',
            retry_count=3,
            max_retries=3,
            next_retry_at=timezone.now() - timedelta(minutes=5) # In the past
        )

    @patch('apps.notifications.tasks.send_email_notification')
    def test_retry_failed_emails(self, mock_send_task, failed_email_ready, failed_email_not_ready, failed_email_max_retries):
        """Test retrying failed emails that are ready."""
        # Run the retry task
        result = retry_failed_emails()

        assert result['success'] is True
        # Only one email (failed_email_ready) should be queued for retry
        assert result['emails_queued'] == 1
        mock_send_task.delay.assert_called_once_with(str(failed_email_ready.id))

        # Ensure other emails were not queued
        # This check is implicit in the fact that delay was only called once with the correct ID.
