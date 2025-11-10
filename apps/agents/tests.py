"""
Tests for Agents app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import Agent, AgentCategory, AgentExecution, AgentSchedule, AgentRating

User = get_user_model()


class AgentModelTest(TestCase):
    """Test cases for Agent model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='developer'
        )
        
        self.category = AgentCategory.objects.create(
            name='Test Category',
            created_by=self.user
        )
        
        self.agent = Agent.objects.create(
            name='Test Agent',
            description='Test agent description',
            category=self.category,
            agent_type='statistics',
            code='print("Hello")',
            created_by=self.user
        )
    
    def test_agent_creation(self):
        """Test agent is created correctly."""
        self.assertEqual(self.agent.name, 'Test Agent')
        self.assertEqual(self.agent.agent_type, 'statistics')
        self.assertEqual(self.agent.status, 'draft')
        self.assertEqual(self.agent.execution_count, 0)
    
    def test_agent_success_rate(self):
        """Test success rate calculation."""
        self.agent.execution_count = 10
        self.agent.success_count = 8
        self.assertEqual(self.agent.success_rate, 80.0)
    
    def test_agent_str(self):
        """Test agent string representation."""
        self.assertEqual(str(self.agent), 'Test Agent v1.0.0')


class AgentAPITest(APITestCase):
    """Test cases for Agent API endpoints."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()
        
        self.developer = User.objects.create_user(
            username='developer',
            email='dev@example.com',
            password='devpass123',
            role='developer'
        )
        
        self.viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='viewpass123',
            role='viewer'
        )
        
        self.category = AgentCategory.objects.create(
            name='Test Category',
            created_by=self.developer
        )
        
        self.agent = Agent.objects.create(
            name='Test Agent',
            description='Test description',
            category=self.category,
            agent_type='statistics',
            status='published',
            is_public=True,
            code='print("Test")',
            created_by=self.developer
        )
    
    def test_list_agents(self):
        """Test listing agents."""
        url = reverse('agent-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_retrieve_agent(self):
        """Test retrieving a single agent."""
        url = reverse('agent-detail', kwargs={'pk': self.agent.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Agent')
    
    def test_create_agent_as_developer(self):
        """Test creating agent as developer."""
        self.client.force_authenticate(user=self.developer)
        url = reverse('agent-list')
        data = {
            'name': 'New Agent',
            'description': 'New agent description',
            'agent_type': 'classification',
            'code': 'print("New agent")',
            'version': '1.0.0'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Agent.objects.count(), 2)
    
    def test_create_agent_as_viewer(self):
        """Test creating agent as viewer (should fail)."""
        self.client.force_authenticate(user=self.viewer)
        url = reverse('agent-list')
        data = {
            'name': 'New Agent',
            'description': 'New agent description',
            'agent_type': 'classification',
            'code': 'print("New agent")'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_publish_agent(self):
        """Test publishing an agent."""
        self.agent.status = 'draft'
        self.agent.save()
        
        self.client.force_authenticate(user=self.developer)
        url = reverse('agent-publish', kwargs={'pk': self.agent.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.status, 'published')
    
    def test_execute_agent(self):
        """Test executing an agent."""
        self.client.force_authenticate(user=self.developer)
        url = reverse('agent-execute', kwargs={'pk': self.agent.pk})
        data = {
            'name': 'Test Execution',
            'parameters': {'test': 'value'}
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('execution_id', response.data)
        self.assertIn('task_id', response.data)
    
    def test_rate_agent(self):
        """Test rating an agent."""
        self.client.force_authenticate(user=self.developer)
        url = reverse('agent-rate', kwargs={'pk': self.agent.pk})
        data = {
            'agent': self.agent.id,
            'rating': 5,
            'comment': 'Excellent agent!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.rating, 5.0)
    
    def test_marketplace(self):
        """Test marketplace endpoint."""
        url = reverse('agent-marketplace')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class AgentExecutionTest(TestCase):
    """Test cases for AgentExecution model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='developer'
        )
        
        self.agent = Agent.objects.create(
            name='Test Agent',
            description='Test description',
            agent_type='statistics',
            code='print("Test")',
            created_by=self.user
        )
        
        self.execution = AgentExecution.objects.create(
            agent=self.agent,
            name='Test Execution',
            parameters={'test': 'value'},
            created_by=self.user
        )
    
    def test_execution_creation(self):
        """Test execution is created correctly."""
        self.assertEqual(self.execution.agent, self.agent)
        self.assertEqual(self.execution.status, 'pending')
        self.assertIsNone(self.execution.started_at)
    
    def test_execution_duration(self):
        """Test duration calculation."""
        from django.utils import timezone
        from datetime import timedelta
        
        self.execution.started_at = timezone.now()
        self.execution.completed_at = self.execution.started_at + timedelta(seconds=30)
        
        self.assertEqual(self.execution.duration, 30.0)


class AgentScheduleTest(TestCase):
    """Test cases for AgentSchedule model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.agent = Agent.objects.create(
            name='Test Agent',
            description='Test description',
            agent_type='statistics',
            code='print("Test")',
            created_by=self.user
        )
        
        self.schedule = AgentSchedule.objects.create(
            agent=self.agent,
            name='Test Schedule',
            schedule_type='interval',
            interval_minutes=60,
            created_by=self.user
        )
    
    def test_schedule_creation(self):
        """Test schedule is created correctly."""
        self.assertEqual(self.schedule.agent, self.agent)
        self.assertEqual(self.schedule.schedule_type, 'interval')
        self.assertEqual(self.schedule.interval_minutes, 60)
        self.assertTrue(self.schedule.is_enabled)
        self.assertEqual(self.schedule.run_count, 0)
    
    def test_schedule_str(self):
        """Test schedule string representation."""
        self.assertEqual(str(self.schedule), 'Test Schedule - Test Agent')
