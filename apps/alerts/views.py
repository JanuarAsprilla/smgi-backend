# apps/alerts/views.py
"""
SMGI Backend - Alerts Views
Sistema de Monitoreo Geoespacial Inteligente
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
from drf_spectacular.utils import extend_schema

from apps.alerts.models import (
    Alert, AlertAction, AlertStatus, AlertSeverity # Removido: AlertRule, NotificationChannel, AlertNotification
)
from apps.alerts.serializers import (
    AlertListSerializer, AlertDetailSerializer, AlertActionSerializer,
    AlertAcknowledgeSerializer, AlertResolveSerializer, AlertAssignSerializer,
    AlertCommentSerializer,
    # Removido: AlertRuleSerializer, NotificationChannelSerializer, AlertNotificationSerializer,
    AlertStatisticsSerializer, BulkAlertActionSerializer,
    # Asegurado: AlertDismissSerializer está importado
    AlertDismissSerializer
)


@extend_schema(tags=['Alerts'])
class AlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing alerts
    """
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category', 'severity', 'status', 'service', 'layer']
    search_fields = ['title', 'description', 'alert_id']
    ordering_fields = ['first_detected', 'severity', 'status']
    ordering = ['-first_detected']
    
    def get_queryset(self):
        queryset = Alert.objects.filter(is_removed=False)
        
        # Filter by assigned user
        assigned_to_me = self.request.query_params.get('assigned_to_me')
        if assigned_to_me == 'true':
            queryset = queryset.filter(assigned_to=self.request.user)
        
        # Filter by date range
        days = self.request.query_params.get('days')
        if days:
            since = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(first_detected__gte=since)
        
        return queryset.select_related(
            'service', 'layer', 'assigned_to',
            'acknowledged_by', 'resolved_by'
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AlertListSerializer
        return AlertDetailSerializer
    
    @extend_schema(
        summary='Acknowledge Alert',
        request=AlertAcknowledgeSerializer,
        responses={200: AlertDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        serializer = AlertAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if alert.acknowledge(request.user, notes):
            return Response({
                'message': _('Alert acknowledged successfully'),
                'alert': AlertDetailSerializer(alert).data
            })
        else:
            return Response({
                'error': _('Alert cannot be acknowledged in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary='Resolve Alert',
        request=AlertResolveSerializer,
        responses={200: AlertDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        serializer = AlertResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if alert.resolve(request.user, notes):
            return Response({
                'message': _('Alert resolved successfully'),
                'alert': AlertDetailSerializer(alert).data
            })
        else:
            return Response({
                'error': _('Alert cannot be resolved in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary='Dismiss Alert',
        # --- CORRECCIÓN: Alinear el request schema con el serializer usado ---
        request=AlertDismissSerializer, # Era AlertCommentSerializer
        responses={200: AlertDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss an alert"""
        alert = self.get_object()
        # Usar el nuevo serializer (ya estaba bien)
        serializer = AlertDismissSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if alert.dismiss(request.user, notes):
            return Response({
                'message': _('Alert dismissed successfully'),
                'alert': AlertDetailSerializer(alert).data
            })
        else:
            return Response({
                'error': _('Alert cannot be dismissed')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary='Assign Alert',
        request=AlertAssignSerializer,
        responses={200: AlertDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign alert to a user"""
        alert = self.get_object()
        serializer = AlertAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from apps.authentication.models import User
        try:
            user = User.objects.get(id=serializer.validated_data['user_id'])
            alert.assign_to(user, request.user)
            
            return Response({
                'message': _('Alert assigned successfully'),
                'alert': AlertDetailSerializer(alert).data
            })
        except User.DoesNotExist:
            return Response({
                'error': _('User not found')
            }, status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        summary='Add Comment',
        request=AlertCommentSerializer,
        responses={200: AlertActionSerializer}
    )
    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):
        """Add comment to alert"""
        alert = self.get_object()
        serializer = AlertCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comment = serializer.validated_data['comment']
        alert.add_comment(request.user, comment)
        
        return Response({
            'message': _('Comment added successfully')
        })
    
    @extend_schema(summary='Get Alert Actions')
    @action(detail=True, methods=['get'])
    def actions(self, request, pk=None):
        """Get alert action history"""
        alert = self.get_object()
        actions = alert.actions.all().order_by('-created')
        serializer = AlertActionSerializer(actions, many=True)
        
        return Response({
            'alert_id': str(alert.id),
            'action_count': actions.count(),
            'actions': serializer.data
        })
    
    # --- REMOVED: Endpoint 'notifications' as AlertNotification is not in alerts app ---
    # @extend_schema(summary='Get Alert Notifications')
    # @action(detail=True, methods=['get'])
    # def notifications(self, request, pk=None):
    #     """Get alert notifications history"""
    #     alert = self.get_object()
    #     notifications = alert.notifications.all().order_by('-sent_at')
    #     serializer = AlertNotificationSerializer(notifications, many=True)
    #     return Response({
    #         'alert_id': str(alert.id),
    #         'notification_count': notifications.count(),
    #         'notifications': serializer.data
    #     })
    
    @extend_schema(summary='Get Active Alerts')
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active alerts"""
        active_alerts = self.get_queryset().filter(
            status__in=[AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
        )
        
        serializer = AlertListSerializer(active_alerts, many=True)
        
        return Response({
            'count': active_alerts.count(),
            'alerts': serializer.data
        })
    
    @extend_schema(summary='Get Critical Alerts')
    @action(detail=False, methods=['get'])
    def critical(self, request):
        """Get critical alerts"""
        critical_alerts = self.get_queryset().filter(
            severity=AlertSeverity.CRITICAL,
            status__in=[AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
        )
        
        serializer = AlertListSerializer(critical_alerts, many=True)
        
        return Response({
            'count': critical_alerts.count(),
            'alerts': serializer.data
        })
    
    @extend_schema(summary='Get My Alerts')
    @action(detail=False, methods=['get'])
    def my_alerts(self, request):
        """Get alerts assigned to current user"""
        my_alerts = self.get_queryset().filter(
            assigned_to=request.user,
            status__in=[AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
        )
        
        serializer = AlertListSerializer(my_alerts, many=True)
        
        return Response({
            'count': my_alerts.count(),
            'alerts': serializer.data
        })
    
    @extend_schema(
        summary='Bulk Actions',
        request=BulkAlertActionSerializer,
        responses={200: {'type': 'object'}}
    )
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk action on multiple alerts"""
        serializer = BulkAlertActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        alert_ids = serializer.validated_data['alert_ids']
        action_type = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        
        alerts = Alert.objects.filter(id__in=alert_ids, is_removed=False)
        
        success_count = 0
        failed_count = 0
        
        for alert in alerts:
            try:
                if action_type == 'acknowledge':
                    alert.acknowledge(request.user, notes)
                elif action_type == 'resolve':
                    alert.resolve(request.user, notes)
                elif action_type == 'dismiss':
                    alert.dismiss(request.user, notes)
                
                success_count += 1
            except Exception:
                failed_count += 1
        
        return Response({
            'message': _('Bulk action completed'),
            'action': action_type,
            'total': len(alert_ids),
            'success': success_count,
            'failed': failed_count
        })
    
    @extend_schema(summary='Get Alert Statistics')
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get alert statistics"""
        queryset = self.get_queryset()
        
        # Time range
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        recent_alerts = queryset.filter(first_detected__gte=since)
        
        # Basic counts
        total_alerts = recent_alerts.count()
        active_alerts = recent_alerts.filter(
            status__in=[AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
        ).count()
        critical_alerts = recent_alerts.filter(severity=AlertSeverity.CRITICAL).count()
        unacknowledged = recent_alerts.filter(status=AlertStatus.ACTIVE).count()
        
        # Resolved today
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        resolved_today = recent_alerts.filter(
            status=AlertStatus.RESOLVED,
            resolved_at__gte=today_start
        ).count()
        
        # Average resolution time
        resolved_alerts = recent_alerts.filter(
            status=AlertStatus.RESOLVED,
            resolved_at__isnull=False
        )
        
        avg_resolution_time = 0
        if resolved_alerts.exists():
            total_time = sum(
                (alert.time_to_resolve or 0) for alert in resolved_alerts
            )
            avg_resolution_time = total_time / resolved_alerts.count() / 3600  # Convert to hours
        
        # Group by severity
        by_severity = recent_alerts.values('severity').annotate(count=Count('id'))
        alerts_by_severity = {item['severity']: item['count'] for item in by_severity}
        
        # Group by category
        by_category = recent_alerts.values('category').annotate(count=Count('id'))
        alerts_by_category = {item['category']: item['count'] for item in by_category}
        
        # Top services with alerts
        top_services = recent_alerts.filter(
            service__isnull=False
        ).values(
            'service__name'
        ).annotate(
            alert_count=Count('id')
        ).order_by('-alert_count')[:5]
        
        top_services_list = [
            {'service': item['service__name'], 'count': item['alert_count']}
            for item in top_services
        ]
        
        stats = {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'critical_alerts': critical_alerts,
            'unacknowledged_alerts': unacknowledged,
            'resolved_today': resolved_today,
            'average_resolution_time_hours': round(avg_resolution_time, 2),
            'alerts_by_severity': alerts_by_severity,
            'alerts_by_category': alerts_by_category,
            'top_services_with_alerts': top_services_list
        }
        
        serializer = AlertStatisticsSerializer(stats)
        return Response(serializer.data)


# --- REMOVED: ViewSets not belonging to 'alerts' app ---
# AlertRuleViewSet
# NotificationChannelViewSet
