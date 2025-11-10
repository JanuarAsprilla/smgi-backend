"""
Views for Agents app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from .models import (
    AgentCategory,
    Agent,
    AgentExecution,
    AgentSchedule,
    AgentRating,
    AgentTemplate
)
from .serializers import (
    AgentCategorySerializer,
    AgentSerializer,
    AgentDetailSerializer,
    AgentCreateSerializer,
    AgentExecutionSerializer,
    AgentExecutionCreateSerializer,
    AgentScheduleSerializer,
    AgentRatingSerializer,
    AgentRatingCreateSerializer,
    AgentTemplateSerializer,
    AgentStatisticsSerializer,
)
from .filters import AgentFilter, AgentExecutionFilter, AgentScheduleFilter
from .tasks import execute_agent, schedule_agent_execution
from apps.users.permissions import IsAnalystOrAbove, IsDeveloperOrAbove
import logging

logger = logging.getLogger(__name__)


class AgentCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AgentCategory model.
    """
    queryset = AgentCategory.objects.all()
    serializer_class = AgentCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Allow public read access for list and retrieve."""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsDeveloperOrAbove()]
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)


class AgentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Agent model.
    Provides CRUD operations for agents.
    """
    queryset = Agent.objects.select_related('category', 'created_by').all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AgentFilter
    
    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return AgentCreateSerializer
        elif self.action == 'retrieve':
            return AgentDetailSerializer
        return AgentSerializer
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Public marketplace view
        if self.action == 'marketplace':
            return queryset.filter(is_public=True, status='published', is_active=True)
        
        # Non-developer users only see published public agents or their own
        if not self.request.user.is_staff and self.request.user.role != 'developer':
            queryset = queryset.filter(
                Q(is_public=True, status='published') | Q(created_by=self.request.user)
            )
        
        return queryset
    
    def get_permissions(self):
        """Define permissions based on action."""
        if self.action in ['list', 'retrieve', 'marketplace']:
            return [AllowAny()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsDeveloperOrAbove()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute an agent."""
        agent = self.get_object()
        
        # Validate agent status
        if agent.status != 'published':
            return Response(
                {'error': 'Solo se pueden ejecutar agentes publicados.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create execution serializer
        execution_data = {
            'agent': agent.id,
            'name': request.data.get('name', f'Ejecución de {agent.name}'),
            'input_layers': request.data.get('input_layers', []),
            'input_datasets': request.data.get('input_datasets', []),
            'parameters': request.data.get('parameters', {}),
        }
        
        serializer = AgentExecutionCreateSerializer(data=execution_data)
        serializer.is_valid(raise_exception=True)
        execution = serializer.save(created_by=request.user)
        
        # Launch async task
        task = execute_agent.delay(execution.id)
        execution.task_id = task.id
        execution.save()
        
        return Response({
            'message': 'Ejecución iniciada',
            'execution_id': execution.id,
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get executions for this agent."""
        agent = self.get_object()
        executions = AgentExecution.objects.filter(agent=agent).order_by('-created_at')
        
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = AgentExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = AgentExecutionSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an agent."""
        agent = self.get_object()
        
        # Check permissions
        if agent.created_by != request.user and not request.user.is_staff:
            return Response(
                {'error': 'No tienes permiso para publicar este agente.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        agent.status = 'published'
        agent.save()
        
        return Response({
            'message': 'Agente publicado exitosamente',
            'status': agent.status
        })
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive an agent."""
        agent = self.get_object()
        
        # Check permissions
        if agent.created_by != request.user and not request.user.is_staff:
            return Response(
                {'error': 'No tienes permiso para archivar este agente.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        agent.status = 'archived'
        agent.save()
        
        return Response({
            'message': 'Agente archivado exitosamente',
            'status': agent.status
        })
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone an agent."""
        agent = self.get_object()
        
        # Create a copy
        agent_copy = Agent.objects.create(
            name=f"{agent.name} (Copia)",
            description=agent.description,
            category=agent.category,
            agent_type=agent.agent_type,
            version='1.0.0',
            status='draft',
            code=agent.code,
            requirements=agent.requirements,
            parameters_schema=agent.parameters_schema,
            default_parameters=agent.default_parameters,
            tags=agent.tags,
            metadata=agent.metadata,
            created_by=request.user,
            updated_by=request.user
        )
        
        serializer = AgentDetailSerializer(agent_copy)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Rate an agent."""
        agent = self.get_object()
        
        serializer = AgentRatingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create or update rating
        rating, created = AgentRating.objects.update_or_create(
            agent=agent,
            user=request.user,
            defaults={
                'rating': serializer.validated_data['rating'],
                'comment': serializer.validated_data.get('comment', '')
            }
        )
        
        # Update agent average rating
        avg_rating = agent.ratings.aggregate(Avg('rating'))['rating__avg']
        agent.rating = round(avg_rating, 2) if avg_rating else 0.0
        agent.save()
        
        return Response({
            'message': 'Calificación guardada exitosamente',
            'rating': rating.rating,
            'average_rating': agent.rating
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def ratings(self, request, pk=None):
        """Get ratings for this agent."""
        agent = self.get_object()
        ratings = agent.ratings.all().order_by('-created_at')
        serializer = AgentRatingSerializer(ratings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def marketplace(self, request):
        """Get agents for marketplace (public and published)."""
        queryset = self.get_queryset()
        
        # Apply filters
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        agent_type = request.query_params.get('type')
        if agent_type:
            queryset = queryset.filter(agent_type=agent_type)
        
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        verified_only = request.query_params.get('verified', 'false').lower() == 'true'
        if verified_only:
            queryset = queryset.filter(is_verified=True)
        
        # Sorting
        sort_by = request.query_params.get('sort', '-rating')
        queryset = queryset.order_by(sort_by)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get general statistics about agents."""
        total_agents = Agent.objects.filter(is_active=True).count()
        public_agents = Agent.objects.filter(is_public=True, status='published', is_active=True).count()
        verified_agents = Agent.objects.filter(is_verified=True, is_active=True).count()
        
        total_executions = AgentExecution.objects.count()
        successful_executions = AgentExecution.objects.filter(status='success').count()
        failed_executions = AgentExecution.objects.filter(status='failed').count()
        
        avg_success_rate = 0.0
        if total_executions > 0:
            avg_success_rate = (successful_executions / total_executions) * 100
        
        # Most used agents
        most_used = Agent.objects.filter(is_active=True).order_by('-execution_count')[:5]
        most_used_data = [{'name': a.name, 'executions': a.execution_count} for a in most_used]
        
        # Executions by type
        executions_by_type = {}
        for choice in Agent.AgentType.choices:
            count = AgentExecution.objects.filter(agent__agent_type=choice[0]).count()
            executions_by_type[choice[1]] = count
        
        stats = {
            'total_agents': total_agents,
            'public_agents': public_agents,
            'verified_agents': verified_agents,
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'average_success_rate': round(avg_success_rate, 2),
            'most_used_agents': most_used_data,
            'executions_by_type': executions_by_type,
        }
        
        serializer = AgentStatisticsSerializer(stats)
        return Response(serializer.data)


class AgentExecutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AgentExecution model.
    """
    queryset = AgentExecution.objects.select_related('agent', 'created_by').all()
    serializer_class = AgentExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AgentExecutionFilter
    
    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return AgentExecutionCreateSerializer
        return AgentExecutionSerializer
    
    def get_queryset(self):
        """Filter queryset to show only user's executions or public."""
        queryset = super().get_queryset()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create and execute agent."""
        execution = serializer.save(created_by=self.request.user)
        
        # Launch async task
        task = execute_agent.delay(execution.id)
        execution.task_id = task.id
        execution.save()
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running execution."""
        execution = self.get_object()
        
        if execution.status not in ['pending', 'running']:
            return Response(
                {'error': 'Solo se pueden cancelar ejecuciones pendientes o en ejecución.'},
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
                {'error': 'Solo se pueden reintentar ejecuciones fallidas.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new execution
        new_execution = AgentExecution.objects.create(
            agent=execution.agent,
            name=f"{execution.name} (Reintento)",
            parameters=execution.parameters,
            created_by=request.user
        )
        
        # Copy input layers and datasets
        new_execution.input_layers.set(execution.input_layers.all())
        new_execution.input_datasets.set(execution.input_datasets.all())
        
        # Launch async task
        task = execute_agent.delay(new_execution.id)
        new_execution.task_id = task.id
        new_execution.save()
        
        return Response({
            'message': 'Ejecución reiniciada',
            'execution_id': new_execution.id,
            'task_id': task.id
        }, status=status.HTTP_201_CREATED)


class AgentScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AgentSchedule model.
    """
    queryset = AgentSchedule.objects.select_related('agent', 'created_by').all()
    serializer_class = AgentScheduleSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AgentScheduleFilter
    
    def get_queryset(self):
        """Filter queryset to show only user's schedules or all for staff."""
        queryset = super().get_queryset()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create schedule and calculate next run."""
        schedule = serializer.save(created_by=self.request.user)
        
        # Calculate next run
        from .utils import calculate_next_run
        schedule.next_run = calculate_next_run(schedule)
        schedule.save()
    
    def perform_update(self, serializer):
        """Update schedule and recalculate next run."""
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
        execution = AgentExecution.objects.create(
            agent=schedule.agent,
            name=f"{schedule.name} (Manual)",
            parameters=schedule.parameters,
            created_by=request.user
        )
        
        # Copy input layers and datasets
        execution.input_layers.set(schedule.input_layers.all())
        execution.input_datasets.set(schedule.input_datasets.all())
        
        # Launch async task
        task = execute_agent.delay(execution.id)
        execution.task_id = task.id
        execution.save()
        
        return Response({
            'message': 'Ejecución iniciada',
            'execution_id': execution.id,
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


class AgentTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AgentTemplate model (read-only for users).
    """
    queryset = AgentTemplate.objects.filter(is_active=True)
    serializer_class = AgentTemplateSerializer
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['post'])
    def use(self, request, pk=None):
        """Create a new agent from this template."""
        template = self.get_object()
        
        # Create agent from template
        agent = Agent.objects.create(
            name=request.data.get('name', template.name),
            description=request.data.get('description', template.description),
            category=template.category,
            agent_type=template.agent_type,
            code=template.code_template,
            parameters_schema=template.parameters_schema,
            default_parameters=template.default_parameters,
            tags=template.tags,
            status='draft',
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Increment usage count
        template.usage_count += 1
        template.save()
        
        serializer = AgentDetailSerializer(agent)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured templates."""
        templates = self.get_queryset().filter(is_featured=True)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)
