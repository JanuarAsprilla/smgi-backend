# apps/reports/views.py
"""
SMGI Backend - Reports Views
Sistema de Monitoreo Geoespacial Inteligente
Vistas para el sistema de generación de informes
"""
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Avg, Q, F, Sum
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.reports.models import (
    Report, ReportTemplate, GeneratedReport, ReportSchedule, ReportExecution,
    ReportParameter, ReportSection, ReportType, ReportFormat, ReportStatus
)
from apps.reports.serializers import (
    ReportListSerializer, ReportDetailSerializer, ReportCreateSerializer,
    ReportTemplateSerializer, GeneratedReportSerializer,
    ReportScheduleSerializer, ReportExecutionSerializer,
    ReportStatisticsSerializer, TriggerReportSerializer,
    DownloadGeneratedReportSerializer, RegenerateReportSerializer,
    ReportScheduleToggleSerializer, RunReportNowSerializer
)
from apps.reports.tasks import (
    generate_report, generate_monitoring_report, generate_alerts_report,
    generate_performance_report, generate_daily_summary_report,
    schedule_report_generation, unschedule_report_generation,
    run_scheduled_report_now
)
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert


@extend_schema(tags=['Reports'])
class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reports
    """
    permission_classes = [IsAuthenticated]
    filterset_fields = [
        'report_type', 'format_type', 'status', 'service', 'layer',
        'monitoring_job', 'alert', 'is_scheduled'
    ]
    search_fields = ['name', 'description', 'report_id']
    ordering_fields = ['name', 'created', 'last_generated', 'generation_count']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = Report.objects.filter(is_removed=False)
        
        # Filter by created by user
        created_by_me = self.request.query_params.get('created_by_me')
        if created_by_me == 'true':
            queryset = queryset.filter(created_by=self.request.user)
        
        # Filter by assigned user (if report has a related field for assignment)
        # assigned_to_me = self.request.query_params.get('assigned_to_me')
        # if assigned_to_me == 'true':
        #     queryset = queryset.filter(assigned_to=self.request.user)
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(created__gte=since)
        
        return queryset.select_related(
            'service', 'layer', 'monitoring_job', 'alert',
            'template', 'created_by'
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReportListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ReportCreateSerializer
        return ReportDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary='Generate Report',
        request=TriggerReportSerializer,
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate this report"""
        report = self.get_object()
        serializer = TriggerReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        parameters = serializer.validated_data.get('parameters', {})
        force = serializer.validated_data.get('force', False)
        
        # Trigger report generation task
        result = generate_report.delay(str(report.id), parameters, force)
        
        return Response({
            'message': _('Report generation initiated'),
            'report_id': str(report.id),
            'report_name': report.name,
            'task_id': result.id
        })
    
    @extend_schema(
        summary='Download Generated Report',
        request=DownloadGeneratedReportSerializer,
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Download a generated report"""
        report = self.get_object()
        serializer = DownloadGeneratedReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        generated_report_id = serializer.validated_data.get('generated_report_id')
        
        if generated_report_id:
            try:
                generated_report = GeneratedReport.objects.get(
                    id=generated_report_id,
                    report=report,
                    is_removed=False
                )
            except GeneratedReport.DoesNotExist:
                return Response({
                    'error': _('Generated report not found')
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get the latest generated report
            generated_report = report.generated_reports.filter(
                is_removed=False
            ).order_by('-created').first()
        
        if not generated_report or not generated_report.is_complete:
            return Response({
                'error': _('No complete generated report available')
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Redirect to download URL or return file content
        # For now, return a download URL
        download_url = request.build_absolute_uri(generated_report.file.url)
        return Response({
            'message': _('Download initiated'),
            'report_id': str(report.id),
            'generated_report_id': str(generated_report.id),
            'download_url': download_url
        })
    
    @extend_schema(
        summary='Schedule Report Generation',
        request=ReportScheduleSerializer,
        responses={200: ReportScheduleSerializer}
    )
    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        """Schedule automatic generation of this report"""
        report = self.get_object()
        serializer = ReportScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create schedule
        schedule_data = serializer.validated_data
        schedule_data['report'] = report
        schedule_data['created_by'] = request.user
        
        schedule = ReportSchedule.objects.create(**schedule_data)
        
        return Response({
            'message': _('Report scheduled successfully'),
            'schedule_id': str(schedule.id),
            'report_name': report.name,
            'next_run': schedule.next_run.isoformat() if schedule.next_run else None
        })
    
    @extend_schema(
        summary='Unschedule Report Generation',
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['post'])
    def unschedule(self, request, pk=None):
        """Unschedule automatic generation of this report"""
        report = self.get_object()
        
        # Get active schedules for this report
        schedules = report.schedules.filter(is_active=True, is_removed=False)
        
        if not schedules.exists():
            return Response({
                'message': _('No active schedules found for this report')
            })
        
        # Deactivate all active schedules
        schedules.update(is_active=False)
        
        return Response({
            'message': _('Report unscheduled successfully'),
            'report_name': report.name,
            'schedules_deactivated': schedules.count()
        })
    
    @extend_schema(
        summary='Run Report Now',
        request=RunReportNowSerializer,
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Run this report immediately"""
        report = self.get_object()
        serializer = RunReportNowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        parameters = serializer.validated_data.get('parameters', {})
        
        # Trigger immediate report generation task
        result = generate_report.delay(str(report.id), parameters, force=True)
        
        return Response({
            'message': _('Report generation initiated immediately'),
            'report_id': str(report.id),
            'report_name': report.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Get Report Statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get report statistics"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_reports = queryset.filter(created__gte=since)
        
        # Basic counts
        total_reports = recent_reports.count()
        active_schedules = recent_reports.filter(is_scheduled=True).count()
        generated_today = recent_reports.filter(
            last_generated__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Reports by type
        by_type = recent_reports.values('report_type').annotate(count=Count('id'))
        reports_by_type = {item['report_type']: item['count'] for item in by_type}
        
        # Reports by format
        by_format = recent_reports.values('format_type').annotate(count=Count('id'))
        reports_by_format = {item['format_type']: item['count'] for item in by_format}
        
        # Top services with reports
        top_services = recent_reports.filter(
            service__isnull=False
        ).values(
            'service__name'
        ).annotate(
            report_count=Count('id')
        ).order_by('-report_count')[:5]
        
        top_services_list = [
            {'service': item['service__name'], 'count': item['report_count']}
            for item in top_services
        ]
        
        stats = {
            'total_reports': total_reports,
            'active_schedules': active_schedules,
            'generated_today': generated_today,
            'reports_by_type': reports_by_type,
            'reports_by_format': reports_by_format,
            'top_services_with_reports': top_services_list
        }
        
        serializer = ReportStatisticsSerializer(stats)
        return Response(serializer.data)
    
    @extend_schema(summary='Get My Reports')
    @action(detail=False, methods=['get'])
    def my_reports(self, request):
        """Get reports created by current user"""
        my_reports = self.get_queryset().filter(created_by=request.user)
        
        serializer = ReportListSerializer(my_reports, many=True)
        
        return Response({
            'count': my_reports.count(),
            'reports': serializer.data
        })
    
    @extend_schema(summary='Get Active Schedules')
    @action(detail=False, methods=['get'])
    def active_schedules(self, request):
        """Get all active report schedules"""
        active_schedules = ReportSchedule.objects.filter(
            is_active=True,
            is_removed=False
        ).select_related('report', 'created_by')
        
        serializer = ReportScheduleSerializer(active_schedules, many=True)
        
        return Response({
            'count': active_schedules.count(),
            'schedules': serializer.data
        })
    
    @extend_schema(summary='Get Recent Executions')
    @action(detail=False, methods=['get'])
    def recent_executions(self, request):
        """Get recent report executions"""
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)
        
        recent_executions = ReportExecution.objects.filter(
            created__gte=since,
            is_removed=False
        ).select_related('schedule__report').order_by('-created')[:50]
        
        serializer = ReportExecutionSerializer(recent_executions, many=True)
        
        return Response({
            'count': recent_executions.count(),
            'executions': serializer.data
        })


@extend_schema(tags=['Report Templates'])
class ReportTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing report templates
    """
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['template_type', 'format_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created', 'template_type', 'format_type']
    ordering = ['name']
    parser_classes = (MultiPartParser, FormParser) # To handle file uploads
    
    def get_queryset(self):
        return ReportTemplate.objects.filter(is_removed=False)
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @extend_schema(summary='Preview Template')
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview the report template"""
        template = self.get_object()
        
        # Return template content (file or raw)
        content = template.template_content
        if template.template_file:
            # Read file content
            try:
                content = template.template_file.read().decode('utf-8')
            except Exception as e:
                content = f"Error reading template file: {e}"
        
        return Response({
            'template_id': str(template.id),
            'template_name': template.name,
            'template_type': template.get_template_type_display(),
            'format_type': template.get_format_type_display(),
            'content': content
        })
    
    @extend_schema(summary='Validate Template')
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate the report template content"""
        template = self.get_object()
        
        # Simple validation: Check if content is not empty
        content = template.template_content
        if template.template_file:
            try:
                content = template.template_file.read().decode('utf-8')
            except Exception as e:
                return Response({
                    'valid': False,
                    'error': f"Error reading template file: {e}"
                })
        
        is_valid = bool(content.strip())
        message = "Template is valid" if is_valid else "Template is empty"
        
        return Response({
            'valid': is_valid,
            'message': message,
            'template_id': str(template.id),
            'template_name': template.name
        })


@extend_schema(tags=['Generated Reports'])
class GeneratedReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing generated reports
    """
    serializer_class = GeneratedReportSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = [
        'report', 'format_type', 'status', 'generated_by'
    ]
    search_fields = ['report__name', 'report_id']
    ordering_fields = [
        'created', 'format_type', 'status', 'file_size_bytes',
        'generation_duration_ms', 'record_count'
    ]
    ordering = ['-created']
    
    def get_queryset(self):
        return GeneratedReport.objects.filter(is_removed=False).select_related(
            'report', 'generated_by'
        )
    
    @extend_schema(
        summary='Download Generated Report File',
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the generated report file"""
        generated_report = self.get_object()
        
        if not generated_report.is_complete or not generated_report.file:
            return Response({
                'error': _('Generated report is not complete or file is missing')
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Serve the file
        try:
            response = HttpResponse(
                generated_report.file.read(),
                content_type=generated_report.get_format_type_display()
            )
            response['Content-Disposition'] = f'attachment; filename="{generated_report.file_name}"'
            return response
        except Exception as e:
            return Response({
                'error': _('Error serving file')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary='Regenerate Report',
        request=RegenerateReportSerializer,
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['post'])
    def re_generate(self, request, pk=None):
        """Regenerate this generated report"""
        generated_report = self.get_object()
        serializer = RegenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        force = serializer.validated_data.get('force', True) # Force regeneration by default
        
        # Trigger report generation task with original parameters
        result = generate_report.delay(
            str(generated_report.report.id),
            generated_report.parameters_used,
            force=force
        )
        
        return Response({
            'message': _('Report regeneration initiated'),
            'report_id': str(generated_report.report.id),
            'generated_report_id': str(generated_report.id),
            'task_id': result.id
        })
    
    @extend_schema(summary='Get Report Details')
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Get detailed information about this generated report"""
        generated_report = self.get_object()
        
        serializer = GeneratedReportSerializer(generated_report)
        
        return Response({
            'generated_report': serializer.data
        })


@extend_schema(tags=['Report Schedules'])
class ReportScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing report schedules
    """
    serializer_class = ReportScheduleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'report', 'created_by']
    search_fields = ['name', 'description', 'report__name']
    ordering_fields = ['name', 'created', 'last_run', 'next_run']
    ordering = ['name']
    
    def get_queryset(self):
        return ReportSchedule.objects.filter(is_removed=False).select_related(
            'report', 'created_by'
        )
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary='Enable/Disable Schedule',
        request=ReportScheduleToggleSerializer,
        responses={200: ReportScheduleSerializer}
    )
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Enable or disable this report schedule"""
        schedule = self.get_object()
        serializer = ReportScheduleToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        is_active = serializer.validated_data.get('is_active', not schedule.is_active)
        schedule.is_active = is_active
        schedule.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Schedule {}').format(
                _('enabled') if schedule.is_active else _('disabled')
            ),
            'is_active': schedule.is_active,
            'schedule_id': str(schedule.id),
            'report_name': schedule.report.name
        })
    
    @extend_schema(
        summary='Run Schedule Now',
        request=RunReportNowSerializer,
        responses={200: {'type': 'object'}}
    )
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Run this scheduled report immediately"""
        schedule = self.get_object()
        serializer = RunReportNowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Trigger immediate scheduled report run task
        result = run_scheduled_report_now.delay(str(schedule.id))
        
        return Response({
            'message': _('Scheduled report run initiated'),
            'schedule_id': str(schedule.id),
            'report_name': schedule.report.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Get Schedule Executions')
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get execution history for this schedule"""
        schedule = self.get_object()
        
        limit = int(request.query_params.get('limit', 50))
        executions = schedule.executions.all().order_by('-started_at')[:limit]
        
        serializer = ReportExecutionSerializer(executions, many=True)
        
        return Response({
            'schedule_name': schedule.name,
            'report_name': schedule.report.name,
            'execution_count': executions.count(),
            'executions': serializer.data
        })
    
    @extend_schema(summary='Get Schedule Statistics')
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for this schedule"""
        schedule = self.get_object()
        
        # Get executions
        executions = schedule.executions.all()
        
        # Total executions
        total_executions = executions.count()
        
        # Successful executions
        successful_executions = executions.filter(success=True).count()
        
        # Failed executions
        failed_executions = executions.filter(success=False).count()
        
        # Average duration
        avg_duration = executions.aggregate(
            avg_duration=Avg('duration_seconds')
        )['avg_duration'] or 0
        
        # Average memory usage
        avg_memory = executions.aggregate(
            avg_memory=Avg('memory_usage_mb')
        )['avg_memory'] or 0
        
        # Average CPU usage
        avg_cpu = executions.aggregate(
            avg_cpu=Avg('cpu_usage_percent')
        )['avg_cpu'] or 0
        
        # Recent executions (last 10)
        recent_executions = executions.order_by('-started_at')[:10]
        recent_serializer = ReportExecutionSerializer(recent_executions, many=True)
        
        stats = {
            'schedule_id': str(schedule.id),
            'schedule_name': schedule.name,
            'report_name': schedule.report.name,
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0,
            'average_duration_seconds': round(avg_duration, 2),
            'average_memory_usage_mb': round(avg_memory, 2),
            'average_cpu_usage_percent': round(avg_cpu, 2),
            'recent_executions': recent_serializer.data
        }
        
        return Response(stats)


@extend_schema(tags=['Report Executions'])
class ReportExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing report executions
    """
    serializer_class = ReportExecutionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['schedule', 'success', 'started_at', 'completed_at']
    search_fields = ['schedule__name', 'schedule__report__name', 'error_message']
    ordering_fields = ['started_at', 'completed_at', 'duration_seconds', 'success']
    ordering = ['-started_at']
    
    def get_queryset(self):
        return ReportExecution.objects.filter(is_removed=False).select_related(
            'schedule__report'
        )


@extend_schema(
    tags=['Reports'],
    summary='Get Overall Report Statistics',
    responses={200: ReportStatisticsSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_statistics(request):
    """Get overall report statistics"""
    
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Report statistics
    total_reports = Report.objects.filter(is_removed=False).count()
    active_schedules = ReportSchedule.objects.filter(is_active=True, is_removed=False).count()
    generated_today = GeneratedReport.objects.filter(
        created__gte=today,
        is_removed=False
    ).count()
    
    # Average generation time
    avg_generation_time = GeneratedReport.objects.filter(
        status=ReportStatus.COMPLETED,
        is_removed=False
    ).aggregate(
        avg_time=Avg('generation_duration_ms')
    )['avg_time'] or 0
    
    # Reports by type
    by_type = Report.objects.filter(is_removed=False).values('report_type').annotate(count=Count('id'))
    reports_by_type = {item['report_type']: item['count'] for item in by_type}
    
    # Reports by format
    by_format = GeneratedReport.objects.filter(is_removed=False).values('format_type').annotate(count=Count('id'))
    reports_by_format = {item['format_type']: item['count'] for item in by_format}
    
    # Top services with reports
    top_services = Report.objects.filter(
        service__isnull=False,
        is_removed=False
    ).values(
        'service__name'
    ).annotate(
        report_count=Count('id')
    ).order_by('-report_count')[:5]
    
    top_services_list = [
        {'service': item['service__name'], 'count': item['report_count']}
        for item in top_services
    ]
    
    stats = {
        'total_reports': total_reports,
        'active_schedules': active_schedules,
        'generated_today': generated_today,
        'average_generation_time_ms': avg_generation_time,
        'reports_by_type': reports_by_type,
        'reports_by_format': reports_by_format,
        'top_services_with_reports': top_services_list
    }
    
    serializer = ReportStatisticsSerializer(stats)
    return Response(serializer.data)


@extend_schema(
    tags=['Reports'],
    summary='Trigger Report Generation',
    request=TriggerReportSerializer,
    responses={200: {'type': 'object'}}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_report_generation(request):
    """Trigger generation of a specific report or all active reports"""
    
    serializer = TriggerReportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    report_id = serializer.validated_data.get('report_id')
    parameters = serializer.validated_data.get('parameters', {})
    force = serializer.validated_data.get('force', False)
    
    if report_id:
        # Generate specific report
        try:
            report = Report.objects.get(id=report_id, is_removed=False)
            result = generate_report.delay(str(report.id), parameters, force)
            
            return Response({
                'message': _('Report generation initiated for specific report'),
                'report_id': str(report.id),
                'report_name': report.name,
                'task_id': result.id
            })
        except Report.DoesNotExist:
            return Response({
                'error': _('Report not found')
            }, status=status.HTTP_404_NOT_FOUND)
    else:
        # Generate all active reports (placeholder, might need refinement)
        # This could be a separate task or a loop over active reports
        # For now, we'll return an error or a message indicating it's not implemented
        return Response({
            'message': _('Generating all active reports is not implemented via this endpoint. Use individual report generation or scheduled runs.')
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Reports'],
    summary='Download Generated Report by ID',
    request=DownloadGeneratedReportSerializer,
    responses={200: {'type': 'object'}}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def download_generated_report(request):
    """Download a generated report by its ID"""
    
    serializer = DownloadGeneratedReportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    generated_report_id = serializer.validated_data.get('generated_report_id')
    
    try:
        generated_report = GeneratedReport.objects.get(
            id=generated_report_id,
            is_removed=False
        )
    except GeneratedReport.DoesNotExist:
        return Response({
            'error': _('Generated report not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not generated_report.is_complete or not generated_report.file:
        return Response({
            'error': _('Generated report is not complete or file is missing')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Redirect to download URL or return file content
    # For now, return a download URL
    download_url = request.build_absolute_uri(generated_report.file.url)
    return Response({
        'message': _('Download initiated'),
        'report_id': str(generated_report.report.id),
        'generated_report_id': str(generated_report.id),
        'download_url': download_url
    })
