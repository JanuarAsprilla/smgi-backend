"""
Tests for Alerts app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import (
    AlertChannel,
    AlertRule,
    Alert,
    AlertLog,
    AlertSubscription,
    AlertTemplate
)
from apps.monitoring.models import MonitoringProject, Monitor, Detection

User = get_user_model()


class AlertChannelModelTest(TestCase):
    """Test cases for AlertChannel model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.channel = AlertChannel.objects.create(
            name='Test Email Channel',
            description='Test email channel',
            channel_type='email',
            configuration={'from_email': 'test@smgi.com'},
            created_by=self.user
        )
    
    def test_channel_creation(self):
        """Test channel is created correctly."""
        self.assertEqual(self.channel.name, 'Test Email Channel')
        self.assertEqual(self.channel.channel_type, 'email')
        self.assertTrue(self.channel.is_enabled)
        self.assertEqual(self.channel.total_sent, 0)
        self.assertEqual(self.channel.total_failed, 0)
    
    def test_channel_str(self):
        """Test channel string representation."""
        self.assertEqual(str(self.channel), 'Test Email Channel (Email)')


class AlertRuleModelTest(TestCase):
    """Test cases for AlertRule model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.channel = AlertChannel.objects.create(
            name='Test Channel',
            channel_type='email',
            created_by=self.user
        )
        
        self.project = MonitoringProject.objects.create(
            name='Test Project',
            created_by=self.user
        )
        
        self.monitor = Monitor.objects.create(
            project=self.project,
            name='Test Monitor',
            monitor_type='change_detection',
            created_by=self.user
        )
        
        self.rule = AlertRule.objects.create(
            name='Test Rule',
            description='Test alert rule',
            severity='high',
            trigger_type='detection',
            message_template='Alert: {{ title }}',
            created_by=self.user
        )
        
        self.rule.channels.add(self.channel)
        self.rule.monitors.add(self.monitor)
        self.rule.recipients.add(self.user)
    
    def test_rule_creation(self):
        """Test rule is created correctly."""
        self.assertEqual(self.rule.name, 'Test Rule')
        self.assertEqual(self.rule.severity, 'high')
        self.assertTrue(self.rule.is_enabled)
        self.assertEqual(self.rule.trigger_count, 0)
    
    def test_rule_str(self):
        """Test rule string representation."""
        self.assertEqual(str(self.rule), 'Test Rule')


class AlertModelTest(TestCase):
    """Test cases for Alert model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.channel = AlertChannel.objects.create(
            name='Test Channel',
            channel_type='email',
            created_by=self.user
        )
        
        self.rule = AlertRule.objects.create(
            name='Test Rule',
            severity='high',
            trigger_type='detection',
            created_by=self.user
        )
        
        self.rule.channels.add(self.channel)
        self.rule.recipients.add(self.user)
        
        self.alert = Alert.objects.create(
            rule=self.rule,
            title='Test Alert',
            message='Test alert message',
            severity='high',
            created_by=self.user
        )
    
    def test_alert_creation(self):
        """Test alert is created correctly."""
        self.assertEqual(self.alert.title, 'Test Alert')
        self.assertEqual(self.alert.severity, 'high')
        self.assertEqual(self.alert.status, 'pending')
        self.assertIsNone(self.alert.sent_at)
    
    def test_alert_str(self):
        """Test alert string representation."""
        self.assertEqual(str(self.alert), 'Test Alert - Alta')


class AlertAPITest(APITestCase):
    """Test cases for Alert API endpoints."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()
        
        self.analyst = User.objects.create_user(
            username='analyst',
            email='analyst@example.com',
            password='analystpass123',
            role='analyst'
        )
        
        self.viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='viewpass123',
            role='viewer'
        )
        
        self.channel = AlertChannel.objects.create(
            name='Test Channel',
            channel_type='email',
            created_by=self.analyst
        )
        
        self.project = MonitoringProject.objects.create(
            name='Test Project',
            created_by=self.analyst
        )
        
        self.monitor = Monitor.objects.create(
            project=self.project,
            name='Test Monitor',
            monitor_type='change_detection',
            created_by=self.analyst
        )
        
        self.rule = AlertRule.objects.create(
            name='Test Rule',
            severity='high',
            trigger_type='detection',
            created_by=self.analyst
        )
        
        self.rule.channels.add(self.channel)
        self.rule.recipients.add(self.analyst)
        
        self.alert = Alert.objects.create(
            rule=self.rule,
            title='Test Alert',
            message='Test message',
            severity='high',
            monitor=self.monitor,
            created_by=self.analyst
        )
    
    def test_list_channels(self):
        """Test listing alert channels."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('alertchannel-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_channel_as_analyst(self):
        """Test creating channel as analyst."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('alertchannel-list')
        data = {
            'name': 'New Channel',
            'description': 'New test channel',
            'channel_type': 'webhook',
            'configuration': {'url': 'https://example.com/webhook'}
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertChannel.objects.count(), 2)
    
    def test_create_channel_as_viewer(self):
        """Test creating channel as viewer (should fail)."""
        self.client.force_authenticate(user=self.viewer)
        url = reverse('alertchannel-list')
        data = {
            'name': 'New Channel',
            'channel_type': 'email'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_rules(self):
        """Test listing alert rules."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('alertrule-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_rule(self):
        """Test creating alert rule."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('alertrule-list')
        data = {
            'name': 'New Rule',
            'description': 'New test rule',
            'severity': 'medium',
            'trigger_type': 'threshold',
            'channels': [self.channel.id],
            'recipients': [self.analyst.id]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertRule.objects.count(), 2)
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('alert-acknowledge', kwargs={'pk': self.alert.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, 'acknowledged')
        self.assertEqual(self.alert.acknowledged_by, self.analyst)
        self.assertIsNotNone(self.alert.acknowledged_at)
    
    def test_resolve_alert(self):
        """Test resolving an alert."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('alert-resolve', kwargs={'pk': self.alert.pk})
        data = {'notes': 'Alert resolved successfully'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, 'resolved')
        self.assertEqual(self.alert.resolved_by, self.analyst)
        self.assertIsNotNone(self.alert.resolved_at)
        self.assertEqual(self.alert.resolution_notes, 'Alert resolved successfully')
    
    def test_alert_dashboard(self):
        """Test alert dashboard endpoint."""
        # Create more alerts
        Alert.objects.create(
            rule=self.rule,
            title='Alert 2',
            message='Test',
            severity='critical',
            created_by=self.analyst
        )
        Alert.objects.create(
            rule=self.rule,
            title='Alert 3',
            message='Test',
            severity='medium',
            created_by=self.analyst
        )
        
        self.client.force_authenticate(user=self.analyst)
        url = reverse('alert-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('statistics', response.data)
        self.assertIn('recent_alerts', response.data)


class AlertSubscriptionModelTest(TestCase):
    """Test cases for AlertSubscription model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.channel = AlertChannel.objects.create(
            name='Test Channel',
            channel_type='email',
            created_by=self.user
        )
        
        self.subscription = AlertSubscription.objects.create(
            user=self.user,
            min_severity='medium',
            created_by=self.user
        )
        
        self.subscription.channels.add(self.channel)
    
    def test_subscription_creation(self):
        """Test subscription is created correctly."""
        self.assertEqual(self.subscription.user, self.user)
        self.assertEqual(self.subscription.min_severity, 'medium')
        self.assertTrue(self.subscription.is_enabled)
    
    def test_subscription_str(self):
        """Test subscription string representation."""
        self.assertEqual(str(self.subscription), 'Suscripción de testuser')


class AlertTemplateModelTest(TestCase):
    """Test cases for AlertTemplate model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.template = AlertTemplate.objects.create(
            name='Test Template',
            description='Test template',
            subject_template='Alert: {{ title }}',
            body_template='Message: {{ message }}',
            variables=['title', 'message'],
            created_by=self.user
        )
    
    def test_template_creation(self):
        """Test template is created correctly."""
        self.assertEqual(self.template.name, 'Test Template')
        self.assertFalse(self.template.is_default)
        self.assertEqual(len(self.template.variables), 2)
    
    def test_template_str(self):
        """Test template string representation."""
        self.assertEqual(str(self.template), 'Test Template')
