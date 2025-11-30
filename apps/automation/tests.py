"""
Tests for Automation app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from .models import (
    Workflow,
    WorkflowTask,
    WorkflowExecution,
    TaskExecution,
    AutomationRule,
    WorkflowSchedule
)
from apps.agents.models import Agent, AgentCategory

User = get_user_model()


class WorkflowModelTest(TestCase):
    """Test cases for Workflow model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='developer'
        )
        
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            description='Test workflow description',
            status='draft',
            trigger_type='manual',
            created_by=self.user
        )
    
    def test_workflow_creation(self):
        """Test workflow is created correctly."""
        self.assertEqual(self.workflow.name, 'Test Workflow')
        self.assertEqual(self.workflow.status, 'draft')
        self.assertEqual(self.workflow.execution_count, 0)
        self.assertEqual(self.workflow.success_rate, 0.0)
    
    def test_workflow_str(self):
        """Test workflow string representation."""
        self.assertEqual(str(self.workflow), 'Test Workflow')
    
    def test_can_execute(self):
        """Test can_execute method."""
        self.workflow.status = 'active'
        self.workflow.is_active = True
        self.assertTrue(self.workflow.can_execute())
        
        self.workflow.status = 'draft'
        self.assertFalse(self.workflow.can_execute())
        
        self.workflow.status = 'active'
        self.workflow.is_active = False
        self.assertFalse(self.workflow.can_execute())
    
    def test_increment_stats(self):
        """Test increment_stats method."""
        initial_count = self.workflow.execution_count
        initial_success = self.workflow.success_count
        initial_failure = self.workflow.failure_count
        
        # Test successful execution
        self.workflow.increment_stats(success=True)
        self.assertEqual(self.workflow.execution_count, initial_count + 1)
        self.assertEqual(self.workflow.success_count, initial_success + 1)
        self.assertEqual(self.workflow.failure_count, initial_failure)
        self.assertIsNotNone(self.workflow.last_execution)
        
        # Test failed execution
        self.workflow.increment_stats(success=False)
        self.assertEqual(self.workflow.execution_count, initial_count + 2)
        self.assertEqual(self.workflow.success_count, initial_success + 1)
        self.assertEqual(self.workflow.failure_count, initial_failure + 1)


class WorkflowTaskModelTest(TestCase):
    """Test cases for WorkflowTask model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='developer'
        )
        
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            created_by=self.user
        )
        
        self.task = WorkflowTask.objects.create(
            workflow=self.workflow,
            name='Test Task',
            description='Test task description',
            task_type='notification',
            order=1,
            created_by=self.user
        )
    
    def test_task_creation(self):
        """Test task is created correctly."""
        self.assertEqual(self.task.name, 'Test Task')
        self.assertEqual(self.task.task_type, 'notification')
        self.assertEqual(self.task.order, 1)
        self.assertFalse(self.task.retry_on_failure)
    
    def test_task_str(self):
        """Test task string representation."""
        self.assertEqual(str(self.task), 'Test Workflow - Test Task')


class WorkflowExecutionModelTest(TestCase):
    """Test cases for WorkflowExecution model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='developer'
        )
        
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            created_by=self.user
        )
        
        self.execution = WorkflowExecution.objects.create(
            workflow=self.workflow,
            input_data={'test': 'data'},
            trigger_source='manual',
            created_by=self.user
        )
    
    def test_execution_creation(self):
        """Test execution is created correctly."""
        self.assertEqual(self.execution.workflow, self.workflow)
        self.assertEqual(self.execution.status, 'pending')
        self.assertIsNone(self.execution.started_at)
        self.assertEqual(self.execution.tasks_total, 0)
    
    def test_execution_duration(self):
        """Test duration calculation."""
        from django.utils import timezone
        from datetime import timedelta
        
        self.execution.started_at = timezone.now()
        self.execution.completed_at = self.execution.started_at + timedelta(seconds=30)
        
        self.assertEqual(self.execution.duration, 30.0)
    
    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        self.execution.tasks_total = 10
        self.execution.tasks_completed = 5
        self.assertEqual(self.execution.progress_percentage, 50.0)
        
        self.execution.tasks_total = 0
        self.assertEqual(self.execution.progress_percentage, 0.0)
    
    def test_can_cancel(self):
        """Test can_cancel method."""
        self.execution.status = 'pending'
        self.assertTrue(self.execution.can_cancel())
        
        self.execution.status = 'running'
        self.assertTrue(self.execution.can_cancel())
        
        self.execution.status = 'completed'
        self.assertFalse(self.execution.can_cancel())
        
        self.execution.status = 'failed'
        self.assertFalse(self.execution.can_cancel())
    
    def test_can_retry(self):
        """Test can_retry method."""
        self.execution.status = 'failed'
        self.assertTrue(self.execution.can_retry())
        
        self.execution.status = 'completed'
        self.assertFalse(self.execution.can_retry())


class WorkflowAPITest(APITestCase):
    """Test cases for Workflow API endpoints."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()
        
        self.developer = User.objects.create_user(
            username='developer',
            email='dev@example.com',
            password='devpass123',
            role='developer'
        )
        
        self.analyst = User.objects.create_user(
            username='analyst',
            email='analyst@example.com',
            password='analystpass123',
            role='analyst'
        )
        
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            description='Test description',
            status='active',
            trigger_type='manual',
            created_by=self.developer
        )
    
    def test_list_workflows(self):
        """Test listing workflows."""
        self.client.force_authenticate(user=self.developer)
        url = reverse('workflow-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_workflow_as_developer(self):
        """Test creating workflow as developer."""
        self.client.force_authenticate(user=self.developer)
        url = reverse('workflow-list')
        data = {
            'name': 'New Workflow',
            'description': 'New workflow description',
            'status': 'draft',
            'trigger_type': 'schedule',
            'workflow_definition': {'tasks': []}
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Workflow.objects.count(), 2)
    
    def test_create_workflow_as_analyst(self):
        """Test creating workflow as analyst (should fail)."""
        self.client.force_authenticate(user=self.analyst)
        url = reverse('workflow-list')
        data = {
            'name': 'New Workflow',
            'description': 'New workflow description'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_execute_workflow(self):
        """Test executing a workflow."""
        self.client.force_authenticate(user=self.developer)
        url = reverse('workflow-execute', kwargs={'pk': self.workflow.pk})
        data = {'input_data': {'test': 'value'}}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('execution_id', response.data)
        self.assertIn('task_id', response.data)
    
    def test_activate_workflow(self):
        """Test activating a workflow."""
        self.workflow.status = 'draft'
        self.workflow.save()
        
        self.client.force_authenticate(user=self.developer)
        url = reverse('workflow-activate', kwargs={'pk': self.workflow.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.status, 'active')
    
    def test_pause_workflow(self):
        """Test pausing a workflow."""
        self.client.force_authenticate(user=self.developer)
        url = reverse('workflow-pause', kwargs={'pk': self.workflow.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.status, 'paused')


class AutomationRuleModelTest(TestCase):
    """Test cases for AutomationRule model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            created_by=self.user
        )
        
        self.rule = AutomationRule.objects.create(
            name='Test Rule',
            description='Test rule description',
            trigger_event='detection_created',
            workflow=self.workflow,
            created_by=self.user
        )
    
    def test_rule_creation(self):
        """Test rule is created correctly."""
        self.assertEqual(self.rule.name, 'Test Rule')
        self.assertEqual(self.rule.trigger_event, 'detection_created')
        self.assertEqual(self.rule.status, 'active')
        self.assertEqual(self.rule.trigger_count, 0)
    
    def test_rule_str(self):
        """Test rule string representation."""
        self.assertEqual(str(self.rule), 'Test Rule')
    
    def test_is_throttled(self):
        """Test is_throttled method."""
        from django.utils import timezone
        from datetime import timedelta
        
        # No throttle configured
        self.rule.throttle_minutes = 0
        self.assertFalse(self.rule.is_throttled())
        
        # Not triggered yet
        self.rule.throttle_minutes = 10
        self.rule.last_triggered = None
        self.assertFalse(self.rule.is_throttled())
        
        # Recently triggered (within throttle period)
        self.rule.last_triggered = timezone.now() - timedelta(minutes=5)
        self.assertTrue(self.rule.is_throttled())
        
        # Triggered outside throttle period
        self.rule.last_triggered = timezone.now() - timedelta(minutes=15)
        self.assertFalse(self.rule.is_throttled())
    
    def test_can_trigger(self):
        """Test can_trigger method."""
        self.rule.status = 'active'
        self.rule.is_active = True
        self.rule.throttle_minutes = 0
        self.assertTrue(self.rule.can_trigger())
        
        self.rule.status = 'draft'
        self.assertFalse(self.rule.can_trigger())
    
    def test_increment_trigger(self):
        """Test increment_trigger method."""
        initial_count = self.rule.trigger_count
        
        self.rule.increment_trigger()
        self.assertEqual(self.rule.trigger_count, initial_count + 1)
        self.assertIsNotNone(self.rule.last_triggered)


class WorkflowScheduleModelTest(TestCase):
    """Test cases for WorkflowSchedule model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='analyst'
        )
        
        self.workflow = Workflow.objects.create(
            name='Test Workflow',
            created_by=self.user
        )
        
        self.schedule = WorkflowSchedule.objects.create(
            workflow=self.workflow,
            name='Test Schedule',
            schedule_type='interval',
            interval_minutes=60,
            created_by=self.user
        )
    
    def test_schedule_creation(self):
        """Test schedule is created correctly."""
        self.assertEqual(self.schedule.name, 'Test Schedule')
        self.assertEqual(self.schedule.schedule_type, 'interval')
        self.assertEqual(self.schedule.interval_minutes, 60)
        self.assertTrue(self.schedule.is_enabled)
        self.assertEqual(self.schedule.run_count, 0)
    
    def test_schedule_str(self):
        """Test schedule string representation."""
        self.assertEqual(str(self.schedule), 'Test Schedule - Test Workflow')
