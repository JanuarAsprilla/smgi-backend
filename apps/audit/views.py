# apps/audit/views.py
"""
SMGI Backend - Audit Views
Sistema de Monitoreo Geoespacial Inteligente
Vistas para el sistema de auditoría
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from datetime import timedelta
from drf_spectacular.utils import extend_schema

from apps.audit.models import (
    AuditLog, AuditTrail, AuditPolicy, AuditConfiguration,
    AuditEventType, AuditEventSeverity, AuditEventStatus, DataClassification
)
from apps.audit.serializers import (
    AuditLogListSerializer, AuditLogDetailSerializer, AuditLogCreateSerializer, AuditLogUpdateSerializer,
    AuditTrailListSerializer, AuditTrailDetailSerializer, AuditTrailCreateSerializer, AuditTrailUpdateSerializer,
    AuditPolicyListSerializer, AuditPolicyDetailSerializer, AuditPolicyCreateSerializer, AuditPolicyUpdateSerializer,
    AuditConfigurationListSerializer, AuditConfigurationDetailSerializer, AuditConfigurationCreateSerializer, AuditConfigurationUpdateSerializer,
    AuditStatisticsSerializer, TriggerAuditSerializer, DownloadAuditLogSerializer,
    MarkAsReadSerializer, MarkAsUnreadSerializer, ArchiveSerializer, UnarchiveSerializer, DeleteSerializer, BulkActionSerializer,
    StatisticsSerializer, TrendSerializer, FilterSerializer, SearchSerializer, SortSerializer, PaginationSerializer,
    ExportSerializer, ImportSerializer, SyncSerializer, ValidateSerializer, TransformSerializer, AggregateSerializer,
    GroupBySerializer, JoinSerializer
)
# Importar tareas Celery
from apps.audit.tasks import (
    audit_log, audit_trail, audit_policy, audit_config,
    send_audit_notification, send_audit_email, send_audit_webhook, send_audit_push,
    process_audit_log, process_audit_trail, process_audit_policy, process_audit_config,
    cleanup_old_audits, cleanup_old_audit_trails, cleanup_old_audit_policies, cleanup_old_audit_configurations,
    check_audit_system_health, run_audit_data_quality_checks, run_audit_performance_checks,
    run_audit_security_checks, run_audit_compliance_checks, run_audit_integrity_checks,
    run_audit_consistency_checks, run_audit_accuracy_checks, run_audit_completeness_checks,
    run_audit_timeliness_checks, run_audit_uniqueness_checks, run_audit_validity_checks,
    run_audit_reliability_checks, run_audit_availability_checks, run_audit_scalability_checks,
    run_audit_efficiency_checks, run_audit_effectiveness_checks, run_audit_sustainability_checks,
    run_audit_usability_checks, run_audit_accessibility_checks, run_audit_compatibility_checks,
    run_audit_interoperability_checks, run_audit_portability_checks, run_audit_maintainability_checks,
    run_audit_testability_checks, run_audit_debuggability_checks, run_audit_traceability_checks,
    run_audit_auditability_checks, run_audit_accountability_checks, run_audit_transparency_checks,
    run_audit_fairness_checks, run_audit_ethics_checks, run_audit_privacy_checks,
    run_audit_security_checks_advanced, run_audit_compliance_checks_advanced,
    run_audit_integrity_checks_advanced, run_audit_consistency_checks_advanced,
    run_audit_accuracy_checks_advanced, run_audit_completeness_checks_advanced,
    run_audit_timeliness_checks_advanced, run_audit_uniqueness_checks_advanced,
    run_audit_validity_checks_advanced, run_audit_reliability_checks_advanced,
    run_audit_availability_checks_advanced, run_audit_scalability_checks_advanced,
    run_audit_efficiency_checks_advanced, run_audit_effectiveness_checks_advanced,
    run_audit_sustainability_checks_advanced, run_audit_usability_checks_advanced,
    run_audit_accessibility_checks_advanced, run_audit_compatibility_checks_advanced,
    run_audit_interoperability_checks_advanced, run_audit_portability_checks_advanced,
    run_audit_maintainability_checks_advanced, run_audit_testability_checks_advanced,
    run_audit_debuggability_checks_advanced, run_audit_traceability_checks_advanced,
    run_audit_auditability_checks_advanced, run_audit_accountability_checks_advanced,
    run_audit_transparency_checks_advanced, run_audit_fairness_checks_advanced,
    run_audit_ethics_checks_advanced, run_audit_privacy_checks_advanced
)
# Importar modelos relacionados
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert
from apps.reports.models import Report
from apps.notifications.models import Notification, EmailNotification, WebhookNotification


@extend_schema(tags=['Audit Logs'])
class AuditLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing audit logs
    """
    serializer_class = AuditLogListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['event_type', 'severity', 'status', 'is_read', 'user', 'alert', 'parent_event']
    search_fields = ['title', 'message', 'short_message', 'user__email', 'user__username', 'alert__title', 'alert__alert_id']
    ordering_fields = ['created', 'event_type', 'severity', 'status', 'is_read', 'read_at']
    ordering = ['-created']
    
    def get_queryset(self):
        queryset = AuditLog.objects.filter(is_removed=False)
        
        # Filter by user
        user_filter = self.request.query_params.get('user')
        if user_filter:
            queryset = queryset.filter(user=user_filter)
        
        # Filter by alert
        alert_filter = self.request.query_params.get('alert')
        if alert_filter:
            queryset = queryset.filter(alert=alert_filter)
        
        # Filter by parent event
        parent_event_filter = self.request.query_params.get('parent_event')
        if parent_event_filter:
            queryset = queryset.filter(parent_event=parent_event_filter)
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(created__gte=since)
        
        return queryset.select_related('user', 'alert', 'parent_event')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuditLogListSerializer
        elif self.action == 'retrieve':
            return AuditLogDetailSerializer
        elif self.action == 'create':
            return AuditLogCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AuditLogUpdateSerializer
        return AuditLogListSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @extend_schema(summary='Mark Audit Log as Read')
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark audit log as read"""
        audit_log = self.get_object()
        serializer = MarkAsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_log.mark_as_read(request.user, notes):
            return Response({
                'message': _('Audit log marked as read successfully'),
                'audit_log': AuditLogDetailSerializer(audit_log).data
            })
        else:
            return Response({
                'error': _('Audit log cannot be marked as read in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Mark Audit Log as Unread')
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark audit log as unread"""
        audit_log = self.get_object()
        serializer = MarkAsUnreadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_log.mark_as_unread(request.user, notes):
            return Response({
                'message': _('Audit log marked as unread successfully'),
                'audit_log': AuditLogDetailSerializer(audit_log).data
            })
        else:
            return Response({
                'error': _('Audit log cannot be marked as unread in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Archive Audit Log')
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive audit log"""
        audit_log = self.get_object()
        serializer = ArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_log.archive(request.user, notes):
            return Response({
                'message': _('Audit log archived successfully'),
                'audit_log': AuditLogDetailSerializer(audit_log).data
            })
        else:
            return Response({
                'error': _('Audit log cannot be archived in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Unarchive Audit Log')
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive audit log"""
        audit_log = self.get_object()
        serializer = UnarchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_log.unarchive(request.user, notes):
            return Response({
                'message': _('Audit log unarchived successfully'),
                'audit_log': AuditLogDetailSerializer(audit_log).data
            })
        else:
            return Response({
                'error': _('Audit log cannot be unarchived in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Delete Audit Log')
    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """Delete (soft delete) audit log"""
        audit_log = self.get_object()
        serializer = DeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_log.delete(request.user, notes):
            return Response({
                'message': _('Audit log deleted successfully'),
                'audit_log': AuditLogDetailSerializer(audit_log).data
            })
        else:
            return Response({
                'error': _('Audit log cannot be deleted in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Bulk Action on Audit Logs')
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk action on multiple audit logs"""
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        audit_log_ids = serializer.validated_data['ids']
        notes = serializer.validated_data.get('notes', '')
        
        audit_logs = AuditLog.objects.filter(id__in=audit_log_ids, is_removed=False)
        
        success_count = 0
        failed_count = 0
        
        for audit_log in audit_logs:
            try:
                if action_type == 'mark_read':
                    audit_log.mark_as_read(request.user, notes)
                elif action_type == 'mark_unread':
                    audit_log.mark_as_unread(request.user, notes)
                elif action_type == 'archive':
                    audit_log.archive(request.user, notes)
                elif action_type == 'unarchive':
                    audit_log.unarchive(request.user, notes)
                elif action_type == 'delete':
                    audit_log.delete(request.user, notes)
                
                success_count += 1
            except Exception:
                failed_count += 1
        
        return Response({
            'message': _('Bulk action completed'),
            'action': action_type,
            'total': len(audit_log_ids),
            'success': success_count,
            'failed': failed_count
        })
    
    @extend_schema(summary='Get Audit Log Statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get audit log statistics"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_audit_logs = queryset.filter(created__gte=since)
        
        # Basic counts
        total_audit_logs = recent_audit_logs.count()
        unread_audit_logs = recent_audit_logs.filter(is_read=False).count()
        audit_logs_today = recent_audit_logs.filter(
            created__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Average duration
        avg_duration = recent_audit_logs.aggregate(
            avg_duration=Avg('duration_ms')
        )['avg_duration'] or 0
        
        # Group by event type
        by_event_type = recent_audit_logs.values('event_type').annotate(count=Count('id'))
        audit_logs_by_event_type = {item['event_type']: item['count'] for item in by_event_type}
        
        # Group by severity
        by_severity = recent_audit_logs.values('severity').annotate(count=Count('id'))
        audit_logs_by_severity = {item['severity']: item['count'] for item in by_severity}
        
        # Group by status
        by_status = recent_audit_logs.values('status').annotate(count=Count('id'))
        audit_logs_by_status = {item['status']: item['count'] for item in by_status}
        
        # Top users with audit logs
        top_users = recent_audit_logs.filter(
            user__isnull=False
        ).values(
            'user__email'
        ).annotate(
            audit_log_count=Count('id')
        ).order_by('-audit_log_count')[:5]
        
        top_users_list = [
            {'user': item['user__email'], 'count': item['audit_log_count']}
            for item in top_users
        ]
        
        stats = {
            'total_audit_logs': total_audit_logs,
            'unread_audit_logs': unread_audit_logs,
            'audit_logs_today': audit_logs_today,
            'average_duration_ms': round(avg_duration, 2),
            'audit_logs_by_event_type': audit_logs_by_event_type,
            'audit_logs_by_severity': audit_logs_by_severity,
            'audit_logs_by_status': audit_logs_by_status,
            'top_users_with_audit_logs': top_users_list
        }
        
        serializer = AuditStatisticsSerializer(stats)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Audit Log Trends')
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get audit log trends"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_audit_logs = queryset.filter(created__gte=since)
        
        # Daily trend
        daily_trend = list(
            recent_audit_logs.extra(select={'day': "date(created)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
            .values('day', 'count')
        )
        
        # Weekly trend
        weekly_trend = list(
            recent_audit_logs.extra(select={'week': "date_trunc('week', created)"})
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
            .values('week', 'count')
        )
        
        # Monthly trend
        monthly_trend = list(
            recent_audit_logs.extra(select={'month': "date_trunc('month', created)"})
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
            .values('month', 'count')
        )
        
        trends = {
            'daily_trend': daily_trend,
            'weekly_trend': weekly_trend,
            'monthly_trend': monthly_trend
        }
        
        serializer = TrendSerializer(trends)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Audit Log Filters')
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get audit log filters"""
        queryset = self.get_queryset()
        
        # Available filters
        filters = {
            'event_types': list(AuditEventType.choices),
            'severities': list(AuditEventSeverity.choices),
            'statuses': list(AuditEventStatus.choices),
            'users': list(queryset.values('user__email').distinct()),
            'alerts': list(queryset.values('alert__title').distinct()),
            'parent_events': list(queryset.values('parent_event__title').distinct())
        }
        
        serializer = FilterSerializer(filters)
        return Response(serializer.data)
    
    @extend_schema(summary='Search Audit Logs')
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search audit logs"""
        queryset = self.get_queryset()
        
        # Search query
        query = request.query_params.get('query', '')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(message__icontains=query) |
                Q(short_message__icontains=query) |
                Q(user__email__icontains=query) |
                Q(user__username__icontains=query) |
                Q(alert__title__icontains=query) |
                Q(alert__alert_id__icontains=query)
            )
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Sort Audit Logs')
    @action(detail=False, methods=['get'])
    def sort(self, request):
        """Sort audit logs"""
        queryset = self.get_queryset()
        
        # Sort by field
        sort_by = request.query_params.get('sort_by', '-created')
        if sort_by in self.ordering_fields:
            queryset = queryset.order_by(sort_by)
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Paginate Audit Logs')
    @action(detail=False, methods=['get'])
    def paginate(self, request):
        """Paginate audit logs"""
        queryset = self.get_queryset()
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Export Audit Logs')
    @action(detail=False, methods=['post'])
    def export(self, request):
        """Export audit logs"""
        serializer = ExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        format_type = serializer.validated_data.get('format', 'json')
        include_details = serializer.validated_data.get('include_details', True)
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Apply filters
        queryset = self.get_queryset()
        if filter_criteria:
            # This would require implementing filter logic based on filter_criteria
            # For now, we'll just return a placeholder
            pass
        
        # Export data
        # This would require implementing export logic based on format_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit logs export initiated'),
            'format': format_type,
            'include_details': include_details,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Import Audit Logs')
    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """Import audit logs"""
        serializer = ImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data.get('file')
        format_type = serializer.validated_data.get('format')
        overwrite_existing = serializer.validated_data.get('overwrite_existing', False)
        
        # Import data
        # This would require implementing import logic based on format_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit logs import initiated'),
            'file': file.name,
            'format': format_type,
            'overwrite_existing': overwrite_existing
        })
    
    @extend_schema(summary='Sync Audit Logs')
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Sync audit logs"""
        serializer = SyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        source = serializer.validated_data.get('source')
        destination = serializer.validated_data.get('destination')
        sync_type = serializer.validated_data.get('sync_type', 'incremental')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Sync data
        # This would require implementing sync logic based on source/destination/sync_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit logs sync initiated'),
            'source': source,
            'destination': destination,
            'sync_type': sync_type,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Validate Audit Logs')
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate audit logs"""
        serializer = ValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validation_rules = serializer.validated_data.get('validation_rules')
        fix_errors = serializer.validated_data.get('fix_errors', False)
        
        # Validate data
        # This would require implementing validation logic based on validation_rules
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit logs validation initiated'),
            'validation_rules': validation_rules,
            'fix_errors': fix_errors
        })
    
    @extend_schema(summary='Transform Audit Logs')
    @action(detail=False, methods=['post'])
    def transform(self, request):
        """Transform audit logs"""
        serializer = TransformSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        transformation_rules = serializer.validated_data.get('transformation_rules')
        output_format = serializer.validated_data.get('output_format', 'json')
        
        # Transform data
        # This would require implementing transformation logic based on transformation_rules
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit logs transformation initiated'),
            'transformation_rules': transformation_rules,
            'output_format': output_format
        })
    
    @extend_schema(summary='Aggregate Audit Logs')
    @action(detail=False, methods=['post'])
    def aggregate(self, request):
        """Aggregate audit logs"""
        serializer = AggregateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        aggregation_functions = serializer.validated_data.get('aggregation_functions')
        group_by_fields = serializer.validated_data.get('group_by_fields', [])
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Aggregate data
        # This would require implementing aggregation logic based on aggregation_functions/group_by_fields
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit logs aggregation initiated'),
            'aggregation_functions': aggregation_functions,
            'group_by_fields': group_by_fields,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Group Audit Logs')
    @action(detail=False, methods=['post'])
    def group_by(self, request):
        """Group audit logs"""
        serializer = GroupBySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        group_by_field = serializer.validated_data.get('group_by_field')
        aggregation_function = serializer.validated_data.get('aggregation_function', 'count')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Group data
        # This would require implementing grouping logic based on group_by_field/aggregation_function
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit logs grouping initiated'),
            'group_by_field': group_by_field,
            'aggregation_function': aggregation_function,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Join Audit Logs')
    @action(detail=False, methods=['post'])
    def join(self, request):
        """Join audit logs with other data sources"""
        serializer = JoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        join_type = serializer.validated_data.get('join_type')
        join_field = serializer.validated_data.get('join_field')
        join_with = serializer.validated_data.get('join_with')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Join data
        # This would require implementing join logic based on join_type/join_field/join_with
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit logs join initiated'),
            'join_type': join_type,
            'join_field': join_field,
            'join_with': join_with,
            'filter_criteria': filter_criteria
        })


@extend_schema(tags=['Audit Trails'])
class AuditTrailViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing audit trails
    """
    serializer_class = AuditTrailListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['model_name', 'change_type', 'user', 'timestamp']
    search_fields = ['model_name', 'object_id', 'field_name', 'user__email', 'user__username']
    ordering_fields = ['created', 'model_name', 'change_type', 'user', 'timestamp']
    ordering = ['-created']
    
    def get_queryset(self):
        queryset = AuditTrail.objects.filter(is_removed=False)
        
        # Filter by model name
        model_name_filter = self.request.query_params.get('model_name')
        if model_name_filter:
            queryset = queryset.filter(model_name=model_name_filter)
        
        # Filter by change type
        change_type_filter = self.request.query_params.get('change_type')
        if change_type_filter:
            queryset = queryset.filter(change_type=change_type_filter)
        
        # Filter by user
        user_filter = self.request.query_params.get('user')
        if user_filter:
            queryset = queryset.filter(user=user_filter)
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(timestamp__gte=since)
        
        return queryset.select_related('user')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuditTrailListSerializer
        elif self.action == 'retrieve':
            return AuditTrailDetailSerializer
        elif self.action == 'create':
            return AuditTrailCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AuditTrailUpdateSerializer
        return AuditTrailListSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @extend_schema(summary='Mark Audit Trail as Read')
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark audit trail as read"""
        audit_trail = self.get_object()
        serializer = MarkAsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_trail.mark_as_read(request.user, notes):
            return Response({
                'message': _('Audit trail marked as read successfully'),
                'audit_trail': AuditTrailDetailSerializer(audit_trail).data
            })
        else:
            return Response({
                'error': _('Audit trail cannot be marked as read in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Mark Audit Trail as Unread')
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark audit trail as unread"""
        audit_trail = self.get_object()
        serializer = MarkAsUnreadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_trail.mark_as_unread(request.user, notes):
            return Response({
                'message': _('Audit trail marked as unread successfully'),
                'audit_trail': AuditTrailDetailSerializer(audit_trail).data
            })
        else:
            return Response({
                'error': _('Audit trail cannot be marked as unread in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Archive Audit Trail')
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive audit trail"""
        audit_trail = self.get_object()
        serializer = ArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_trail.archive(request.user, notes):
            return Response({
                'message': _('Audit trail archived successfully'),
                'audit_trail': AuditTrailDetailSerializer(audit_trail).data
            })
        else:
            return Response({
                'error': _('Audit trail cannot be archived in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Unarchive Audit Trail')
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive audit trail"""
        audit_trail = self.get_object()
        serializer = UnarchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_trail.unarchive(request.user, notes):
            return Response({
                'message': _('Audit trail unarchived successfully'),
                'audit_trail': AuditTrailDetailSerializer(audit_trail).data
            })
        else:
            return Response({
                'error': _('Audit trail cannot be unarchived in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Delete Audit Trail')
    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """Delete (soft delete) audit trail"""
        audit_trail = self.get_object()
        serializer = DeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if audit_trail.delete(request.user, notes):
            return Response({
                'message': _('Audit trail deleted successfully'),
                'audit_trail': AuditTrailDetailSerializer(audit_trail).data
            })
        else:
            return Response({
                'error': _('Audit trail cannot be deleted in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(summary='Bulk Action on Audit Trails')
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk action on multiple audit trails"""
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        audit_trail_ids = serializer.validated_data['ids']
        notes = serializer.validated_data.get('notes', '')
        
        audit_trails = AuditTrail.objects.filter(id__in=audit_trail_ids, is_removed=False)
        
        success_count = 0
        failed_count = 0
        
        for audit_trail in audit_trails:
            try:
                if action_type == 'mark_read':
                    audit_trail.mark_as_read(request.user, notes)
                elif action_type == 'mark_unread':
                    audit_trail.mark_as_unread(request.user, notes)
                elif action_type == 'archive':
                    audit_trail.archive(request.user, notes)
                elif action_type == 'unarchive':
                    audit_trail.unarchive(request.user, notes)
                elif action_type == 'delete':
                    audit_trail.delete(request.user, notes)
                
                success_count += 1
            except Exception:
                failed_count += 1
        
        return Response({
            'message': _('Bulk action completed'),
            'action': action_type,
            'total': len(audit_trail_ids),
            'success': success_count,
            'failed': failed_count
        })
    
    @extend_schema(summary='Get Audit Trail Statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get audit trail statistics"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_audit_trails = queryset.filter(timestamp__gte=since)
        
        # Basic counts
        total_audit_trails = recent_audit_trails.count()
        audit_trails_today = recent_audit_trails.filter(
            timestamp__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Group by model name
        by_model_name = recent_audit_trails.values('model_name').annotate(count=Count('id'))
        audit_trails_by_model_name = {item['model_name']: item['count'] for item in by_model_name}
        
        # Group by change type
        by_change_type = recent_audit_trails.values('change_type').annotate(count=Count('id'))
        audit_trails_by_change_type = {item['change_type']: item['count'] for item in by_change_type}
        
        # Top users with audit trails
        top_users = recent_audit_trails.filter(
            user__isnull=False
        ).values(
            'user__email'
        ).annotate(
            audit_trail_count=Count('id')
        ).order_by('-audit_trail_count')[:5]
        
        top_users_list = [
            {'user': item['user__email'], 'count': item['audit_trail_count']}
            for item in top_users
        ]
        
        stats = {
            'total_audit_trails': total_audit_trails,
            'audit_trails_today': audit_trails_today,
            'audit_trails_by_model_name': audit_trails_by_model_name,
            'audit_trails_by_change_type': audit_trails_by_change_type,
            'top_users_with_audit_trails': top_users_list
        }
        
        serializer = StatisticsSerializer(stats)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Audit Trail Trends')
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get audit trail trends"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_audit_trails = queryset.filter(timestamp__gte=since)
        
        # Daily trend
        daily_trend = list(
            recent_audit_trails.extra(select={'day': "date(timestamp)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
            .values('day', 'count')
        )
        
        # Weekly trend
        weekly_trend = list(
            recent_audit_trails.extra(select={'week': "date_trunc('week', timestamp)"})
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
            .values('week', 'count')
        )
        
        # Monthly trend
        monthly_trend = list(
            recent_audit_trails.extra(select={'month': "date_trunc('month', timestamp)"})
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
            .values('month', 'count')
        )
        
        trends = {
            'daily_trend': daily_trend,
            'weekly_trend': weekly_trend,
            'monthly_trend': monthly_trend
        }
        
        serializer = TrendSerializer(trends)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Audit Trail Filters')
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get audit trail filters"""
        queryset = self.get_queryset()
        
        # Available filters
        filters = {
            'model_names': list(queryset.values('model_name').distinct()),
            'change_types': list(AuditTrail.change_type_choices),
            'users': list(queryset.values('user__email').distinct())
        }
        
        serializer = FilterSerializer(filters)
        return Response(serializer.data)
    
    @extend_schema(summary='Search Audit Trails')
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search audit trails"""
        queryset = self.get_queryset()
        
        # Search query
        query = request.query_params.get('query', '')
        if query:
            queryset = queryset.filter(
                Q(model_name__icontains=query) |
                Q(object_id__icontains=query) |
                Q(field_name__icontains=query) |
                Q(user__email__icontains=query) |
                Q(user__username__icontains=query)
            )
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Sort Audit Trails')
    @action(detail=False, methods=['get'])
    def sort(self, request):
        """Sort audit trails"""
        queryset = self.get_queryset()
        
        # Sort by field
        sort_by = request.query_params.get('sort_by', '-timestamp')
        if sort_by in self.ordering_fields:
            queryset = queryset.order_by(sort_by)
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Paginate Audit Trails')
    @action(detail=False, methods=['get'])
    def paginate(self, request):
        """Paginate audit trails"""
        queryset = self.get_queryset()
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Export Audit Trails')
    @action(detail=False, methods=['post'])
    def export(self, request):
        """Export audit trails"""
        serializer = ExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        format_type = serializer.validated_data.get('format', 'json')
        include_details = serializer.validated_data.get('include_details', True)
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Apply filters
        queryset = self.get_queryset()
        if filter_criteria:
            # This would require implementing filter logic based on filter_criteria
            # For now, we'll just return a placeholder
            pass
        
        # Export data
        # This would require implementing export logic based on format_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit trails export initiated'),
            'format': format_type,
            'include_details': include_details,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Import Audit Trails')
    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """Import audit trails"""
        serializer = ImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data.get('file')
        format_type = serializer.validated_data.get('format')
        overwrite_existing = serializer.validated_data.get('overwrite_existing', False)
        
        # Import data
        # This would require implementing import logic based on format_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit trails import initiated'),
            'file': file.name,
            'format': format_type,
            'overwrite_existing': overwrite_existing
        })
    
    @extend_schema(summary='Sync Audit Trails')
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Sync audit trails"""
        serializer = SyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        source = serializer.validated_data.get('source')
        destination = serializer.validated_data.get('destination')
        sync_type = serializer.validated_data.get('sync_type', 'incremental')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Sync data
        # This would require implementing sync logic based on source/destination/sync_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit trails sync initiated'),
            'source': source,
            'destination': destination,
            'sync_type': sync_type,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Validate Audit Trails')
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate audit trails"""
        serializer = ValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validation_rules = serializer.validated_data.get('validation_rules')
        fix_errors = serializer.validated_data.get('fix_errors', False)
        
        # Validate data
        # This would require implementing validation logic based on validation_rules
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit trails validation initiated'),
            'validation_rules': validation_rules,
            'fix_errors': fix_errors
        })
    
    @extend_schema(summary='Transform Audit Trails')
    @action(detail=False, methods=['post'])
    def transform(self, request):
        """Transform audit trails"""
        serializer = TransformSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        transformation_rules = serializer.validated_data.get('transformation_rules')
        output_format = serializer.validated_data.get('output_format', 'json')
        
        # Transform data
        # This would require implementing transformation logic based on transformation_rules
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit trails transformation initiated'),
            'transformation_rules': transformation_rules,
            'output_format': output_format
        })
    
    @extend_schema(summary='Aggregate Audit Trails')
    @action(detail=False, methods=['post'])
    def aggregate(self, request):
        """Aggregate audit trails"""
        serializer = AggregateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        aggregation_functions = serializer.validated_data.get('aggregation_functions')
        group_by_fields = serializer.validated_data.get('group_by_fields', [])
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Aggregate data
        # This would require implementing aggregation logic based on aggregation_functions/group_by_fields
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit trails aggregation initiated'),
            'aggregation_functions': aggregation_functions,
            'group_by_fields': group_by_fields,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Group Audit Trails')
    @action(detail=False, methods=['post'])
    def group_by(self, request):
        """Group audit trails"""
        serializer = GroupBySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        group_by_field = serializer.validated_data.get('group_by_field')
        aggregation_function = serializer.validated_data.get('aggregation_function', 'count')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Group data
        # This would require implementing grouping logic based on group_by_field/aggregation_function
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit trails grouping initiated'),
            'group_by_field': group_by_field,
            'aggregation_function': aggregation_function,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Join Audit Trails')
    @action(detail=False, methods=['post'])
    def join(self, request):
        """Join audit trails with other data sources"""
        serializer = JoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        join_type = serializer.validated_data.get('join_type')
        join_field = serializer.validated_data.get('join_field')
        join_with = serializer.validated_data.get('join_with')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Join data
        # This would require implementing join logic based on join_type/join_field/join_with
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit trails join initiated'),
            'join_type': join_type,
            'join_field': join_field,
            'join_with': join_with,
            'filter_criteria': filter_criteria
        })


@extend_schema(tags=['Audit Policies'])
class AuditPolicyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing audit policies
    """
    serializer_class = AuditPolicyListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'resource_types', 'event_types', 'severity_levels', 'actions', 'users', 'ip_addresses', 'user_agents']
    search_fields = ['name', 'description', 'users__email', 'users__username', 'ip_addresses', 'user_agents']
    ordering_fields = ['name', 'is_active', 'created', 'modified']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = AuditPolicy.objects.filter(is_removed=False)
        
        # Filter by active status
        is_active_filter = self.request.query_params.get('is_active')
        if is_active_filter is not None:
            queryset = queryset.filter(is_active=is_active_filter.lower() == 'true')
        
        # Filter by resource types
        resource_types_filter = self.request.query_params.get('resource_types')
        if resource_types_filter:
            resource_types_list = resource_types_filter.split(',')
            queryset = queryset.filter(resource_types__overlap=resource_types_list)
        
        # Filter by event types
        event_types_filter = self.request.query_params.get('event_types')
        if event_types_filter:
            event_types_list = event_types_filter.split(',')
            queryset = queryset.filter(event_types__overlap=event_types_list)
        
        # Filter by severity levels
        severity_levels_filter = self.request.query_params.get('severity_levels')
        if severity_levels_filter:
            severity_levels_list = severity_levels_filter.split(',')
            queryset = queryset.filter(severity_levels__overlap=severity_levels_list)
        
        # Filter by actions
        actions_filter = self.request.query_params.get('actions')
        if actions_filter:
            actions_list = actions_filter.split(',')
            queryset = queryset.filter(actions__overlap=actions_list)
        
        # Filter by users
        users_filter = self.request.query_params.get('users')
        if users_filter:
            user_ids = users_filter.split(',')
            queryset = queryset.filter(users__id__in=user_ids)
        
        # Filter by IP addresses
        ip_addresses_filter = self.request.query_params.get('ip_addresses')
        if ip_addresses_filter:
            ip_addresses_list = ip_addresses_filter.split(',')
            queryset = queryset.filter(ip_addresses__overlap=ip_addresses_list)
        
        # Filter by user agents
        user_agents_filter = self.request.query_params.get('user_agents')
        if user_agents_filter:
            user_agents_list = user_agents_filter.split(',')
            queryset = queryset.filter(user_agents__overlap=user_agents_list)
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(created__gte=since)
        
        return queryset.select_related('created_by', 'modified_by')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuditPolicyListSerializer
        elif self.action == 'retrieve':
            return AuditPolicyDetailSerializer
        elif self.action == 'create':
            return AuditPolicyCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AuditPolicyUpdateSerializer
        return AuditPolicyListSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @extend_schema(summary='Toggle Audit Policy Active Status')
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle audit policy active status"""
        policy = self.get_object()
        policy.is_active = not policy.is_active
        policy.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit policy {}').format(
                _('activated') if policy.is_active else _('deactivated')
            ),
            'is_active': policy.is_active
        })
    
    @extend_schema(summary='Enable Audit Policy')
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable audit policy"""
        policy = self.get_object()
        policy.is_active = True
        policy.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit policy enabled'),
            'is_active': policy.is_active
        })
    
    @extend_schema(summary='Disable Audit Policy')
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable audit policy"""
        policy = self.get_object()
        policy.is_active = False
        policy.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit policy disabled'),
            'is_active': policy.is_active
        })
    
    @extend_schema(summary='Activate Audit Policy')
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate audit policy"""
        policy = self.get_object()
        policy.is_active = True
        policy.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit policy activated'),
            'is_active': policy.is_active
        })
    
    @extend_schema(summary='Deactivate Audit Policy')
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate audit policy"""
        policy = self.get_object()
        policy.is_active = False
        policy.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit policy deactivated'),
            'is_active': policy.is_active
        })
    
    @extend_schema(summary='Run Audit Policy Now')
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Run audit policy immediately"""
        policy = self.get_object()
        
        # Trigger audit policy task
        from apps.audit.tasks import audit_policy
        result = audit_policy.delay(str(policy.id))
        
        return Response({
            'message': _('Audit policy execution initiated'),
            'policy_id': str(policy.id),
            'policy_name': policy.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Schedule Audit Policy')
    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        """Schedule audit policy"""
        policy = self.get_object()
        
        # Trigger schedule task
        from apps.audit.tasks import schedule_audit_policy
        result = schedule_audit_policy.delay(str(policy.id))
        
        return Response({
            'message': _('Audit policy scheduling initiated'),
            'policy_id': str(policy.id),
            'policy_name': policy.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Unschedule Audit Policy')
    @action(detail=True, methods=['post'])
    def unschedule(self, request, pk=None):
        """Cancel audit policy scheduling"""
        policy = self.get_object()
        
        # Trigger unschedule task
        from apps.audit.tasks import unschedule_audit_policy
        result = unschedule_audit_policy.delay(str(policy.id))
        
        return Response({
            'message': _('Audit policy unscheduling initiated'),
            'policy_id': str(policy.id),
            'policy_name': policy.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Execute Audit Policy')
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute audit policy"""
        policy = self.get_object()
        
        # Trigger audit policy task
        from apps.audit.tasks import audit_policy
        result = audit_policy.delay(str(policy.id))
        
        return Response({
            'message': _('Audit policy execution initiated'),
            'policy_id': str(policy.id),
            'policy_name': policy.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Test Audit Policy')
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test audit policy"""
        policy = self.get_object()
        
        # Trigger test task
        from apps.audit.tasks import test_audit_policy
        result = test_audit_policy.delay(str(policy.id))
        
        return Response({
            'message': _('Audit policy test initiated'),
            'policy_id': str(policy.id),
            'policy_name': policy.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Validate Audit Policy')
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate audit policy"""
        policy = self.get_object()
        
        # Trigger validate task
        from apps.audit.tasks import validate_audit_policy
        result = validate_audit_policy.delay(str(policy.id))
        
        return Response({
            'message': _('Audit policy validation initiated'),
            'policy_id': str(policy.id),
            'policy_name': policy.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Preview Audit Policy')
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview audit policy"""
        policy = self.get_object()
        
        # Return policy details
        serializer = self.get_serializer(policy)
        return Response(serializer.data)
    
    @extend_schema(summary='Clone Audit Policy')
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone audit policy"""
        policy = self.get_object()
        
        # Create a new policy with the same data
        new_policy = AuditPolicy.objects.create(
            name=f"{policy.name} (Copy)",
            description=_(f"Copy of {policy.description}"),
            is_active=False, # Start as inactive
            resource_types=policy.resource_types,
            event_types=policy.event_types,
            severity_levels=policy.severity_levels,
            actions=policy.actions,
            users=policy.users.all(), # Copy M2M relations
            ip_addresses=policy.ip_addresses,
            user_agents=policy.user_agents,
            retention_days=policy.retention_days,
            archive_after_days=policy.archive_after_days,
            notify_on_events=policy.notify_on_events,
            notification_channels=policy.notification_channels,
            notification_recipients=policy.notification_recipients.all(), # Copy M2M relations
            created_by=request.user,
            modified_by=request.user
        )
        
        serializer = self.get_serializer(new_policy)
        return Response({
            'message': _('Audit policy cloned successfully'),
            'policy': serializer.data
        })
    
    @extend_schema(summary='Delete Audit Policy')
    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """Delete (soft delete) audit policy"""
        policy = self.get_object()
        policy.delete() # Soft delete
        
        return Response({
            'message': _('Audit policy deleted successfully')
        }, status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(summary='Bulk Action on Audit Policies')
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk action on multiple audit policies"""
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        policy_ids = serializer.validated_data['ids']
        notes = serializer.validated_data.get('notes', '')
        
        policies = AuditPolicy.objects.filter(id__in=policy_ids, is_removed=False)
        
        success_count = 0
        failed_count = 0
        
        for policy in policies:
            try:
                if action_type == 'enable':
                    policy.is_active = True
                    policy.save(update_fields=['is_active'])
                elif action_type == 'disable':
                    policy.is_active = False
                    policy.save(update_fields=['is_active'])
                elif action_type == 'activate':
                    policy.is_active = True
                    policy.save(update_fields=['is_active'])
                elif action_type == 'deactivate':
                    policy.is_active = False
                    policy.save(update_fields=['is_active'])
                elif action_type == 'delete':
                    policy.delete() # Soft delete
                
                success_count += 1
            except Exception:
                failed_count += 1
        
        return Response({
            'message': _('Bulk action completed'),
            'action': action_type,
            'total': len(policy_ids),
            'success': success_count,
            'failed': failed_count
        })
    
    @extend_schema(summary='Get Audit Policy Statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get audit policy statistics"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_policies = queryset.filter(created__gte=since)
        
        # Basic counts
        total_policies = recent_policies.count()
        active_policies = recent_policies.filter(is_active=True).count()
        policies_today = recent_policies.filter(
            created__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Group by resource types
        by_resource_types = recent_policies.values('resource_types').annotate(count=Count('id'))
        policies_by_resource_types = {item['resource_types']: item['count'] for item in by_resource_types}
        
        # Group by event types
        by_event_types = recent_policies.values('event_types').annotate(count=Count('id'))
        policies_by_event_types = {item['event_types']: item['count'] for item in by_event_types}
        
        # Group by severity levels
        by_severity_levels = recent_policies.values('severity_levels').annotate(count=Count('id'))
        policies_by_severity_levels = {item['severity_levels']: item['count'] for item in by_severity_levels}
        
        # Group by actions
        by_actions = recent_policies.values('actions').annotate(count=Count('id'))
        policies_by_actions = {item['actions']: item['count'] for item in by_actions}
        
        # Top users with policies
        top_users = recent_policies.filter(
            users__isnull=False
        ).values(
            'users__email'
        ).annotate(
            policy_count=Count('id')
        ).order_by('-policy_count')[:5]
        
        top_users_list = [
            {'user': item['users__email'], 'count': item['policy_count']}
            for item in top_users
        ]
        
        stats = {
            'total_policies': total_policies,
            'active_policies': active_policies,
            'policies_today': policies_today,
            'policies_by_resource_types': policies_by_resource_types,
            'policies_by_event_types': policies_by_event_types,
            'policies_by_severity_levels': policies_by_severity_levels,
            'policies_by_actions': policies_by_actions,
            'top_users_with_policies': top_users_list
        }
        
        serializer = StatisticsSerializer(stats)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Audit Policy Trends')
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get audit policy trends"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_policies = queryset.filter(created__gte=since)
        
        # Daily trend
        daily_trend = list(
            recent_policies.extra(select={'day': "date(created)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
            .values('day', 'count')
        )
        
        # Weekly trend
        weekly_trend = list(
            recent_policies.extra(select={'week': "date_trunc('week', created)"})
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
            .values('week', 'count')
        )
        
        # Monthly trend
        monthly_trend = list(
            recent_policies.extra(select={'month': "date_trunc('month', created)"})
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
            .values('month', 'count')
        )
        
        trends = {
            'daily_trend': daily_trend,
            'weekly_trend': weekly_trend,
            'monthly_trend': monthly_trend
        }
        
        serializer = TrendSerializer(trends)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Audit Policy Filters')
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get audit policy filters"""
        queryset = self.get_queryset()
        
        # Available filters
        filters = {
            'is_active': list(queryset.values('is_active').distinct()),
            'resource_types': list(queryset.values('resource_types').distinct()),
            'event_types': list(queryset.values('event_types').distinct()),
            'severity_levels': list(queryset.values('severity_levels').distinct()),
            'actions': list(queryset.values('actions').distinct()),
            'users': list(queryset.values('users__email').distinct()),
            'ip_addresses': list(queryset.values('ip_addresses').distinct()),
            'user_agents': list(queryset.values('user_agents').distinct())
        }
        
        serializer = FilterSerializer(filters)
        return Response(serializer.data)
    
    @extend_schema(summary='Search Audit Policies')
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search audit policies"""
        queryset = self.get_queryset()
        
        # Search query
        query = request.query_params.get('query', '')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(users__email__icontains=query) |
                Q(users__username__icontains=query) |
                Q(ip_addresses__icontains=query) |
                Q(user_agents__icontains=query)
            )
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Sort Audit Policies')
    @action(detail=False, methods=['get'])
    def sort(self, request):
        """Sort audit policies"""
        queryset = self.get_queryset()
        
        # Sort by field
        sort_by = request.query_params.get('sort_by', 'name')
        if sort_by in self.ordering_fields:
            queryset = queryset.order_by(sort_by)
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Paginate Audit Policies')
    @action(detail=False, methods=['get'])
    def paginate(self, request):
        """Paginate audit policies"""
        queryset = self.get_queryset()
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Export Audit Policies')
    @action(detail=False, methods=['post'])
    def export(self, request):
        """Export audit policies"""
        serializer = ExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        format_type = serializer.validated_data.get('format', 'json')
        include_details = serializer.validated_data.get('include_details', True)
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Apply filters
        queryset = self.get_queryset()
        if filter_criteria:
            # This would require implementing filter logic based on filter_criteria
            # For now, we'll just return a placeholder
            pass
        
        # Export data
        # This would require implementing export logic based on format_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit policies export initiated'),
            'format': format_type,
            'include_details': include_details,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Import Audit Policies')
    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """Import audit policies"""
        serializer = ImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data.get('file')
        format_type = serializer.validated_data.get('format')
        overwrite_existing = serializer.validated_data.get('overwrite_existing', False)
        
        # Import data
        # This would require implementing import logic based on format_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit policies import initiated'),
            'file': file.name,
            'format': format_type,
            'overwrite_existing': overwrite_existing
        })
    
    @extend_schema(summary='Sync Audit Policies')
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Sync audit policies"""
        serializer = SyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        source = serializer.validated_data.get('source')
        destination = serializer.validated_data.get('destination')
        sync_type = serializer.validated_data.get('sync_type', 'incremental')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Sync data
        # This would require implementing sync logic based on source/destination/sync_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit policies sync initiated'),
            'source': source,
            'destination': destination,
            'sync_type': sync_type,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Validate Audit Policies')
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate audit policies"""
        serializer = ValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validation_rules = serializer.validated_data.get('validation_rules')
        fix_errors = serializer.validated_data.get('fix_errors', False)
        
        # Validate data
        # This would require implementing validation logic based on validation_rules
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit policies validation initiated'),
            'validation_rules': validation_rules,
            'fix_errors': fix_errors
        })
    
    @extend_schema(summary='Transform Audit Policies')
    @action(detail=False, methods=['post'])
    def transform(self, request):
        """Transform audit policies"""
        serializer = TransformSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        transformation_rules = serializer.validated_data.get('transformation_rules')
        output_format = serializer.validated_data.get('output_format', 'json')
        
        # Transform data
        # This would require implementing transformation logic based on transformation_rules
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit policies transformation initiated'),
            'transformation_rules': transformation_rules,
            'output_format': output_format
        })
    
    @extend_schema(summary='Aggregate Audit Policies')
    @action(detail=False, methods=['post'])
    def aggregate(self, request):
        """Aggregate audit policies"""
        serializer = AggregateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        aggregation_functions = serializer.validated_data.get('aggregation_functions')
        group_by_fields = serializer.validated_data.get('group_by_fields', [])
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Aggregate data
        # This would require implementing aggregation logic based on aggregation_functions/group_by_fields
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit policies aggregation initiated'),
            'aggregation_functions': aggregation_functions,
            'group_by_fields': group_by_fields,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Group Audit Policies')
    @action(detail=False, methods=['post'])
    def group_by(self, request):
        """Group audit policies"""
        serializer = GroupBySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        group_by_field = serializer.validated_data.get('group_by_field')
        aggregation_function = serializer.validated_data.get('aggregation_function', 'count')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Group data
        # This would require implementing grouping logic based on group_by_field/aggregation_function
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit policies grouping initiated'),
            'group_by_field': group_by_field,
            'aggregation_function': aggregation_function,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Join Audit Policies')
    @action(detail=False, methods=['post'])
    def join(self, request):
        """Join audit policies with other data sources"""
        serializer = JoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        join_type = serializer.validated_data.get('join_type')
        join_field = serializer.validated_data.get('join_field')
        join_with = serializer.validated_data.get('join_with')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Join data
        # This would require implementing join logic based on join_type/join_field/join_with
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit policies join initiated'),
            'join_type': join_type,
            'join_field': join_field,
            'join_with': join_with,
            'filter_criteria': filter_criteria
        })


@extend_schema(tags=['Audit Configurations'])
class AuditConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing audit configurations
    """
    serializer_class = AuditConfigurationListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'default_retention_days', 'default_archive_after_days', 'default_data_classification']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'is_active', 'created', 'modified']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = AuditConfiguration.objects.filter(is_removed=False)
        
        # Filter by active status
        is_active_filter = self.request.query_params.get('is_active')
        if is_active_filter is not None:
            queryset = queryset.filter(is_active=is_active_filter.lower() == 'true')
        
        # Filter by default retention days
        default_retention_days_filter = self.request.query_params.get('default_retention_days')
        if default_retention_days_filter:
            queryset = queryset.filter(default_retention_days=int(default_retention_days_filter))
        
        # Filter by default archive after days
        default_archive_after_days_filter = self.request.query_params.get('default_archive_after_days')
        if default_archive_after_days_filter:
            queryset = queryset.filter(default_archive_after_days=int(default_archive_after_days_filter))
        
        # Filter by default data classification
        default_data_classification_filter = self.request.query_params.get('default_data_classification')
        if default_data_classification_filter:
            queryset = queryset.filter(default_data_classification=default_data_classification_filter)
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(created__gte=since)
        
        return queryset.select_related('created_by', 'modified_by')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuditConfigurationListSerializer
        elif self.action == 'retrieve':
            return AuditConfigurationDetailSerializer
        elif self.action == 'create':
            return AuditConfigurationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AuditConfigurationUpdateSerializer
        return AuditConfigurationListSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @extend_schema(summary='Toggle Audit Configuration Active Status')
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle audit configuration active status"""
        config = self.get_object()
        config.is_active = not config.is_active
        config.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit configuration {}').format(
                _('activated') if config.is_active else _('deactivated')
            ),
            'is_active': config.is_active
        })
    
    @extend_schema(summary='Enable Audit Configuration')
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable audit configuration"""
        config = self.get_object()
        config.is_active = True
        config.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit configuration enabled'),
            'is_active': config.is_active
        })
    
    @extend_schema(summary='Disable Audit Configuration')
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable audit configuration"""
        config = self.get_object()
        config.is_active = False
        config.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit configuration disabled'),
            'is_active': config.is_active
        })
    
    @extend_schema(summary='Activate Audit Configuration')
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate audit configuration"""
        config = self.get_object()
        config.is_active = True
        config.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit configuration activated'),
            'is_active': config.is_active
        })
    
    @extend_schema(summary='Deactivate Audit Configuration')
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate audit configuration"""
        config = self.get_object()
        config.is_active = False
        config.save(update_fields=['is_active'])
        
        return Response({
            'message': _('Audit configuration deactivated'),
            'is_active': config.is_active
        })
    
    @extend_schema(summary='Run Audit Configuration Now')
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Run audit configuration immediately"""
        config = self.get_object()
        
        # Trigger audit config task
        from apps.audit.tasks import audit_config
        result = audit_config.delay(str(config.id))
        
        return Response({
            'message': _('Audit configuration execution initiated'),
            'config_id': str(config.id),
            'config_name': config.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Schedule Audit Configuration')
    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        """Schedule audit configuration"""
        config = self.get_object()
        
        # Trigger schedule task
        from apps.audit.tasks import schedule_audit_config
        result = schedule_audit_config.delay(str(config.id))
        
        return Response({
            'message': _('Audit configuration scheduling initiated'),
            'config_id': str(config.id),
            'config_name': config.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Unschedule Audit Configuration')
    @action(detail=True, methods=['post'])
    def unschedule(self, request, pk=None):
        """Cancel audit configuration scheduling"""
        config = self.get_object()
        
        # Trigger unschedule task
        from apps.audit.tasks import unschedule_audit_config
        result = unschedule_audit_config.delay(str(config.id))
        
        return Response({
            'message': _('Audit configuration unscheduling initiated'),
            'config_id': str(config.id),
            'config_name': config.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Execute Audit Configuration')
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute audit configuration"""
        config = self.get_object()
        
        # Trigger audit config task
        from apps.audit.tasks import audit_config
        result = audit_config.delay(str(config.id))
        
        return Response({
            'message': _('Audit configuration execution initiated'),
            'config_id': str(config.id),
            'config_name': config.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Test Audit Configuration')
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test audit configuration"""
        config = self.get_object()
        
        # Trigger test task
        from apps.audit.tasks import test_audit_config
        result = test_audit_config.delay(str(config.id))
        
        return Response({
            'message': _('Audit configuration test initiated'),
            'config_id': str(config.id),
            'config_name': config.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Validate Audit Configuration')
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate audit configuration"""
        config = self.get_object()
        
        # Trigger validate task
        from apps.audit.tasks import validate_audit_config
        result = validate_audit_config.delay(str(config.id))
        
        return Response({
            'message': _('Audit configuration validation initiated'),
            'config_id': str(config.id),
            'config_name': config.name,
            'task_id': result.id
        })
    
    @extend_schema(summary='Preview Audit Configuration')
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview audit configuration"""
        config = self.get_object()
        
        # Return config details
        serializer = self.get_serializer(config)
        return Response(serializer.data)
    
    @extend_schema(summary='Clone Audit Configuration')
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone audit configuration"""
        config = self.get_object()
        
        # Create a new config with the same data
        new_config = AuditConfiguration.objects.create(
            name=f"{config.name} (Copy)",
            description=_(f"Copy of {config.description}"),
            is_active=False, # Start as inactive
            default_retention_days=config.default_retention_days,
            default_archive_after_days=config.default_archive_after_days,
            default_data_classification=config.default_data_classification,
            enable_real_time_logging=config.enable_real_time_logging,
            enable_batch_logging=config.enable_batch_logging,
            batch_size=config.batch_size,
            log_level=config.log_level,
            exclude_sensitive_fields=config.exclude_sensitive_fields,
            mask_sensitive_data=config.mask_sensitive_data,
            encrypt_audit_logs=config.encrypt_audit_logs,
            store_audit_trails=config.store_audit_trails,
            store_user_sessions=config.store_user_sessions,
            store_api_calls=config.store_api_calls,
            store_external_api_calls=config.store_external_api_calls,
            store_internal_api_calls=config.store_internal_api_calls,
            store_database_queries=config.store_database_queries,
            store_cache_operations=config.store_cache_operations,
            store_file_operations=config.store_file_operations,
            store_email_sending=config.store_email_sending,
            store_sms_sending=config.store_sms_sending,
            store_webhook_sending=config.store_webhook_sending,
            store_push_notification_sending=config.store_push_notification_sending,
            store_report_generation=config.store_report_generation,
            store_alert_triggering=config.store_alert_triggering,
            store_monitoring_job_scheduling=config.store_monitoring_job_scheduling,
            store_system_health_checks=config.store_system_health_checks,
            store_data_validation=config.store_data_validation,
            store_gis_service_interaction=config.store_gis_service_interaction,
            store_authentication=config.store_authentication,
            store_authorization=config.store_authorization,
            store_error_handling=config.store_error_handling,
            store_performance_monitoring=config.store_performance_monitoring,
            created_by=request.user,
            modified_by=request.user
        )
        
        serializer = self.get_serializer(new_config)
        return Response({
            'message': _('Audit configuration cloned successfully'),
            'config': serializer.data
        })
    
    @extend_schema(summary='Delete Audit Configuration')
    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """Delete (soft delete) audit configuration"""
        config = self.get_object()
        config.delete() # Soft delete
        
        return Response({
            'message': _('Audit configuration deleted successfully')
        }, status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(summary='Bulk Action on Audit Configurations')
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk action on multiple audit configurations"""
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        config_ids = serializer.validated_data['ids']
        notes = serializer.validated_data.get('notes', '')
        
        configs = AuditConfiguration.objects.filter(id__in=config_ids, is_removed=False)
        
        success_count = 0
        failed_count = 0
        
        for config in configs:
            try:
                if action_type == 'enable':
                    config.is_active = True
                    config.save(update_fields=['is_active'])
                elif action_type == 'disable':
                    config.is_active = False
                    config.save(update_fields=['is_active'])
                elif action_type == 'activate':
                    config.is_active = True
                    config.save(update_fields=['is_active'])
                elif action_type == 'deactivate':
                    config.is_active = False
                    config.save(update_fields=['is_active'])
                elif action_type == 'delete':
                    config.delete() # Soft delete
                
                success_count += 1
            except Exception:
                failed_count += 1
        
        return Response({
            'message': _('Bulk action completed'),
            'action': action_type,
            'total': len(config_ids),
            'success': success_count,
            'failed': failed_count
        })
    
    @extend_schema(summary='Get Audit Configuration Statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get audit configuration statistics"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_configs = queryset.filter(created__gte=since)
        
        # Basic counts
        total_configs = recent_configs.count()
        active_configs = recent_configs.filter(is_active=True).count()
        configs_today = recent_configs.filter(
            created__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Group by default retention days
        by_retention_days = recent_configs.values('default_retention_days').annotate(count=Count('id'))
        configs_by_retention_days = {item['default_retention_days']: item['count'] for item in by_retention_days}
        
        # Group by default archive after days
        by_archive_days = recent_configs.values('default_archive_after_days').annotate(count=Count('id'))
        configs_by_archive_days = {item['default_archive_after_days']: item['count'] for item in by_archive_days}
        
        # Group by default data classification
        by_data_classification = recent_configs.values('default_data_classification').annotate(count=Count('id'))
        configs_by_data_classification = {item['default_data_classification']: item['count'] for item in by_data_classification}
        
        # Top users with configs
        top_users = recent_configs.filter(
            created_by__isnull=False
        ).values(
            'created_by__email'
        ).annotate(
            config_count=Count('id')
        ).order_by('-config_count')[:5]
        
        top_users_list = [
            {'user': item['created_by__email'], 'count': item['config_count']}
            for item in top_users
        ]
        
        stats = {
            'total_configs': total_configs,
            'active_configs': active_configs,
            'configs_today': configs_today,
            'configs_by_retention_days': configs_by_retention_days,
            'configs_by_archive_days': configs_by_archive_days,
            'configs_by_data_classification': configs_by_data_classification,
            'top_users_with_configs': top_users_list
        }
        
        serializer = StatisticsSerializer(stats)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Audit Configuration Trends')
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get audit configuration trends"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_configs = queryset.filter(created__gte=since)
        
        # Daily trend
        daily_trend = list(
            recent_configs.extra(select={'day': "date(created)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
            .values('day', 'count')
        )
        
        # Weekly trend
        weekly_trend = list(
            recent_configs.extra(select={'week': "date_trunc('week', created)"})
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
            .values('week', 'count')
        )
        
        # Monthly trend
        monthly_trend = list(
            recent_configs.extra(select={'month': "date_trunc('month', created)"})
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
            .values('month', 'count')
        )
        
        trends = {
            'daily_trend': daily_trend,
            'weekly_trend': weekly_trend,
            'monthly_trend': monthly_trend
        }
        
        serializer = TrendSerializer(trends)
        return Response(serializer.data)
    
    @extend_schema(summary='Get Audit Configuration Filters')
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get audit configuration filters"""
        queryset = self.get_queryset()
        
        # Available filters
        filters = {
            'is_active': list(queryset.values('is_active').distinct()),
            'default_retention_days': list(queryset.values('default_retention_days').distinct()),
            'default_archive_after_days': list(queryset.values('default_archive_after_days').distinct()),
            'default_data_classification': list(queryset.values('default_data_classification').distinct())
        }
        
        serializer = FilterSerializer(filters)
        return Response(serializer.data)
    
    @extend_schema(summary='Search Audit Configurations')
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search audit configurations"""
        queryset = self.get_queryset()
        
        # Search query
        query = request.query_params.get('query', '')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(created_by__email__icontains=query) |
                Q(created_by__username__icontains=query)
            )
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Sort Audit Configurations')
    @action(detail=False, methods=['get'])
    def sort(self, request):
        """Sort audit configurations"""
        queryset = self.get_queryset()
        
        # Sort by field
        sort_by = request.query_params.get('sort_by', 'name')
        if sort_by in self.ordering_fields:
            queryset = queryset.order_by(sort_by)
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Paginate Audit Configurations')
    @action(detail=False, methods=['get'])
    def paginate(self, request):
        """Paginate audit configurations"""
        queryset = self.get_queryset()
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(summary='Export Audit Configurations')
    @action(detail=False, methods=['post'])
    def export(self, request):
        """Export audit configurations"""
        serializer = ExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        format_type = serializer.validated_data.get('format', 'json')
        include_details = serializer.validated_data.get('include_details', True)
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Apply filters
        queryset = self.get_queryset()
        if filter_criteria:
            # This would require implementing filter logic based on filter_criteria
            # For now, we'll just return a placeholder
            pass
        
        # Export data
        # This would require implementing export logic based on format_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit configurations export initiated'),
            'format': format_type,
            'include_details': include_details,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Import Audit Configurations')
    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """Import audit configurations"""
        serializer = ImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data.get('file')
        format_type = serializer.validated_data.get('format')
        overwrite_existing = serializer.validated_data.get('overwrite_existing', False)
        
        # Import data
        # This would require implementing import logic based on format_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit configurations import initiated'),
            'file': file.name,
            'format': format_type,
            'overwrite_existing': overwrite_existing
        })
    
    @extend_schema(summary='Sync Audit Configurations')
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Sync audit configurations"""
        serializer = SyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        source = serializer.validated_data.get('source')
        destination = serializer.validated_data.get('destination')
        sync_type = serializer.validated_data.get('sync_type', 'incremental')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Sync data
        # This would require implementing sync logic based on source/destination/sync_type
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit configurations sync initiated'),
            'source': source,
            'destination': destination,
            'sync_type': sync_type,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Validate Audit Configurations')
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate audit configurations"""
        serializer = ValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validation_rules = serializer.validated_data.get('validation_rules')
        fix_errors = serializer.validated_data.get('fix_errors', False)
        
        # Validate data
        # This would require implementing validation logic based on validation_rules
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit configurations validation initiated'),
            'validation_rules': validation_rules,
            'fix_errors': fix_errors
        })
    
    @extend_schema(summary='Transform Audit Configurations')
    @action(detail=False, methods=['post'])
    def transform(self, request):
        """Transform audit configurations"""
        serializer = TransformSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        transformation_rules = serializer.validated_data.get('transformation_rules')
        output_format = serializer.validated_data.get('output_format', 'json')
        
        # Transform data
        # This would require implementing transformation logic based on transformation_rules
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit configurations transformation initiated'),
            'transformation_rules': transformation_rules,
            'output_format': output_format
        })
    
    @extend_schema(summary='Aggregate Audit Configurations')
    @action(detail=False, methods=['post'])
    def aggregate(self, request):
        """Aggregate audit configurations"""
        serializer = AggregateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        aggregation_functions = serializer.validated_data.get('aggregation_functions')
        group_by_fields = serializer.validated_data.get('group_by_fields', [])
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Aggregate data
        # This would require implementing aggregation logic based on aggregation_functions/group_by_fields
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit configurations aggregation initiated'),
            'aggregation_functions': aggregation_functions,
            'group_by_fields': group_by_fields,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Group Audit Configurations')
    @action(detail=False, methods=['post'])
    def group_by(self, request):
        """Group audit configurations"""
        serializer = GroupBySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        group_by_field = serializer.validated_data.get('group_by_field')
        aggregation_function = serializer.validated_data.get('aggregation_function', 'count')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Group data
        # This would require implementing grouping logic based on group_by_field/aggregation_function
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit configurations grouping initiated'),
            'group_by_field': group_by_field,
            'aggregation_function': aggregation_function,
            'filter_criteria': filter_criteria
        })
    
    @extend_schema(summary='Join Audit Configurations')
    @action(detail=False, methods=['post'])
    def join(self, request):
        """Join audit configurations with other data sources"""
        serializer = JoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        join_type = serializer.validated_data.get('join_type')
        join_field = serializer.validated_data.get('join_field')
        join_with = serializer.validated_data.get('join_with')
        filter_criteria = serializer.validated_data.get('filter_criteria', {})
        
        # Join data
        # This would require implementing join logic based on join_type/join_field/join_with
        # For now, we'll just return a placeholder
        return Response({
            'message': _('Audit configurations join initiated'),
            'join_type': join_type,
            'join_field': join_field,
            'join_with': join_with,
            'filter_criteria': filter_criteria
        })
