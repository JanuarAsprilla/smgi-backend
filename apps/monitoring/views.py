"""
Views for Monitoring app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from .models import (
    MonitoringProject,
    Monitor,
    Detection,
    ChangeRecord,
    MonitoringReport,
    Baseline
)
from .serializers import (
    MonitoringProjectSerializer,
    MonitorSerializer,
    DetectionSerializer,
    DetectionDetailSerializer,
    ChangeRecordSerializer,
    MonitoringReportSerializer,
    BaselineSerializer,
    MonitoringStatisticsSerializer,
)
from .filters import (
    MonitoringProjectFilter,
    MonitorFilter,
    DetectionFilter
)
from .tasks import (
    run_monitor_check,
    generate_monitoring_report
)
from apps.users.permissions import IsAnalystOrAbove
import logging

logger = logging.getLogger(__name__)


class MonitoringProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for MonitoringProject model.
    """
    queryset = MonitoringProject.objects.all()
    serializer_class = MonitoringProjectSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MonitoringProjectFilter
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see their own projects
        if not self.request.user.is_staff:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def monitors(self, request, pk=None):
        """Get monitors for this project."""
        project = self.get_object()
        monitors = project.monitors.filter(is_active=True)
        
        page = self.paginate_queryset(monitors)
        if page is not None:
            serializer = MonitorSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = MonitorSerializer(monitors, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def detections(self, request, pk=None):
        """Get detections for this project."""
        project = self.get_object()
        detections = Detection.objects.filter(
            monitor__project=project,
            is_active=True
        ).order_by('-detected_at')
        
        # Apply filters
        severity = request.query_params.get('severity')
        if severity:
            detections = detections.filter(severity=severity)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            detections = detections.filter(status=status_filter)
        
        page = self.paginate_queryset(detections)
        if page is not None:
            serializer = DetectionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DetectionSerializer(detections, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for this project."""
        project = self.get_object()
        
        monitors = project.monitors.filter(is_active=True)
        detections = Detection.objects.filter(
            monitor__project=project,
            is_active=True
        )
        
        stats = {
            'total_monitors': monitors.count(),
            'active_monitors': monitors.filter(status='active').count(),
            'total_detections': detections.count(),
            'new_detections': detections.filter(status='new').count(),
            'confirmed_detections': detections.filter(status='confirmed').count(),
            'detections_by_severity': {
                'low': detections.filter(severity='low').count(),
                'medium': detections.filter(severity='medium').count(),
                'high': detections.filter(severity='high').count(),
                'critical': detections.filter(severity='critical').count(),
            },
            'total_checks': sum(m.check_count for m in monitors),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def generate_report(self, request, pk=None):
        """Generate a monitoring report for this project."""
        project = self.get_object()
        
        report_type = request.data.get('report_type', 'custom')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date y end_date son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Launch async task
        task = generate_monitoring_report.delay(
            project.id,
            report_type,
            start_date,
            end_date
        )
        
        return Response({
            'message': 'Generación de reporte iniciada',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


class MonitorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Monitor model.
    """
    queryset = Monitor.objects.select_related('project', 'agent').all()
    serializer_class = MonitorSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MonitorFilter
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see monitors from their projects
        if not self.request.user.is_staff:
            queryset = queryset.filter(project__created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field and calculate next_check."""
        monitor = serializer.save(created_by=self.request.user)
        
        # Calculate next check
        from .utils import calculate_next_check
        monitor.next_check = calculate_next_check(monitor)
        monitor.save()
    
    def perform_update(self, serializer):
        """Set updated_by field and recalculate next_check."""
        monitor = serializer.save(updated_by=self.request.user)
        
        # Recalculate next check
        from .utils import calculate_next_check
        monitor.next_check = calculate_next_check(monitor)
        monitor.save()
    
    @action(detail=True, methods=['post'])
    def run_check(self, request, pk=None):
        """Run a manual check for this monitor."""
        monitor = self.get_object()
        
        if monitor.status != 'active':
            return Response(
                {'error': 'Solo se pueden ejecutar monitores activos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Launch async task
        task = run_monitor_check.delay(monitor.id)
        
        return Response({
            'message': 'Verificación de monitor iniciada',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a monitor."""
        monitor = self.get_object()
        monitor.status = 'paused'
        monitor.save()
        
        return Response({'message': 'Monitor pausado'})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused monitor."""
        monitor = self.get_object()
        monitor.status = 'active'
        
        # Recalculate next check
        from .utils import calculate_next_check
        monitor.next_check = calculate_next_check(monitor)
        monitor.save()
        
        return Response({'message': 'Monitor reanudado'})
    
    @action(detail=True, methods=['get'])
    def detections(self, request, pk=None):
        """Get detections for this monitor."""
        monitor = self.get_object()
        detections = monitor.detections.filter(is_active=True).order_by('-detected_at')
        
        page = self.paginate_queryset(detections)
        if page is not None:
            serializer = DetectionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DetectionSerializer(detections, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def baselines(self, request, pk=None):
        """Get baselines for this monitor."""
        monitor = self.get_object()
        baselines = monitor.baselines.filter(is_active=True).order_by('-baseline_date')
        serializer = BaselineSerializer(baselines, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_baseline(self, request, pk=None):
        """Create a new baseline for this monitor."""
        monitor = self.get_object()
        
        # Set previous baselines as not current
        monitor.baselines.filter(is_current=True).update(is_current=False)
        
        # Create new baseline
        baseline = Baseline.objects.create(
            monitor=monitor,
            name=request.data.get('name', f'Baseline {timezone.now()}'),
            description=request.data.get('description', ''),
            baseline_date=timezone.now(),
            baseline_data=request.data.get('baseline_data', {}),
            is_current=True,
            created_by=request.user
        )
        
        serializer = BaselineSerializer(baseline)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DetectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Detection model.
    """
    queryset = Detection.objects.select_related('monitor', 'monitor__project').all()
    serializer_class = DetectionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DetectionFilter
    
    def get_serializer_class(self):
        """Return detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return DetectionDetailSerializer
        return DetectionSerializer
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see detections from their projects
        if not self.request.user.is_staff:
            queryset = queryset.filter(monitor__project__created_by=self.request.user)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a detection."""
        detection = self.get_object()
        detection.status = 'confirmed'
        detection.reviewed_by = request.user
        detection.reviewed_at = timezone.now()
        detection.review_notes = request.data.get('notes', '')
        detection.save()
        
        return Response({'message': 'Detección confirmada'})
    
    @action(detail=True, methods=['post'])
    def mark_false_positive(self, request, pk=None):
        """Mark detection as false positive."""
        detection = self.get_object()
        detection.status = 'false_positive'
        detection.reviewed_by = request.user
        detection.reviewed_at = timezone.now()
        detection.review_notes = request.data.get('notes', '')
        detection.save()
        
        return Response({'message': 'Detección marcada como falso positivo'})
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a detection."""
        detection = self.get_object()
        detection.status = 'resolved'
        detection.reviewed_by = request.user
        detection.reviewed_at = timezone.now()
        detection.review_notes = request.data.get('notes', '')
        detection.save()
        
        return Response({'message': 'Detección resuelta'})
    
    @action(detail=True, methods=['post'])
    def ignore(self, request, pk=None):
        """Ignore a detection."""
        detection = self.get_object()
        detection.status = 'ignored'
        detection.reviewed_by = request.user
        detection.reviewed_at = timezone.now()
        detection.review_notes = request.data.get('notes', '')
        detection.save()
        
        return Response({'message': 'Detección ignorada'})
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard data with recent detections."""
        queryset = self.get_queryset()
        
        # Recent detections
        recent = queryset.order_by('-detected_at')[:10]
        
        # Statistics
        stats = {
            'total': queryset.count(),
            'new': queryset.filter(status='new').count(),
            'confirmed': queryset.filter(status='confirmed').count(),
            'by_severity': {
                'critical': queryset.filter(severity='critical').count(),
                'high': queryset.filter(severity='high').count(),
                'medium': queryset.filter(severity='medium').count(),
                'low': queryset.filter(severity='low').count(),
            }
        }
        
        serializer = self.get_serializer(recent, many=True)
        
        return Response({
            'statistics': stats,
            'recent_detections': serializer.data
        })


class ChangeRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ChangeRecord model (read-only).
    """
    queryset = ChangeRecord.objects.select_related('detection', 'layer').all()
    serializer_class = ChangeRecordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see changes from their projects
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                detection__monitor__project__created_by=self.request.user
            )
        
        return queryset


class MonitoringReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for MonitoringReport model (read-only).
    """
    queryset = MonitoringReport.objects.select_related('project').all()
    serializer_class = MonitoringReportSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see reports from their projects
        if not self.request.user.is_staff:
            queryset = queryset.filter(project__created_by=self.request.user)
        
        return queryset


class BaselineViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Baseline model.
    """
    queryset = Baseline.objects.select_related('monitor').all()
    serializer_class = BaselineSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see baselines from their monitors
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                monitor__project__created_by=self.request.user
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_as_current(self, request, pk=None):
        """Set this baseline as current."""
        baseline = self.get_object()
        
        # Unset other current baselines for this monitor
        baseline.monitor.baselines.filter(is_current=True).update(is_current=False)
        
        # Set this as current
        baseline.is_current = True
        baseline.save()
        
        return Response({'message': 'Baseline establecido como actual'})


class MonitoringStatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet for monitoring statistics.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get general monitoring statistics."""
        # Filter by user if not staff
        if request.user.is_staff:
            projects = MonitoringProject.objects.filter(is_active=True)
            monitors = Monitor.objects.filter(is_active=True)
            detections = Detection.objects.filter(is_active=True)
        else:
            projects = MonitoringProject.objects.filter(
                created_by=request.user,
                is_active=True
            )
            monitors = Monitor.objects.filter(
                project__created_by=request.user,
                is_active=True
            )
            detections = Detection.objects.filter(
                monitor__project__created_by=request.user,
                is_active=True
            )
        
        # Calculate statistics
        stats = {
            'total_projects': projects.count(),
            'active_monitors': monitors.filter(status='active').count(),
            'total_detections': detections.count(),
            'detections_by_severity': {
                'critical': detections.filter(severity='critical').count(),
                'high': detections.filter(severity='high').count(),
                'medium': detections.filter(severity='medium').count(),
                'low': detections.filter(severity='low').count(),
            },
            'detections_by_status': {
                'new': detections.filter(status='new').count(),
                'confirmed': detections.filter(status='confirmed').count(),
                'false_positive': detections.filter(status='false_positive').count(),
                'resolved': detections.filter(status='resolved').count(),
                'ignored': detections.filter(status='ignored').count(),
            },
            'recent_detections': [],
            'top_monitors': []
        }
        
        # Recent detections
        recent = detections.order_by('-detected_at')[:5]
        stats['recent_detections'] = [
            {
                'id': d.id,
                'title': d.title,
                'severity': d.severity,
                'detected_at': d.detected_at
            }
            for d in recent
        ]
        
        # Top monitors by detection count
        top_monitors = monitors.annotate(
            det_count=Count('detections')
        ).order_by('-det_count')[:5]
        
        stats['top_monitors'] = [
            {
                'id': m.id,
                'name': m.name,
                'detection_count': m.det_count
            }
            for m in top_monitors
        ]
        
        serializer = MonitoringStatisticsSerializer(stats)
        return Response(serializer.data)
