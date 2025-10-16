# apps/monitoring/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import (
    LayerSnapshot, ChangeDetectionResult, MonitoringJob,
    MonitoringJobExecution, DataQualityRule, DataQualityResult,
    SystemHealthMetric, AffectedFeature, ChangeDetectionAlgorithm
)

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='testpass')

@pytest.fixture
def arcgis_service(user):
    return ArcGISService.objects.create(
        name='Test Service',
        base_url='https://test.arcgis.com',
        service_type='featureserver',
        created_by=user
    )

@pytest.fixture
def spatial_layer(arcgis_service):
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=1,
        name='Test Layer',
        geometry_type='polygon',
        created_by=arcgis_service.created_by
    )

@pytest.fixture
def layer_snapshot(spatial_layer):
    return LayerSnapshot.objects.create(
        layer=spatial_layer,
        snapshot_hash='abc123',
        feature_count=100,
        total_area=500.0,
        centroid=None, # O crear un punto real si es necesario
        is_valid=True
    )

@pytest.fixture
def change_detection_result(layer_snapshot):
    return ChangeDetectionResult.objects.create(
        current_snapshot=layer_snapshot,
        algorithm_used=ChangeDetectionAlgorithm.SIMPLE_COUNT,
        confidence_score=0.9,
        has_changes=True,
        feature_count_change=10,
        feature_count_change_percent=10.0,
        exceeds_threshold=True
    )

@pytest.fixture
def monitoring_job(user, spatial_layer):
    job = MonitoringJob.objects.create(
        name='Test Job',
        schedule_expression='15m', # Ejemplo de intervalo simple
        created_by=user
    )
    job.layers.add(spatial_layer)
    return job

@pytest.fixture
def data_quality_rule(spatial_layer):
    return DataQualityRule.objects.create(
        name='Test Rule',
        layer=spatial_layer,
        rule_type='completeness',
        rule_expression='field IS NOT NULL',
        warning_threshold=0.95,
        error_threshold=0.90,
        is_active=True
    )

class TestLayerSnapshotModel:

    def test_str_representation(self, layer_snapshot):
        expected_str = f"Snapshot of {layer_snapshot.layer.name} - {layer_snapshot.created.strftime('%Y-%m-%d %H:%M')}"
        assert str(layer_snapshot) == expected_str

    def test_compression_ratio_calculation(self, layer_snapshot):
        layer_snapshot.data_size_bytes = 1000
        layer_snapshot.compressed_size_bytes = 500
        assert layer_snapshot.compression_ratio == 50.0

        layer_snapshot.data_size_bytes = 0
        assert layer_snapshot.compression_ratio == 0

    def test_get_previous_snapshot(self, layer_snapshot):
        # Crear una instantánea anterior
        previous_snapshot = LayerSnapshot.objects.create(
            layer=layer_snapshot.layer,
            snapshot_hash='def456',
            feature_count=90,
            is_valid=True
        )
        # La instantánea original no debería tener anterior
        assert layer_snapshot.get_previous_snapshot() is None
        # Pero la anterior debería tener la original como siguiente si se crea después
        next_snapshot = LayerSnapshot.objects.create(
            layer=layer_snapshot.layer,
            snapshot_hash='ghi789',
            feature_count=110,
            is_valid=True
        )
        assert next_snapshot.get_previous_snapshot() == layer_snapshot

    def test_compare_with_previous(self, layer_snapshot):
        previous_snapshot = LayerSnapshot.objects.create(
            layer=layer_snapshot.layer,
            snapshot_hash='def456',
            feature_count=90,
            total_area=450.0,
            is_valid=True
        )
        comparison = layer_snapshot.compare_with_previous()
        assert comparison is None # Porque layer_snapshot es la primera

        next_snapshot = LayerSnapshot.objects.create(
            layer=layer_snapshot.layer,
            snapshot_hash='ghi789',
            feature_count=110,
            total_area=550.0,
            is_valid=True
        )
        comparison = next_snapshot.compare_with_previous()
        assert comparison is not None
        assert comparison['feature_count_change'] == 20 # 110 - 90
        assert comparison['area_change'] == 100.0 # 550.0 - 450.0


class TestChangeDetectionResultModel:

    def test_str_representation(self, change_detection_result):
        expected_str = f"{change_detection_result.layer.name} - Changes detected - {change_detection_result.created.strftime('%Y-%m-%d %H:%M')}"
        assert str(change_detection_result) == expected_str

    def test_layer_property(self, change_detection_result, spatial_layer):
        assert change_detection_result.layer == spatial_layer

    def test_total_features_affected(self, change_detection_result):
        change_detection_result.new_features = 5
        change_detection_result.deleted_features = 3
        change_detection_result.modified_features = 2
        assert change_detection_result.total_features_affected == 10 # 5 + 3 + 2

    def test_change_severity(self, change_detection_result):
        # Prueba con valores que den > 50 de severity_score
        change_detection_result.feature_count_change_percent = 60
        change_detection_result.confidence_score = 1.0
        assert change_detection_result.change_severity == 'critical'

        # Prueba con valores que den > 25 pero < 50
        change_detection_result.feature_count_change_percent = 30
        change_detection_result.confidence_score = 0.9
        assert change_detection_result.change_severity == 'high'

        # Prueba con valores que den > 10 pero < 25
        change_detection_result.feature_count_change_percent = 15
        change_detection_result.confidence_score = 0.8
        assert change_detection_result.change_severity == 'medium'

        # Prueba sin cambios
        change_detection_result.has_changes = False
        assert change_detection_result.change_severity == 'none'

    def test_get_change_summary(self, change_detection_result):
        summary = change_detection_result.get_change_summary()
        assert "Changes detected in layer properties." in summary
        # Ajustar la aserción si se cambian los valores de ejemplo
        # assert "Feature count increased by 10 (10.0%)" in summary


class TestMonitoringJobModel:

    def test_str_representation(self, monitoring_job):
        expected_str = f"{monitoring_job.name} ({monitoring_job.get_status_display()})"
        assert str(monitoring_job) == expected_str

    def test_is_overdue(self, monitoring_job):
        # No debería estar vencido si no tiene next_run o no está activo
        assert not monitoring_job.is_overdue

        # Establecer un next_run en el pasado
        monitoring_job.next_run = timezone.now() - timedelta(minutes=1)
        monitoring_job.is_active = True
        monitoring_job.save()
        assert monitoring_job.is_overdue

        # Establecer un next_run en el futuro
        monitoring_job.next_run = timezone.now() + timedelta(minutes=1)
        monitoring_job.save()
        assert not monitoring_job.is_overdue

    def test_total_layers(self, monitoring_job, spatial_layer):
        # Ya tiene una capa de la fixture
        assert monitoring_job.total_layers == 1
        # Añadir otra capa
        other_layer = SpatialLayer.objects.create(
            service=spatial_layer.service,
            layer_id=2,
            name='Other Layer',
            geometry_type='point',
            created_by=spatial_layer.created_by
        )
        monitoring_job.layers.add(other_layer)
        assert monitoring_job.total_layers == 2

    def test_calculate_next_run_simple_interval(self, monitoring_job):
        monitoring_job.schedule_expression = '30m'
        next_run = monitoring_job.calculate_next_run()
        expected_time = timezone.now() + timedelta(minutes=30)
        # Permitir un pequeño margen de error por tiempo de ejecución
        assert abs((next_run - expected_time).total_seconds()) < 2

        monitoring_job.schedule_expression = '2h'
        next_run = monitoring_job.calculate_next_run()
        expected_time = timezone.now() + timedelta(hours=2)
        assert abs((next_run - expected_time).total_seconds()) < 2

    def test_calculate_next_run_invalid_cron_uses_fallback(self, monitoring_job):
        monitoring_job.schedule_expression = 'invalid_cron'
        next_run = monitoring_job.calculate_next_run()
        expected_time = timezone.now() + timedelta(hours=1)
        assert abs((next_run - expected_time).total_seconds()) < 2

    # Tests para record_execution pueden requerir mocks de MonitoringJobExecution.objects.create
    # o una transacción de base de datos.


class TestDataQualityRuleModel:

    def test_str_representation(self, data_quality_rule, spatial_layer):
        expected_str = f"{data_quality_rule.name} ({spatial_layer.name})"
        assert str(data_quality_rule) == expected_str

    def test_needs_check(self, data_quality_rule):
        # Debería necesitar check si no está activo o no tiene last_check
        data_quality_rule.is_active = False
        assert data_quality_rule.needs_check

        data_quality_rule.is_active = True
        data_quality_rule.last_check = None
        assert data_quality_rule.needs_check

        # Debería necesitar check si ha pasado el tiempo de check_frequency
        data_quality_rule.last_check = timezone.now() - timedelta(hours=data_quality_rule.check_frequency_hours + 1)
        assert data_quality_rule.needs_check

        # No debería necesitar check si no ha pasado el tiempo
        data_quality_rule.last_check = timezone.now() - timedelta(hours=data_quality_rule.check_frequency_hours - 1)
        assert not data_quality_rule.needs_check

    def test_current_status(self, data_quality_rule):
        # Sin last_score
        data_quality_rule.last_score = None
        assert data_quality_rule.current_status == 'unknown'

        # Dentro del warning threshold
        data_quality_rule.last_score = 0.96
        assert data_quality_rule.current_status == 'good'

        # Dentro del error threshold pero por debajo del warning
        data_quality_rule.last_score = 0.92
        assert data_quality_rule.current_status == 'warning'

        # Por debajo del error threshold
        data_quality_rule.last_score = 0.85
        assert data_quality_rule.current_status == 'error'


class TestDataQualityResultModel:

    def test_str_representation(self, data_quality_rule):
        result = DataQualityResult.objects.create(
            rule=data_quality_rule,
            quality_score=0.9,
            passed=True
        )
        expected_str = f"{data_quality_rule.name} - Passed (0.90)"
        assert str(result) == expected_str

        result.passed = False
        result.quality_score = 0.8
        expected_str = f"{data_quality_rule.name} - Failed (0.80)"
        assert str(result) == expected_str

    def test_quality_grade(self):
        # Pruebas para diferentes puntajes y sus grados correspondientes
        grades_map = {
            1.0: 'A+', 0.95: 'A+', 0.94: 'A', 0.90: 'A', 0.89: 'B+', 0.85: 'B+', 0.84: 'B',
            0.80: 'B', 0.79: 'C+', 0.75: 'C+', 0.74: 'C', 0.70: 'C', 0.69: 'D+', 0.65: 'D+',
            0.64: 'D', 0.60: 'D', 0.59: 'F', 0.0: 'F'
        }
        for score, expected_grade in grades_map.items():
            result = DataQualityResult(quality_score=score)
            assert result.quality_grade == expected_grade

    def test_issue_count(self):
        result = DataQualityResult(issues_found=['issue1', 'issue2'])
        assert result.issue_count == 2

        result.issues_found = []
        assert result.issue_count == 0

        # Si no es una lista
        result.issues_found = 'not_a_list'
        assert result.issue_count == 0


class TestSystemHealthMetricModel:

    def test_str_representation(self):
        metric = SystemHealthMetric(
            overall_health='good',
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
            disk_usage_percent=70.0,
            db_connections_active=10,
            db_connections_idle=5,
            db_query_avg_time_ms=2.5,
            redis_memory_usage_mb=100,
            redis_connected_clients=5,
            redis_operations_per_sec=1000,
            celery_active_tasks=2,
            celery_pending_tasks=1,
            celery_failed_tasks=0,
            active_users=100,
            api_requests_per_minute=500,
            api_error_rate_percent=0.5
        )
        expected_str = f"System Health - Good - {metric.created.strftime('%Y-%m-%d %H:%M')}"
        assert str(metric) == expected_str

    def test_get_latest(self):
        # Crear métricas en diferentes momentos
        metric1 = SystemHealthMetric.objects.create(cpu_usage_percent=10)
        metric2 = SystemHealthMetric.objects.create(cpu_usage_percent=20)
        latest = SystemHealthMetric.get_latest()
        assert latest == metric2

    def test_get_average_metrics(self):
        now = timezone.now()
        # Crear métricas en los últimos 24 horas
        SystemHealthMetric.objects.create(
            cpu_usage_percent=10, memory_usage_percent=20, disk_usage_percent=30,
            db_query_avg_time_ms=1.0, api_error_rate_percent=0.1,
            created=now - timedelta(hours=1)
        )
        SystemHealthMetric.objects.create(
            cpu_usage_percent=30, memory_usage_percent=40, disk_usage_percent=50,
            db_query_avg_time_ms=3.0, api_error_rate_percent=0.3,
            created=now - timedelta(hours=2)
        )
        # Crear métrica fuera del rango
        SystemHealthMetric.objects.create(
            cpu_usage_percent=50, memory_usage_percent=60, disk_usage_percent=70,
            db_query_avg_time_ms=5.0, api_error_rate_percent=0.5,
            created=now - timedelta(days=2)
        )

        averages = SystemHealthMetric.get_average_metrics(hours=24)
        # Verificar que se hayan calculado promedios
        assert averages['avg_cpu'] == (10 + 30) / 2
        assert averages['avg_memory'] == (20 + 40) / 2
        assert averages['avg_disk'] == (30 + 50) / 2
        assert averages['avg_db_query_time'] == (1.0 + 3.0) / 2
        assert averages['avg_api_error_rate'] == (0.1 + 0.3) / 2

        # Verificar que no se incluyan métricas fuera del rango
        old_averages = SystemHealthMetric.get_average_metrics(hours=1)
        assert old_averages['avg_cpu'] == 10 # Solo la primera métrica está dentro del rango de 1 hora
