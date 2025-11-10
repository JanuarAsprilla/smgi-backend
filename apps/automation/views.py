"""
Views for Automation app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from .models import (
    Workflow,
    WorkflowTask,
    WorkflowExecution,
    TaskExecution,
    AutomationRule,
    WorkflowSchedule
)
from .serializers import (
    WorkflowSerializer,
    WorkflowDetailSerializer,
    WorkflowTaskSerializer,
    WorkflowExecutionSerializer,
    WorkflowExecutionDetailSerializer,
    TaskExecutionSerializer,
    AutomationRuleSerializer,
    WorkflowScheduleSerializer,
    AutomationStatisticsSerializer,
)
from .filters import WorkflowFilter, WorkflowExecutionFilter, AutomationRuleFilter
from .tasks import execute_workflow
from apps.users.permissions import IsAnalystOrAbove, IsDeveloperOrAbove
import logging

logger = logging.getLogger(__name__)


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Workflow model.
    """
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [IsAuthenticated, IsDeveloperOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_class = WorkflowFilter
    
    def get_serializer_class(self):
        """Return detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return WorkflowDetailSerializer
        return WorkflowSerializer
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see their own workflows
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute a workflow manually."""
        workflow = self.get_object()
        
        if workflow.status != 'active':
            return Response(
                {'error': 'Solo se pueden ejecutar workflows activos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get input data
        input_data = request.data.get('input_data', {})
        
        # Create execution
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            input_data=input_data,
            trigger_source='manual',
            trigger_data={'user': request.user.username},
            created_by=request.user
        )
        
        # Launch async task
        task = execute_workflow.delay(execution.id)
        execution.task_id = task.id
        execution.save()
        
        return Response({
            'message': 'Ejecución de workflow iniciada',
            'execution_id': execution.id,
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get executions for this workflow."""
        workflow = self.get_object()
        executions = workflow.executions.order_by('-created_at')
        
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = WorkflowExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = WorkflowExecutionSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a workflow."""
        workflow = self.get_object()
        workflow.status = 'active'
        workflow.save()
        
        return Response({'message': 'Workflow activado'})
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a workflow."""
        workflow = self.get_object()
        workflow.status = 'paused'
        workflow.save()
        
        return Response({'message': 'Workflow pausado'})
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a workflow."""
        workflow = self.get_object()
        
        # Create a copy
        workflow_copy = Workflow.objects.create(
            name=f"{workflow.name} (Copia)",
            description=workflow.description,
            status='draft',
            workflow_definition=workflow.workflow_definition,
            trigger_type=workflow.trigger_type,
            trigger_config=workflow.trigger_config,
            timeout_minutes=workflow.timeout_minutes,
            retry_count=workflow.retry_count,
            tags=workflow.tags,
            metadata=workflow.metadata,
            created_by=request.user
        )
        
        # Clone tasks
        for task in workflow.tasks.all():
            WorkflowTask.objects.create(
                workflow=workflow_copy,
                name=task.name,
                description=task.description,
                task_type=task.task_type,
                configuration=task.configuration,
                order=task.order,
                timeout_minutes=task.timeout_minutes,
                retry_on_failure=task.retry_on_failure,
                continue_on_failure=task.continue_on_failure,
                created_by=request.user
            )
        
        serializer = WorkflowDetailSerializer(workflow_copy)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WorkflowTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for WorkflowTask model.
    """
    queryset = WorkflowTask.objects.all()
    serializer_class = WorkflowTaskSerializer
    permission_classes = [IsAuthenticated, IsDeveloperOrAbove]
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see tasks from their workflows
        if not self.request.user.is_staff:
            queryset = queryset.filter(workflow__created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)


class WorkflowExecutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for WorkflowExecution model.
    """
    queryset = WorkflowExecution.objects.select_related('workflow').all()
    serializer_class = WorkflowExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = WorkflowExecutionFilter
    
    def get_serializer_class(self):
        """Return detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return WorkflowExecutionDetailSerializer
        return WorkflowExecutionSerializer
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see executions from their workflows
        if not self.request.user.is_staff:
            queryset = queryset.filter(workflow__created_by=self.request.user)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running execution."""
        execution = self.get_object()
        
        if execution.status not in ['pending', 'running']:
            return Response(
                {'error': 'Solo se pueden cancelar ejecuciones pendientes o en ejecución'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel Celery task
        if execution.task_id:
            from celery import current_app
            current_app.control.revoke(execution.task_id, terminate=True)
        
        execution.status = 'cancelled'
        execution.completed_at = timezone.now()
        execution.save()
        
        return Response({'message': 'Ejecución cancelada'})
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed execution."""
        execution = self.get_object()
        
        if execution.status != 'failed':
            return Response(
                {'error': 'Solo se pueden reintentar ejecuciones fallidas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new execution
        new_execution = WorkflowExecution.objects.create(
            workflow=execution.workflow,
            input_data=execution.input_data,
            trigger_source='retry',
            trigger_data={'original_execution_id': execution.id},
            created_by=request.user
        )
        
        # Launch async task
        task = execute_workflow.delay(new_execution.id)
        new_execution.task_id = task.id
        new_execution.save()
        
        return Response({
            'message': 'Ejecución reiniciada',
            'execution_id': new_execution.id,
            'task_id': task.id
        }, status=status.HTTP_201_CREATED)


class AutomationRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AutomationRule model.
    """
    queryset = AutomationRule.objects.select_related('workflow').all()
    serializer_class = AutomationRuleSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AutomationRuleFilter
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see their own rules
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a rule."""
        rule = self.get_object()
        rule.status = 'active'
        rule.save()
        
        return Response({'message': 'Regla activada'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a rule."""
        rule = self.get_object()
        rule.status = 'inactive'
        rule.save()
        
        return Response({'message': 'Regla desactivada'})


class WorkflowScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for WorkflowSchedule model.
    """
    queryset = WorkflowSchedule.objects.select_related('workflow').all()
    serializer_class = WorkflowScheduleSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see their own schedules
        if not self.request.user.is_staff:
            queryset = queryset.filter(workflow__created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field and calculate next_run."""
        schedule = serializer.save(created_by=self.request.user)
        
        # Calculate next run
        from .utils import calculate_next_run
        schedule.next_run = calculate_next_run(schedule)
        schedule.save()
    
    def perform_update(self, serializer):
        """Set updated_by field and recalculate next_run."""
        schedule = serializer.save(updated_by=self.request.user)
        
        # Recalculate next run
        from .utils import calculate_next_run
        schedule.next_run = calculate_next_run(schedule)
        schedule.save()
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable a schedule."""
        schedule = self.get_object()
        schedule.is_enabled = True
        schedule.save()
        
        return Response({'message': 'Programación habilitada'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a schedule."""
        schedule = self.get_object()
        schedule.is_enabled = False
        schedule.save()
        
        return Response({'message': 'Programación deshabilitada'})
    
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Execute schedule immediately."""
        schedule = self.get_object()
        
        # Create execution
        execution = WorkflowExecution.objects.create(
            workflow=schedule.workflow,
            input_data=schedule.input_data,
            trigger_source='schedule_manual',
            trigger_data={'schedule_id': schedule.id},
            created_by=request.user
        )
        
        # Launch async task
        task = execute_workflow.delay(execution.id)
        execution.task_id = task.id
        execution.save()
        
        return Response({
            'message': 'Ejecución iniciada',
            'execution_id': execution.id,
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


class AutomationStatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet for automation statistics.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get general automation statistics."""
        # Filter by user if not staff
        if request.user.is_staff:
            workflows = Workflow.objects.filter(is_active=True)
            executions = WorkflowExecution.objects.all()
        else:
            workflows = Workflow.objects.filter(
                created_by=request.user,
                is_active=True
            )
            executions = WorkflowExecution.objects.filter(
                workflow__created_by=request.user
            )
        
        # Calculate statistics
        total_executions = executions.count()
        successful = executions.filter(status='success').count()
        
        avg_success_rate = 0.0
        if total_executions > 0:
            avg_success_rate = (successful / total_executions) * 100
        
        stats = {
            'total_workflows': workflows.count(),
            'active_workflows': workflows.filter(status='active').count(),
            'total_executions': total_executions,
            'running_executions': executions.filter(status='running').count(),
            'successful_executions': successful,
            'failed_executions': executions.filter(status='failed').count(),
            'average_success_rate': round(avg_success_rate, 2),
            'recent_executions': [],
            'top_workflows': []
        }
        
        # Recent executions
        recent = executions.order_by('-created_at')[:5]
        stats['recent_executions'] = [
            {
                'id': e.id,
                'workflow_name': e.workflow.name,
                'status': e.status,
                'created_at': e.created_at
            }
            for e in recent
        ]
        
        # Top workflows by execution count
        top_workflows = workflows.annotate(
            exec_count=Count('executions')
        ).order_by('-exec_count')[:5]
        
        stats['top_workflows'] = [
            {
                'id': w.id,
                'name': w.name,
                'execution_count': w.exec_count
            }
            for w in top_workflows
        ]
        
        serializer = AutomationStatisticsSerializer(stats)
        return Response(serializer.data)
