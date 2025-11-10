"""
Tests for Monitoring app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import (
    MonitoringProject,
    Monitor,
    Detection,
    ChangeRecord,
    Baseline
)
from apps.geodata.models import DataSource, Layer

User = get_user_model()


class MonitoringProjectModelTest(TestCase):
    """Test cases for MonitoringProject model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.project = MonitoringProject.objects.create(
            name='Test Project',
            description='Test project description',
            status='active',
            created_by=self.user
        )
    
    def test_project_creation(self):
        """Test project is created correctly."""
        self.assertEqual(self.project.name, 'Test Project')
        self.assertEqual(self.project.status, 'active')
        self.assertTrue(self.project.is_active)
    
    def test_project_str(self):
        """Test project string representation."""
        self.assertEqual(str(self.project), 'Test Project')


class MonitorModelTest(TestCase):
    """Test cases for Monitor model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.project = MonitoringProject.objects.create(
            name='Test Project',
            created_by=self.user
        )
        
        self.data_source = DataSource.objects.create(
            name='Test Source',
            source_type='wfs',
            url='http://example.com/wfs',
            created_by=self.user
        )
        
        self.layer = Layer.objects.create(
            name='Test Layer',
            data_source=self.data_source,
            layer_type='vector',
            geometry_type='polygon',
            created_by=self.user
        )
        
        self.monitor = Monitor.objects.create(
            project=self.project,
            name='Test Monitor',
            description='Test monitor description',
            monitor_type='change_detection',
            check_interval=60,
            created_by=self.user
        )
        
        self.monitor.layers.add(self.layer)
    
    def test_monitor_creation(self):
        """Test monitor is created correctly."""
        self.assertEqual(self.monitor.name, 'Test Monitor')
        self.assertEqual(self.monitor.monitor_type, 'change_detection')
        self.assertEqual(self.monitor.status, 'active')
        self.assertEqual(self.monitor.check_count, 0)
        self.assertEqual(self.monitor.detection_count, 0)
    
    def test_monitor_str(self):
        """Test monitor string representation."""
        self.assertEqual(str(self.monitor), 'Test Monitor - Test Project')


class DetectionModelTest(TestCase):
    """Test cases for Detection model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
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
        
        self.detection = Detection.objects.create(
            monitor=self.monitor,
            title='Test Detection',
            description='Test detection description',
            severity='high',
            location=Point(0, 0),
            created_by=self.user
        )
    
    def test_detection_creation(self):
        """Test detection is created correctly."""
        self.assertEqual(self.detection.title, 'Test Detection')
        self.assertEqual(self.detection.severity, 'high')
        self.assertEqual(self.detection.status, 'new')
    
    def test_detection_str(self):
        """Test detection string representation."""
        self.assertEqual(str(self.detection), 'Test Detection - Test Monitor')


class MonitoringAPITest(APITestCase):
    """Test cases for Monitoring API endpoints."""
    
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
        
        self.project = MonitoringProject.objects.create(
            name='Test Project',
            description='Test description',
            status='active',
            created_by=self.analyst
        )
        
        self.monitor = Monitor.objects.create(
            project=self.project,
            name='Test Monitor',
            monitor_type='change_detection',
            created_by=self.analyst
        )
    
    def test_list_projects(self):
        """Test listing monitoring projects."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('monitoringproject-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_project_as_analyst(self):
        """Test creating project as analyst."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('monitoringproject-list')
        data = {
            'name': 'New Project',
            'description': 'New project description',
            'status': 'active'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MonitoringProject.objects.count(), 2)
    
    def test_create_project_as_viewer(self):
        """Test creating project as viewer (should fail)."""
        self.client.force_authenticate(user=self.viewer)
        url = reverse('monitoringproject-list')
        data = {
            'name': 'New Project',
            'description': 'New project description'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_run_monitor_check(self):
        """Test running a manual monitor check."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('monitor-run-check', kwargs={'pk': self.monitor.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
    
    def test_pause_monitor(self):
        """Test pausing a monitor."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('monitor-pause', kwargs={'pk': self.monitor.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.status, 'paused')
    
    def test_resume_monitor(self):
        """Test resuming a monitor."""
        self.monitor.status = 'paused'
        self.monitor.save()
        
        self.client.force_authenticate(user=self.analyst)
        url = reverse('monitor-resume', kwargs={'pk': self.monitor.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.status, 'active')
    
    def test_detection_dashboard(self):
        """Test detection dashboard endpoint."""
        # Create some detections
        Detection.objects.create(
            monitor=self.monitor,
            title='Detection 1',
            severity='high',
            created_by=self.analyst
        )
        Detection.objects.create(
            monitor=self.monitor,
            title='Detection 2',
            severity='critical',
            created_by=self.analyst
        )
        
        self.client.force_authenticate(user=self.analyst)
        url = reverse('detection-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('statistics', response.data)
        self.assertIn('recent_detections', response.data)


class BaselineModelTest(TestCase):
    """Test cases for Baseline model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
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
        
        from django.utils import timezone
        self.baseline = Baseline.objects.create(
            monitor=self.monitor,
            name='Test Baseline',
            baseline_date=timezone.now(),
            baseline_data={'test': 'data'},
            feature_count=100,
            is_current=True,
            created_by=self.user
        )
    
    def test_baseline_creation(self):
        """Test baseline is created correctly."""
        self.assertEqual(self.baseline.name, 'Test Baseline')
        self.assertEqual(self.baseline.feature_count, 100)
        self.assertTrue(self.baseline.is_current)
    
    def test_baseline_str(self):
        """Test baseline string representation."""
        self.assertEqual(str(self.baseline), 'Test Baseline - Test Monitor')
