"""
Views for Geodata app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import DataSource, Layer, Feature, Dataset, SyncLog
from .serializers import (
    DataSourceSerializer,
    LayerSerializer,
    FeatureSerializer,
    FeatureGeoSerializer,
    FeatureCreateSerializer,
    DatasetSerializer,
    SyncLogSerializer,
)
from .filters import DataSourceFilter, LayerFilter, FeatureFilter
from .tasks import sync_data_source
from apps.users.permissions import IsAnalystOrAbove


class DataSourceViewSet(viewsets.ModelViewSet):
    """ViewSet for DataSource model."""
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DataSourceFilter
    
    def perform_create(self, serializer):
        """Set created_by field when creating."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by field when updating."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger manual sync for this data source."""
        data_source = self.get_object()
        task = sync_data_source.delay(data_source.id)
        return Response({
            'message': 'Sincronización iniciada',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)


class LayerViewSet(viewsets.ModelViewSet):
    """ViewSet for Layer model."""
    queryset = Layer.objects.select_related('data_source').all()
    serializer_class = LayerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LayerFilter
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(created_by=self.request.user)
            )
        return queryset


class FeatureViewSet(viewsets.ModelViewSet):
    """ViewSet for Feature model."""
    queryset = Feature.objects.select_related('layer').all()
    serializer_class = FeatureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = FeatureFilter
    
    def get_serializer_class(self):
        """Use GeoJSON serializer for geojson action."""
        if self.action == 'geojson':
            return FeatureGeoSerializer
        if self.action == 'create':
            return FeatureCreateSerializer
        return FeatureSerializer
    
    @action(detail=False, methods=['get'])
    def geojson(self, request):
        """Return features in GeoJSON format."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = FeatureGeoSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = FeatureGeoSerializer(queryset, many=True)
        return Response(serializer.data)


class DatasetViewSet(viewsets.ModelViewSet):
    """ViewSet for Dataset model."""
    queryset = Dataset.objects.prefetch_related('layers').all()
    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SyncLog model (read-only)."""
    queryset = SyncLog.objects.select_related('data_source').all()
    serializer_class = SyncLogSerializer
    permission_classes = [IsAuthenticated]
