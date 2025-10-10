"""
SMGI Backend - Monitoring Views
Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
from drf_spectacular.utils import extend_schema

from apps.monitoring.models import (
    LayerSnapshot, ChangeDetectionResult, MonitoringJob,
    MonitoringJobExecution, DataQualityRule, DataQualityResult,
    SystemHealthMetric
)
from apps.monitoring.serializers import (
    LayerSnapshotSerializer, ChangeDetectionResultSerializer,
    MonitoringJobSerializer, MonitoringJobExecutionSerializer,
    DataQualityRuleSerializer, DataQualityResultSerializer,
    SystemHealthMetricSerializer, MonitoringStatisticsSerializer,
    TriggerMonitoringSerializer
)


@extend_schema(tags=['Monitoring'])
class LayerSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Layer Snapshots
    """
    serializer_class = LayerSnapshotSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['layer', 'is_valid']
    ordering = ['-created']
    
    def get_queryset(self):
        queryset = LayerSnapshot.objects.all()
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(created__gte=since)
        
        return queryset.select_related('layer__service')
    
    @extend_schema(summary='Compare Snapshots')
    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        """Compare snapshot with previous one"""
        snapshot = self.get_object()
        comparison = snapshot.compare_with_previous()
        
        if not comparison:
            return Response({
                'message': _('No previous snapshot available for comparison')
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'current_snapshot': str(snapshot.id),
            'previous_snapshot': str(snapshot.get_previous_snapshot().id),
            'comparison': comparison
        })


@extend_schema(tags=['Monitoring'])
class ChangeDetectionResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Change Detection Results
    """
    serializer_class = ChangeDetectionResultSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['has_changes', 'exceeds_threshold', 'processing_status']
    ordering = ['-created']
    
    def get_queryset(self):
        queryset = ChangeDetectionResult.objects.all()
        
        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            severity_filters = {
                'low': Q(confidence_score__lt=0.5) | Q(feature_count_change_percent__lt=5),
                'medium': Q(feature_count_change_percent__gte=5, feature_count_change_percent__lt=25),
                'high': Q(feature_count_change_percent__gte=25, feature_count_change_percent__lt=50),
                'critical': Q(feature_count_change_percent__gte=50)
            }
            if severity in severity_filters:
                queryset = queryset.filter(severity_filters[severity])
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(created__gte=since)
        
        return queryset.select_related('current_snapshot__layer__service')
    
    @extend_schema(summary='Get Recent Significant Changes')
    @action(detail=False, methods=['get'])
    def significant(self, request):
        """Get recent significant changes"""
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        significant_changes = self.get_queryset().filter(
            has_changes=True,
            exceeds_threshold=True,
            created__gte=since
        )
        
        serializer = self.get_serializer(significant_changes, many=True)
        
        return Response({
            'period_hours': hours,
            'count': significant_changes.count(),
            'changes': serializer.data
        })


@extend_schema(tags=['Monitoring Jobs'])
class MonitoringJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Monitoring Jobs
    """
    serializer_class = MonitoringJobSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'status']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def get_queryset(self):
        return MonitoringJob.objects.filter(is_removed=False)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @extend_schema(summary='Execute Monitoring Job')
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute monitoring job immediately"""
        job = self.get_object()
        
        # Trigger job execution
        from apps.monitoring.tasks import process_monitoring_job
        result = process_monitoring_job.delay(str(job.id))
        
        return Response({
            'message': _('Monitoring job execution initiated'),
            'job_id': str(job.id),
            'job_name': job.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Enable/Disable Job')
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle job active status"""
        job = self.get_object()
        job.is_active = not job.is_active
        job.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Job {}').format(
                _('activated') if job.is_active else _('deactivated')
            ),
            'is_active': job.is_active
        })
    
    @extend_schema(summary='Get Job Execution History')
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get execution history for this job"""
        job = self.get_object()
        
        limit = int(request.query_params.get('limit', 50))
        executions = job.executions.all().order_by('-started_at')[:limit]
        
        serializer = MonitoringJobExecutionSerializer(executions, many=True)
        
        return Response({
            'job_name': job.name,
            'execution_count': executions.count(),
            'executions': serializer.data
        })


@extend_schema(tags=['Data Quality'])
class DataQualityRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Data Quality Rules
    """
    serializer_class = DataQualityRuleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'rule_type', 'layer', 'service']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def get_queryset(self):
        return DataQualityRule.objects.filter(is_removed=False)
    
    @extend_schema(summary='Execute Quality Check')
    @action(detail=True, methods=['post'])
    def check(self, request, pk=None):
        """Execute quality check for this rule"""
        rule = self.get_object()
        
        # Trigger quality check task
        from apps.monitoring.tasks import run_data_quality_checks
        result = run_data_quality_checks.delay()
        
        return Response({
            'message': _('Quality check initiated'),
            'rule_id': str(rule.id),
            'rule_name': rule.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Get Quality Check Results')
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get quality check results for this rule"""
        rule = self.get_object()
        
        limit = int(request.query_params.get('limit', 50))
        results = rule.results.all().order_by('-created')[:limit]
        
        serializer = DataQualityResultSerializer(results, many=True)
        
        return Response({
            'rule_name': rule.name,
            'result_count': results.count(),
            'results': serializer.data
        })


@extend_schema(tags=['System Health'])
class SystemHealthMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing System Health Metrics
    """
    queryset = SystemHealthMetric.objects.all()
    serializer_class = SystemHealthMetricSerializer
    permission_classes = [IsAdminUser]
    ordering = ['-created']
    
    @extend_schema(summary='Get Latest Health Status')
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest system health status"""
        latest_metric = SystemHealthMetric.get_latest()
        
        if not latest_metric:
            return Response({
                'message': _('No health metrics available')
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(latest_metric)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Average Metrics')
    @action(detail=False, methods=['get'])
    def average(self, request):
        """Get average metrics for specified period"""
        hours = int(request.query_params.get('hours', 24))
        avg_metrics = SystemHealthMetric.get_average_metrics(hours=hours)
        
        return Response({
            'period_hours': hours,
            'average_metrics': avg_metrics
        })
    
    @extend_schema(summary='Trigger Health Check')
    @action(detail=False, methods=['post'])
    def check(self, request):
        """Trigger immediate system health check"""
        from apps.monitoring.tasks import system_health_check
        result = system_health_check.delay()
        
        return Response({
            'message': _('Health check initiated'),
            'task_id': result.id
        })


@extend_schema(
    tags=['Monitoring'],
    summary='Get Monitoring Statistics',
    responses={200: MonitoringStatisticsSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monitoring_statistics(request):
    """Get overall monitoring statistics"""
    
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Snapshot statistics
    total_snapshots = LayerSnapshot.objects.count()
    snapshots_today = LayerSnapshot.objects.filter(created__gte=today).count()
    
    # Change detection statistics
    total_changes = ChangeDetectionResult.objects.filter(has_changes=True).count()
    changes_today = ChangeDetectionResult.objects.filter(
        has_changes=True,
        created__gte=today
    ).count()
    
    # Job statistics
    active_jobs = MonitoringJob.objects.filter(
        is_active=True,
        is_removed=False
    ).count()
    
    # Layer statistics
    from apps.gis_services.models import SpatialLayer
    layers_monitored = SpatialLayer.objects.filter(
        is_monitored=True,
        is_removed=False
    ).count()
    
    # Average detection time
    avg_detection_time = ChangeDetectionResult.objects.filter(
        processing_status='completed'
    ).aggregate(
        avg_time=Avg('detection_duration_ms')
    )['avg_time'] or 0
    
    # Latest health status
    latest_health = SystemHealthMetric.get_latest()
    health_status = latest_health.overall_health if latest_health else 'unknown'
    
    stats = {
        'total_snapshots': total_snapshots,
        'snapshots_today': snapshots_today,
        'total_changes_detected': total_changes,
        'changes_today': changes_today,
        'active_monitoring_jobs': active_jobs,
        'layers_monitored': layers_monitored,
        'average_detection_time_ms': avg_detection_time,
        'latest_health_status': health_status
    }
    
    serializer = MonitoringStatisticsSerializer(stats)
    return Response(serializer.data)


@extend_schema(
    tags=['Monitoring'],
    summary='Trigger Monitoring',
    request=TriggerMonitoringSerializer,
    responses={200: {'type': 'object'}}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_monitoring(request):
    """Trigger monitoring for specified layers or all active layers"""
    
    serializer = TriggerMonitoringSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    layer_ids = serializer.validated_data.get('layer_ids', [])
    force = serializer.validated_data.get('force', False)
    
    if layer_ids:
        # Monitor specific layers
        from apps.monitoring.tasks import monitor_layer
        task_ids = []
        
        for layer_id in layer_ids:
            result = monitor_layer.delay(str(layer_id))
            task_ids.append(result.id)
        
        return Response({
            'message': _('Monitoring initiated for {} layers').format(len(layer_ids)),
            'layer_count': len(layer_ids),
            'task_ids': task_ids
        })
    else:
        # Monitor all active layers
        from apps.monitoring.tasks import monitor_all_active_layers
        result = monitor_all_active_layers.delay()
        
        return Response({
            'message': _('Monitoring initiated for all active layers'),
            'task_id': result.id
        })


@extend_schema(
    tags=['Monitoring'],
    summary='Get Monitoring Dashboard Data',
    responses={200: {'type': 'object'}}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monitoring_dashboard(request):
    """Get comprehensive dashboard data for monitoring"""
    
    # Get time period from query params
    hours = int(request.query_params.get('hours', 24))
    since = timezone.now() - timedelta(hours=hours)
    
    # Recent changes
    recent_changes = ChangeDetectionResult.objects.filter(
        has_changes=True,
        created__gte=since
    ).order_by('-created')[:10]
    
    # Recent snapshots
    recent_snapshots = LayerSnapshot.objects.filter(
        created__gte=since
    ).order_by('-created')[:10]
    
    # System health
    latest_health = SystemHealthMetric.get_latest()
    
    # Active monitoring jobs
    active_jobs = MonitoringJob.objects.filter(
        is_active=True,
        is_removed=False
    ).count()
    
    # Overdue jobs
    overdue_jobs = MonitoringJob.objects.filter(
        is_active=True,
        next_run__lt=timezone.now(),
        is_removed=False
    ).count()
    
    dashboard_data = {
        'period_hours': hours,
        'recent_changes_count': recent_changes.count(),
        'recent_changes': ChangeDetectionResultSerializer(recent_changes, many=True).data,
        'recent_snapshots_count': recent_snapshots.count(),
        'recent_snapshots': LayerSnapshotSerializer(recent_snapshots, many=True).data,
        'system_health': SystemHealthMetricSerializer(latest_health).data if latest_health else None,
        'active_jobs': active_jobs,
        'overdue_jobs': overdue_jobs,
    }
    
    return Response(dashboard_data)