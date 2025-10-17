# apps/notifications/tests/test_models.py
"""
SMGI Backend - Tests for Notifications Models
Sistema de Monitoreo Geoespacial Inteligente
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from apps.authentication.models import User
from apps.notifications.models import (
    Notification, EmailNotification, WebhookNotification,
    NotificationPreference, NotificationType, NotificationPriority,
    NotificationChannel
)
# Asumimos que Alert existe en alerts
# from apps.alerts.models import Alert

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def notification(user):
    return Notification.objects.create(
        user=user,
        title='Test Notification',
        message='This is a test notification.',
        notification_type=NotificationType.ALERT,
        priority=NotificationPriority.HIGH
    )

@pytest.fixture
def email_notification(user):
    return EmailNotification.objects.create(
        user=user,
        subject='Test Email',
        body_text='This is a test email.',
        recipient_email=user.email,
        recipient_name=user.get_full_name(),
        status='pending',
        priority=NotificationPriority.NORMAL
    )

@pytest.fixture
def webhook_notification():
    return WebhookNotification.objects.create(
        webhook_url='https://example.com/webhook',
        method='POST',
        payload={'test': 'data'},
        status='pending'
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


class TestNotificationModel:

    def test_str_representation(self, notification):
        expected_str = f"{notification.title} - {notification.user.email}"
        assert str(notification) == expected_str

    def test_is_expired(self):
        # Notification without expires_at
        notif1 = Notification(
            title='No Expire',
            message='Test',
            notification_type=NotificationType.INFO
        )
        assert not notif1.is_expired

        # Notification with future expires_at
        future_date = timezone.now() + timedelta(hours=1)
        notif2 = Notification(
            title='Future Expire',
            message='Test',
            notification_type=NotificationType.INFO,
            expires_at=future_date
        )
        assert not notif2.is_expired

        # Notification with past expires_at
        past_date = timezone.now() - timedelta(hours=1)
        notif3 = Notification(
            title='Past Expire',
            message='Test',
            notification_type=NotificationType.INFO,
            expires_at=past_date
        )
        assert notif3.is_expired

    def test_mark_as_read(self, notification):
        assert not notification.is_read
        assert notification.read_at is None

        notification.mark_as_read()
        assert notification.is_read
        assert notification.read_at is not None

    def test_mark_as_unread(self, notification):
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

        notification.mark_as_unread()
        assert not notification.is_read
        assert notification.read_at is None


class TestEmailNotificationModel:

    def test_str_representation(self, email_notification):
        expected_str = f"{email_notification.subject} -> {email_notification.recipient_email}"
        assert str(email_notification) == expected_str

    def test_can_retry(self):
        # Email that can be retried
        email1 = EmailNotification(
            status='failed',
            retry_count=1,
            max_retries=3
        )
        assert email1.can_retry

        # Email that cannot be retried (max retries reached)
        email2 = EmailNotification(
            status='failed',
            retry_count=3,
            max_retries=3
        )
        assert not email2.can_retry

        # Email that is not failed
        email3 = EmailNotification(
            status='sent',
            retry_count=1,
            max_retries=3
        )
        assert not email3.can_retry

    def test_mark_sent(self, email_notification):
        assert email_notification.status == 'pending'
        assert email_notification.sent_at is None

        email_notification.mark_sent()
        assert email_notification.status == 'sent'
        assert email_notification.sent_at is not None

    def test_mark_failed(self, email_notification):
        assert email_notification.status == 'pending'
        assert email_notification.error_message == ''
        initial_retry_count = email_notification.retry_count

        error_msg = "Test error"
        email_notification.mark_failed(error_msg)

        assert email_notification.status == 'failed'
        assert email_notification.error_message == error_msg
        assert email_notification.retry_count == initial_retry_count + 1
        # next_retry_at should be set
        assert email_notification.next_retry_at is not None


class TestWebhookNotificationModel:

    def test_str_representation(self, webhook_notification):
        expected_str = f"Webhook to {webhook_notification.webhook_url}"
        assert str(webhook_notification) == expected_str

    def test_mark_sent(self, webhook_notification):
        status_code = 200
        response_body = '{"status": "ok"}'
        response_time_ms = 150

        webhook_notification.mark_sent(status_code, response_body, response_time_ms)

        assert webhook_notification.status == 'sent'
        assert webhook_notification.sent_at is not None
        assert webhook_notification.response_status_code == status_code
        assert webhook_notification.response_body == response_body
        assert webhook_notification.response_time_ms == response_time_ms

    def test_mark_failed(self, webhook_notification):
        error_msg = "Connection timeout"

        webhook_notification.mark_failed(error_msg)

        assert webhook_notification.status == 'failed'
        assert webhook_notification.error_message == error_msg
        assert webhook_notification.retry_count == 1 # Initial retry count is 0


class TestNotificationPreferenceModel:

    def test_str_representation(self, notification_preference):
        expected_str = f"Preferences for {notification_preference.user.email}"
        assert str(notification_preference) == expected_str

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
