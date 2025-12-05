"""
Views for Alerts app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from .models import (
    AlertChannel,
    AlertRule,
    Alert,
    AlertLog,
    AlertSubscription,
    AlertTemplate
)
from .serializers import (
    AlertChannelSerializer,
    AlertRuleSerializer,
    AlertSerializer,
    AlertDetailSerializer,
    AlertLogSerializer,
    AlertSubscriptionSerializer,
    AlertTemplateSerializer,
    AlertStatisticsSerializer,
)
from .filters import AlertRuleFilter, AlertFilter
from .tasks import send_alert, test_alert_channel
from apps.users.permissions import IsAnalystOrAbove
import logging

logger = logging.getLogger(__name__)


class AlertChannelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AlertChannel model.
    """
    queryset = AlertChannel.objects.all()
    serializer_class = AlertChannelSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test an alert channel."""
        channel = self.get_object()
        
        # Launch async task
        task = test_alert_channel.delay(
            channel.id,
            request.user.id
        )
        
        return Response({
            'message': 'Prueba de canal iniciada',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable a channel."""
        channel = self.get_object()
        channel.is_enabled = True
        channel.save()
        
        return Response({'message': 'Canal habilitado'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a channel."""
        channel = self.get_object()
        channel.is_enabled = False
        channel.save()
        
        return Response({'message': 'Canal deshabilitado'})
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get logs for this channel."""
        channel = self.get_object()
        logs = AlertLog.objects.filter(channel=channel).order_by('-sent_at')[:50]
        serializer = AlertLogSerializer(logs, many=True)
        return Response(serializer.data)


class AlertRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AlertRule model.
    """
    queryset = AlertRule.objects.prefetch_related('channels', 'recipients').all()
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AlertRuleFilter
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see rules from their projects
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(projects__created_by=self.request.user) |
                Q(created_by=self.request.user)
            ).distinct()
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable a rule."""
        rule = self.get_object()
        rule.is_enabled = True
        rule.save()
        
        return Response({'message': 'Regla habilitada'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a rule."""
        rule = self.get_object()
        rule.is_enabled = False
        rule.save()
        
        return Response({'message': 'Regla deshabilitada'})
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test an alert rule by sending a test alert."""
        rule = self.get_object()
        
        if not rule.can_trigger():
            return Response(
                {'error': 'La regla no puede ser activada en este momento (throttled o deshabilitada)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a test alert
        test_alert = Alert.objects.create(
            rule=rule,
            title=f'Prueba: {rule.name}',
            message='Esta es una alerta de prueba.',
            severity=rule.severity,
            alert_data={'test': True},
            created_by=request.user
        )
        
        # Send alert
        task = send_alert.delay(test_alert.id)
        
        return Response({
            'message': 'Alerta de prueba enviada',
            'alert_id': test_alert.id,
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['get'])
    def alerts(self, request, pk=None):
        """Get alerts triggered by this rule."""
        rule = self.get_object()
        alerts = rule.alerts.filter(is_active=True).order_by('-created_at')
        
        page = self.paginate_queryset(alerts)
        if page is not None:
            serializer = AlertSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)


class AlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Alert model.
    """
    queryset = Alert.objects.select_related('rule', 'detection', 'monitor').all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AlertFilter
    
    def get_serializer_class(self):
        """Return detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return AlertDetailSerializer
        return AlertSerializer
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see alerts from their projects or directed to them
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(monitor__project__created_by=self.request.user) |
                Q(rule__recipients=self.request.user) |
                Q(created_by=self.request.user)
            ).distinct()
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert."""
        alert = self.get_object()
        
        if not alert.can_acknowledge():
            return Response(
                {'error': 'La alerta no puede ser reconocida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if alert.acknowledge(request.user):
            return Response({'message': 'Alerta reconocida'})
        
        return Response(
            {'error': 'Error al reconocer la alerta'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert."""
        alert = self.get_object()
        
        if not alert.can_resolve():
            return Response(
                {'error': 'La alerta no puede ser resuelta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notes = request.data.get('notes', '')
        if alert.resolve(request.user, notes):
            return Response({'message': 'Alerta resuelta'})
        
        return Response(
            {'error': 'Error al resolver la alerta'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend an alert."""
        alert = self.get_object()
        
        # Launch async task
        task = send_alert.delay(alert.id, resend=True)
        
        return Response({
            'message': 'Reenvío de alerta iniciado',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard data with recent alerts."""
        queryset = self.get_queryset()
        
        # Recent alerts
        recent = queryset.order_by('-created_at')[:10]
        
        # Statistics
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'sent': queryset.filter(status='sent').count(),
            'failed': queryset.filter(status='failed').count(),
            'acknowledged': queryset.filter(status='acknowledged').count(),
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
            'recent_alerts': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def my_alerts(self, request):
        """Get alerts for current user."""
        queryset = self.get_queryset().filter(
            rule__recipients=request.user
        ).order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AlertLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AlertLog model (read-only).
    """
    queryset = AlertLog.objects.select_related('alert', 'channel', 'recipient').all()
    serializer_class = AlertLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users only see their own logs
        if not self.request.user.is_staff:
            queryset = queryset.filter(recipient=self.request.user)
        
        return queryset


class AlertSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AlertSubscription model.
    """
    queryset = AlertSubscription.objects.prefetch_related('channels', 'projects', 'monitors').all()
    serializer_class = AlertSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter to only current user's subscriptions."""
        return super().get_queryset().filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set user and created_by when creating."""
        serializer.save(user=self.request.user, created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's subscription."""
        subscription = self.get_queryset().first()
        
        if not subscription:
            return Response(
                {'message': 'No hay suscripción configurada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)


class AlertTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AlertTemplate model.
    """
    queryset = AlertTemplate.objects.all()
    serializer_class = AlertTemplateSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """Get default templates."""
        templates = self.get_queryset().filter(is_default=True)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)


class AlertStatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet for alert statistics.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        description='Obtener estadísticas generales de alertas',
        responses={200: dict},
        tags=['Alerts - Statistics']
    )
    def list(self, request):
        """Get general alert statistics."""
        # Filter by user if not staff
        if request.user.is_staff:
            alerts = Alert.objects.filter(is_active=True)
            rules = AlertRule.objects.filter(is_active=True)
        else:
            alerts = Alert.objects.filter(
                Q(monitor__project__created_by=request.user) |
                Q(rule__recipients=request.user),
                is_active=True
            ).distinct()
            rules = AlertRule.objects.filter(
                Q(projects__created_by=request.user) |
                Q(created_by=request.user),
                is_active=True
            ).distinct()
        
        # Calculate statistics
        stats = {
            'total_alerts': alerts.count(),
            'pending_alerts': alerts.filter(status='pending').count(),
            'sent_alerts': alerts.filter(status='sent').count(),
            'failed_alerts': alerts.filter(status='failed').count(),
            'acknowledged_alerts': alerts.filter(status='acknowledged').count(),
            'alerts_by_severity': {
                'critical': alerts.filter(severity='critical').count(),
                'high': alerts.filter(severity='high').count(),
                'medium': alerts.filter(severity='medium').count(),
                'low': alerts.filter(severity='low').count(),
            },
            'alerts_by_status': {
                'pending': alerts.filter(status='pending').count(),
                'sent': alerts.filter(status='sent').count(),
                'failed': alerts.filter(status='failed').count(),
                'acknowledged': alerts.filter(status='acknowledged').count(),
                'resolved': alerts.filter(status='resolved').count(),
            },
            'recent_alerts': [],
            'top_rules': []
        }
        
        # Recent alerts
        recent = alerts.order_by('-created_at')[:5]
        stats['recent_alerts'] = [
            {
                'id': a.id,
                'title': a.title,
                'severity': a.severity,
                'status': a.status,
                'created_at': a.created_at
            }
            for a in recent
        ]
        
        # Top rules by trigger count
        top_rules = rules.annotate(
            alert_count=Count('alerts')
        ).order_by('-alert_count')[:5]
        
        stats['top_rules'] = [
            {
                'id': r.id,
                'name': r.name,
                'alert_count': r.alert_count
            }
            for r in top_rules
        ]
        
        serializer = AlertStatisticsSerializer(stats)
        return Response(serializer.data)
