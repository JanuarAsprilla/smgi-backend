"""
Tests for Notifications app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Notification
from .services import NotificationService, EmailService, SMSService

User = get_user_model()


class NotificationModelTest(TestCase):
    """Test cases for Notification model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            type='info',
            title='Test Notification',
            message='Test message'
        )
    
    def test_notification_creation(self):
        """Test notification is created correctly."""
        self.assertEqual(self.notification.title, 'Test Notification')
        self.assertEqual(self.notification.user, self.user)
        self.assertFalse(self.notification.is_read)
    
    def test_notification_str(self):
        """Test notification string representation."""
        self.assertEqual(str(self.notification), f'Test Notification - {self.user.username}')
    
    def test_mark_as_read(self):
        """Test marking notification as read."""
        self.assertFalse(self.notification.is_read)
        self.assertIsNone(self.notification.read_at)
        
        self.notification.mark_as_read()
        
        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)


class NotificationAPITest(APITestCase):
    """Test cases for Notification API."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            type='info',
            title='Test Notification',
            message='Test message'
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_get_preferences(self):
        """Test getting notification preferences."""
        response = self.client.get('/api/v1/notifications/preferences/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('email_notifications', response.data)
    
    def test_update_preferences(self):
        """Test updating notification preferences."""
        data = {
            'email_notifications': False,
            'sms_notifications': True
        }
        response = self.client.put('/api/v1/notifications/update-preferences/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.email_notifications)
        self.assertTrue(self.user.profile.sms_notifications)


class EmailServiceTest(TestCase):
    """Test cases for EmailService."""
    
    def test_email_service_exists(self):
        """Test EmailService class exists."""
        self.assertTrue(hasattr(EmailService, 'send_email'))
        self.assertTrue(hasattr(EmailService, 'send_analysis_complete'))
        self.assertTrue(hasattr(EmailService, 'send_alert_notification'))


class SMSServiceTest(TestCase):
    """Test cases for SMSService."""
    
    def test_sms_service_exists(self):
        """Test SMSService class exists."""
        sms_service = SMSService()
        self.assertTrue(hasattr(sms_service, 'send_sms'))
        self.assertTrue(hasattr(sms_service, 'send_analysis_complete_sms'))


class NotificationServiceTest(TestCase):
    """Test cases for NotificationService."""
    
    def test_notification_service_exists(self):
        """Test NotificationService class exists."""
        notification_service = NotificationService()
        self.assertTrue(hasattr(notification_service, 'notify_analysis_complete'))
        self.assertTrue(hasattr(notification_service, 'notify_analysis_failed'))
        self.assertTrue(hasattr(notification_service, 'notify_alert'))
