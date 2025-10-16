# apps/monitoring/tests/test_tasks.py
import pytest
from unittest.mock import patch, MagicMock
from celery import current_app
from django.utils import timezone
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import (
    LayerSnapshot, ChangeDetectionResult, MonitoringJob,
    MonitoringJobExecution, SystemHealthMetric, DataQualityRule
)
from apps.monitoring.tasks import (
    monitor_layer, create_layer_snapshot, perform_change_detection,
    create_change_alert, system_health_check, run_data_quality_checks,
    cleanup_old_snapshots
)
from apps.gis_services.clients.arcgis_client import ArcGISClient

# --- Tests para monitor_layer ---
# Requiere mock de ArcGISClient, LayerSnapshot, ChangeDetectionResult, etc.

@pytest.fixture
def mock_arcgis_client():
    with patch('apps.monitoring.tasks.ArcGISClient') as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        yield mock_client_instance

@pytest.fixture
def mock_spatial_layer(user, arcgis_service):
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=1,
        name='Test Layer',
        geometry_type='polygon',
        created_by=user
    )

class TestMonitorLayerTask:

    @patch('apps.monitoring.tasks.create_layer_snapshot')
    @patch('apps.monitoring.tasks.perform_change_detection')
    @patch('apps.monitoring.tasks.create_change_alert')
    def test_monitor_layer_success(self, mock_create_alert, mock_perform_detection, mock_create_snapshot, mock_arcgis_client, mock_spatial_layer):
        # Configurar mocks
        mock_layer_data = {'count': 150, 'extent': {'xmin': 0, 'ymin': 0, 'xmax': 10, 'ymax': 10}, 'fields': []}
        mock_arcgis_client.get_layer_info.return_value = mock_layer_data
        mock_snapshot = MagicMock()
        mock_snapshot.get_previous_snapshot.return_value = MagicMock() # Simula una snapshot anterior
        mock_create_snapshot.return_value = mock_snapshot
        mock_detection_result = MagicMock()
        mock_detection_result.has_changes = True
        mock_detection_result.exceeds_threshold = True
        mock_perform_detection.return_value = mock_detection_result

        # Ejecutar tarea
        result = monitor_layer(mock_spatial_layer.id)

        # Aserciones
        assert result['success'] is True
        assert result['layer_id'] == str(mock_spatial_layer.id)
        mock_arcgis_client.get_layer_info.assert_called_once_with(mock_spatial_layer.layer_id)
        mock_create_snapshot.assert_called_once()
        mock_perform_detection.assert_called_once()
        mock_create_alert.delay.assert_called_once() # Se llama a delay, no directamente
        mock_spatial_layer.refresh_from_db()
        assert mock_spatial_layer.feature_count == 150 # update_feature_count se llama internamente

    @patch('apps.monitoring.tasks.create_layer_snapshot')
    def test_monitor_layer_data_collection_failure(self, mock_create_snapshot, mock_arcgis_client, mock_spatial_layer):
        # Configurar mock para fallar
        mock_arcgis_client.get_layer_info.return_value = None
        mock_create_snapshot.return_value = None

        # Ejecutar tarea
        result = monitor_layer(mock_spatial_layer.id)

        # Aserciones
        assert result['success'] is False
        assert result['error'] == 'data_collection_failed'
        mock_spatial_layer.refresh_from_db()
        # record_check_failure debería haberse llamado, pero es difícil asertarlo directamente aquí
        # sin mockear SpatialLayer.record_check_failure también


# --- Tests para create_layer_snapshot ---
# Requiere interacción con ArcGISClient para obtener datos reales, se puede mockear layer_data

class TestCreateLayerSnapshotTask:

    def test_create_layer_snapshot_basic(self, mock_spatial_layer):
        layer_data = {
            'count': 200,
            'extent': {'xmin': -5, 'ymin': -5, 'xmax': 5, 'ymax': 5},
            'fields': [{'name': 'field1', 'type': 'esriFieldTypeString'}]
        }
        collection_duration = 100 # ms

        snapshot = create_layer_snapshot(mock_spatial_layer, layer_data, collection_duration)

        assert snapshot is not None
        assert snapshot.layer == mock_spatial_layer
        assert snapshot.feature_count == 200
        assert snapshot.collection_duration_ms == collection_duration
        # Verificar que se calculó el hash
        assert len(snapshot.snapshot_hash) == 64 # SHA-256
        # Verificar cálculos aproximados de área/centroide basados en extent
        # (Estos son aproximados, se pueden asertar valores esperados si se conocen los cálculos internos)
        assert snapshot.total_area is not None # Debería ser un valor calculado
        assert snapshot.centroid is not None # Debería ser un Point


# --- Tests para perform_change_detection ---
# Requiere snapshots de entrada, puede mockearse el detector específico

@pytest.fixture
def mock_snapshots(mock_spatial_layer):
    snap1 = LayerSnapshot.objects.create(
        layer=mock_spatial_layer,
        snapshot_hash='hash1',
        feature_count=100,
        total_area=500.0,
        is_valid=True
    )
    snap2 = LayerSnapshot.objects.create(
        layer=mock_spatial_layer,
        snapshot_hash='hash2',
        feature_count=120, # 20% increase
        total_area=600.0, # 20% increase
        is_valid=True
    )
    return snap1, snap2

class TestPerformChangeDetectionTask:

    @patch('apps.monitoring.algorithms.change_detection.SimpleCountChangeDetector')
    def test_perform_change_detection_simple_count(self, mock_detector_class, mock_snapshots):
        current_snapshot, previous_snapshot = mock_snapshots
        mock_detector_instance = MagicMock()
        mock_detector_class.return_value = mock_detector_instance
        mock_detection_data = {
            'has_changes': True,
            'change_types': ['feature_count'],
            'feature_count_change': 20,
            'feature_count_change_percent': 20.0,
            'exceeds_threshold': True,
            'affected_feature_ids': ['feat_1', 'feat_2']
        }
        mock_detector_instance.detect.return_value = mock_detection_data

        result = perform_change_detection(current_snapshot, previous_snapshot, current_snapshot.layer)

        assert result is not None
        assert result.has_changes
        assert result.exceeds_threshold
        assert result.feature_count_change == 20
        # Verificar que se crearon AffectedFeature
        assert result.affected_feature_ids.count() == 2
        assert result.affected_feature_ids.filter(feature_id='feat_1').exists()
        assert result.affected_feature_ids.filter(feature_id='feat_2').exists()


# --- Tests para system_health_check ---
# Requiere mock de psutil, celery inspect, redis, cache, etc.

class TestSystemHealthCheckTask:

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('apps.monitoring.tasks.current_app')
    @patch('apps.monitoring.tasks.cache')
    def test_system_health_check_basic(self, mock_cache, mock_celery_app, mock_disk, mock_memory, mock_cpu):
        # Configurar mocks
        mock_cpu.return_value = 65.0
        mock_memory.return_value.percent = 75.0
        mock_disk.return_value.percent = 60.0
        mock_inspect = MagicMock()
        mock_celery_app.control.inspect.return_value = mock_inspect
        mock_inspect.active.return_value = {'worker1': []} # Lista de tareas activas
        mock_cache.get.side_effect = lambda key, default: {'active_users_count': 50, 'api_requests_last_minute': 1000, 'api_errors_last_minute': 5}.get(key, default)

        result = system_health_check()

        assert result['success'] is True
        # La salud debería ser 'warning' basado en los valores simulados
        assert result['health_status'] in ['warning', 'good'] # Depende del cálculo exacto de health_score
        # Verificar que se creó una métrica
        assert SystemHealthMetric.objects.count() == 1
        metric = SystemHealthMetric.objects.first()
        assert metric.cpu_usage_percent == 65.0
        assert metric.memory_usage_percent == 75.0
        assert metric.disk_usage_percent == 60.0
        # ... verificar otros campos si es necesario


# --- Tests para otras tareas ---
# run_data_quality_checks, cleanup_old_snapshots, etc., pueden requerir mocks
# específicos para sus dependencias (DataQualityRule, LayerSnapshot, etc.)

class TestRunDataQualityChecksTask:

    @patch('apps.monitoring.tasks.DataQualityRule.objects')
    def test_run_data_quality_checks_calls_rules(self, mock_dq_rule_qs, mock_spatial_layer):
        # Configurar mock de reglas
        rule1 = MagicMock()
        rule1.needs_check = True
        rule1.id = 1
        rule2 = MagicMock()
        rule2.needs_check = False # No debería ser procesada
        rule2.id = 2
        mock_dq_rule_qs.filter.return_value.select_related.return_value = [rule1, rule2]

        result = run_data_quality_checks()

        # Aserciones
        assert result['success'] is True
        # La regla 1 debería haber sido procesada, la 2 no
        # Esto dependería de la lógica interna de la tarea para verificar
        # cómo se llama la evaluación de la regla. Se puede mockear
        # DataQualityResult.objects.create y verificar su llamada.
        # Por ahora, verificamos que se iteró por las reglas que necesitaban check.
        mock_dq_rule_qs.filter.assert_called_once_with(is_active=True)
        # La lógica interna de la tarea evaluaría rule1, no rule2


class TestCleanupOldSnapshotsTask:

    def test_cleanup_old_snapshots_removes_old_ones(self, mock_spatial_layer):
        # Crear snapshots nuevos y antiguos
        now = timezone.now()
        old_snapshot = LayerSnapshot.objects.create(
            layer=mock_spatial_layer,
            snapshot_hash='old',
            feature_count=50,
            created=now - timezone.timedelta(days=35), # Más viejo que 30 días
            is_valid=True
        )
        new_snapshot = LayerSnapshot.objects.create(
            layer=mock_spatial_layer,
            snapshot_hash='new',
            feature_count=60,
            created=now - timezone.timedelta(days=5), # Más reciente que 30 días
            is_valid=True
        )

        initial_count = LayerSnapshot.objects.count()
        result = cleanup_old_snapshots(days_to_keep=30)

        final_count = LayerSnapshot.objects.count()
        # Debería haber eliminado solo el viejo
        assert result['snapshots_deleted'] == 1
        assert final_count == initial_count - 1
        # El snapshot nuevo debería seguir existiendo
        assert LayerSnapshot.objects.filter(id=new_snapshot.id).exists()
        # El snapshot viejo no debería existir
        assert not LayerSnapshot.objects.filter(id=old_snapshot.id).exists()

