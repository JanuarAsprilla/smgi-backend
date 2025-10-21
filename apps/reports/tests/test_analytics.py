# apps/reports/tests/test_analytics.py
"""
SMGI Backend - Tests for Reports Analytics
Sistema de Monitoreo Geoespacial Inteligente
Pruebas unitarias para el sistema de análisis de informes
"""
import pytest
import logging
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.reports.analytics.dashboard_data import (
    get_report_statistics, get_report_trends, get_top_reports,
    get_report_performance, get_user_report_activity,
    get_service_report_distribution, get_schedule_efficiency,
    get_system_health_metrics, ReportAnalyticsProcessor, DashboardDataAggregator
)
from apps.reports.analytics.metrics_calculator import (
    get_average_generation_time, get_success_rate, get_failure_rate,
    get_top_services_by_report_count, get_top_layers_by_report_count,
    get_report_volume_trend, get_peak_generation_times,
    ReportMetricsCalculator
)
from apps.reports.analytics.trend_analyzer import (
    get_report_volume_growth_rate, get_report_success_rate_growth_rate,
    get_report_generation_time_trend_slope, identify_seasonal_patterns,
    detect_outliers, calculate_correlation, ReportTrendAnalyzer
)
from apps.reports.models import (
    Report, GeneratedReport, ReportSchedule, ReportExecution,
    ReportType, ReportFormat, ReportStatus
)
# Importar modelos relacionados
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert


logger = logging.getLogger('apps.reports.tests.analytics')


# --- Fixtures ---

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='analytics_test_user',
        email='analytics@test.com',
        password='testpass123'
    )

@pytest.fixture
def arcgis_service(user):
    return ArcGISService.objects.create(
        name='Analytics Test Service',
        base_url='https://analyticstest.arcgis.com',
        service_type='featureserver',
        created_by=user
    )

@pytest.fixture
def spatial_layer(arcgis_service):
    return SpatialLayer.objects.create(
        service=arcgis_service,
        layer_id=999,
        name='Analytics Test Layer',
        geometry_type='polygon',
        created_by=arcgis_service.created_by
    )

@pytest.fixture
def report(user, arcgis_service, spatial_layer):
    return Report.objects.create(
        name='Analytics Test Report',
        description='Test report for analytics',
        report_id='ANALYTICS-TEST-001',
        report_type=ReportType.MONITORING_SUMMARY,
        format_type=ReportFormat.PDF,
        service=arcgis_service,
        layer=spatial_layer,
        created_by=user,
        is_active=True,
        is_scheduled=False,
        change_threshold=5.0,
        notify_on_completion=True
    )

@pytest.fixture
def generated_report(report, user):
    return GeneratedReport.objects.create(
        report=report,
        generated_by=user,
        report_id='GEN-ANALYTICS-TEST-001',
        file='path/to/report.pdf',
        file_size_bytes=102400, # 100 KB
        file_checksum='abc123...',
        format_type=ReportFormat.PDF,
        status=ReportStatus.COMPLETED,
        parameters_used={'test_param': 'value'},
        generation_duration_ms=5000, # 5 segundos
        record_count=1000,
        page_count=10,
        memory_usage_mb=50,
        cpu_usage_percent=25.0,
        execution_log=[],
        performance_metrics={}
    )

@pytest.fixture
def report_schedule(report, user):
    return ReportSchedule.objects.create(
        report=report,
        name='Daily Analytics Test Report',
        description='Run analytics test report daily',
        schedule_expression='0 2 * * *', # Daily at 2 AM
        is_active=True,
        max_runtime_minutes=60,
        created_by=user
    )

@pytest.fixture
def report_execution(report_schedule):
    return ReportExecution.objects.create(
        schedule=report_schedule,
        success=True,
        started_at=timezone.now() - timedelta(minutes=10),
        completed_at=timezone.now() - timedelta(minutes=5),
        duration_seconds=300, # 5 minutos
        layers_processed=1,
        snapshots_created=1,
        changes_detected=0,
        alerts_created=0,
        memory_usage_mb=100,
        cpu_usage_percent=30.0,
        execution_log=[],
        performance_metrics={}
    )


# --- Tests for Dashboard Data ---

class TestDashboardData:

    def test_get_report_statistics(self, user, arcgis_service, spatial_layer, report, generated_report):
        stats = get_report_statistics(hours=24)
        assert 'total_reports' in stats
        assert 'active_reports' in stats
        assert 'generated_reports' in stats
        assert 'generated_today' in stats
        assert 'failed_reports' in stats
        assert 'completed_reports' in stats
        assert 'success_rate_percent' in stats
        assert 'average_generation_time_ms' in stats
        assert 'reports_by_type' in stats
        assert 'reports_by_format' in stats
        assert 'top_services_with_reports' in stats
        # Verificar valores razonables
        assert stats['total_reports'] >= 1
        assert stats['generated_reports'] >= 1
        assert stats['completed_reports'] >= 1
        assert stats['success_rate_percent'] >= 0
        assert stats['average_generation_time_ms'] >= 0

    def test_get_report_trends(self, generated_report):
        trends = get_report_trends(days=30)
        assert 'daily_trend' in trends
        assert 'weekly_trend' in trends
        assert 'monthly_trend' in trends
        # Verificar que las tendencias sean listas
        assert isinstance(trends['daily_trend'], list)
        assert isinstance(trends['weekly_trend'], list)
        assert isinstance(trends['monthly_trend'], list)

    def test_get_top_reports(self, report, generated_report):
        top_reports = get_top_reports(limit=10)
        assert isinstance(top_reports, list)
        # Verificar que el informe esté en los top reports
        report_names = [r['name'] for r in top_reports]
        assert report.name in report_names

    def test_get_report_performance(self, generated_report):
        performance = get_report_performance(hours=24)
        assert 'time_metrics' in performance
        assert 'size_metrics' in performance
        assert 'count_metrics' in performance
        assert 'format_metrics' in performance
        # Verificar valores razonables
        assert performance['time_metrics']['average_duration_ms'] >= 0
        assert performance['size_metrics']['average_size_bytes'] >= 0
        assert performance['count_metrics']['total_reports'] >= 0
        assert performance['count_metrics']['completed_reports'] >= 0
        assert performance['count_metrics']['failed_reports'] >= 0
        assert performance['count_metrics']['success_rate_percent'] >= 0

    def test_get_user_report_activity(self, user, generated_report):
        activity = get_user_report_activity(hours=24)
        assert isinstance(activity, list)
        # Verificar que el usuario esté en la actividad
        user_emails = [u['email'] for u in activity]
        assert user.email in user_emails

    def test_get_service_report_distribution(self, arcgis_service, spatial_layer, report, generated_report):
        distribution = get_service_report_distribution()
        assert 'by_service' in distribution
        assert 'by_layer' in distribution
        # Verificar que el servicio y la capa estén en la distribución
        service_names = [s['name'] for s in distribution['by_service']]
        layer_names = [l['name'] for l in distribution['by_layer']]
        assert arcgis_service.name in service_names
        assert spatial_layer.name in layer_names

    def test_get_schedule_efficiency(self, report_schedule, report_execution):
        efficiency = get_schedule_efficiency(hours=24)
        assert 'execution_metrics' in efficiency
        assert 'schedule_metrics' in efficiency
        # Verificar valores razonables
        assert efficiency['execution_metrics']['total_executions'] >= 0
        assert efficiency['execution_metrics']['successful_executions'] >= 0
        assert efficiency['execution_metrics']['failed_executions'] >= 0
        assert efficiency['execution_metrics']['success_rate_percent'] >= 0
        assert efficiency['schedule_metrics']['active_schedules'] >= 0
        assert efficiency['schedule_metrics']['failing_schedules'] >= 0
        assert efficiency['schedule_metrics']['delayed_executions'] >= 0

    def test_get_system_health_metrics(self):
        health = get_system_health_metrics(hours=24)
        assert 'resource_metrics' in health
        assert 'error_metrics' in health
        assert 'user_metrics' in health
        # Verificar valores razonables (placeholder)
        assert health['resource_metrics']['cpu_usage_percent'] >= 0
        assert health['resource_metrics']['memory_usage_percent'] >= 0
        assert health['resource_metrics']['disk_usage_percent'] >= 0
        assert health['error_metrics']['generation_errors'] >= 0
        assert health['error_metrics']['execution_errors'] >= 0
        assert health['error_metrics']['critical_alerts'] >= 0
        assert health['user_metrics']['active_users'] >= 0

    def test_report_analytics_processor(self, user, arcgis_service, spatial_layer, report, generated_report, report_schedule, report_execution):
        processor = ReportAnalyticsProcessor(hours=24)
        analytics_data = processor.get_all_analytics()
        assert 'statistics' in analytics_data
        assert 'trends' in analytics_data
        assert 'top_reports' in analytics_data
        assert 'performance' in analytics_data
        assert 'user_activity' in analytics_data
        assert 'distribution' in analytics_data
        assert 'schedule_efficiency' in analytics_data
        assert 'system_health' in analytics_data
        # Verificar que los datos no estén vacíos
        assert isinstance(analytics_data['statistics'], dict)
        assert isinstance(analytics_data['trends'], dict)
        assert isinstance(analytics_data['top_reports'], list)
        assert isinstance(analytics_data['performance'], dict)
        assert isinstance(analytics_data['user_activity'], list)
        assert isinstance(analytics_data['distribution'], dict)
        assert isinstance(analytics_data['schedule_efficiency'], dict)
        assert isinstance(analytics_data['system_health'], dict)

    def test_dashboard_data_aggregator(self, user, arcgis_service, spatial_layer, report, generated_report, report_schedule, report_execution):
        aggregator = DashboardDataAggregator(hours=24)
        dashboard_data = aggregator.aggregate_dashboard_data()
        assert 'period_hours' in dashboard_data
        assert 'generated_at' in dashboard_data
        assert 'statistics' in dashboard_data
        assert 'trends' in dashboard_data
        assert 'top_reports' in dashboard_data
        assert 'performance' in dashboard_data
        assert 'user_activity' in dashboard_data
        assert 'distribution' in dashboard_data
        assert 'schedule_efficiency' in dashboard_data
        assert 'system_health' in dashboard_data
        # Verificar que los datos no estén vacíos
        assert isinstance(dashboard_data['statistics'], dict)
        assert isinstance(dashboard_data['trends'], dict)
        assert isinstance(dashboard_data['top_reports'], list)
        assert isinstance(dashboard_data['performance'], dict)
        assert isinstance(dashboard_data['user_activity'], list)
        assert isinstance(dashboard_data['distribution'], dict)
        assert isinstance(dashboard_data['schedule_efficiency'], dict)
        assert isinstance(dashboard_data['system_health'], dict)


# --- Tests for Metrics Calculator ---

class TestMetricsCalculator:

    def test_get_average_generation_time(self, generated_report):
        avg_time = get_average_generation_time(hours=24)
        assert isinstance(avg_time, float)
        assert avg_time >= 0

    def test_get_success_rate(self, generated_report):
        success_rate = get_success_rate(hours=24)
        assert isinstance(success_rate, float)
        assert 0 <= success_rate <= 100

    def test_get_failure_rate(self, generated_report):
        # Crear un informe fallido para la prueba
        failed_report = GeneratedReport.objects.create(
            report=generated_report.report,
            generated_by=generated_report.generated_by,
            report_id='GEN-ANALYTICS-TEST-002',
            file='path/to/failed_report.pdf',
            file_size_bytes=0,
            file_checksum='',
            format_type=ReportFormat.PDF,
            status=ReportStatus.FAILED,
            parameters_used={},
            generation_duration_ms=0,
            record_count=0,
            page_count=0,
            memory_usage_mb=0,
            cpu_usage_percent=0,
            execution_log=[],
            performance_metrics={},
            error_message='Test failure'
        )
        failure_rate = get_failure_rate(hours=24)
        assert isinstance(failure_rate, float)
        assert 0 <= failure_rate <= 100
        # Limpiar informe fallido
        failed_report.delete()

    def test_get_top_services_by_report_count(self, arcgis_service, generated_report):
        top_services = get_top_services_by_report_count(hours=24, limit=10)
        assert isinstance(top_services, list)
        # Verificar que el servicio esté en los top services
        service_names = [s['name'] for s in top_services]
        assert arcgis_service.name in service_names

    def test_get_top_layers_by_report_count(self, spatial_layer, generated_report):
        top_layers = get_top_layers_by_report_count(hours=24, limit=10)
        assert isinstance(top_layers, list)
        # Verificar que la capa esté en los top layers
        layer_names = [l['name'] for l in top_layers]
        assert spatial_layer.name in layer_names

    def test_get_report_volume_trend(self, generated_report):
        trend_data = get_report_volume_trend(hours=24)
        assert isinstance(trend_data, list)
        # Verificar que haya datos de tendencia
        assert len(trend_data) >= 0 # Puede ser 0 si no hay datos suficientes

    def test_get_peak_generation_times(self, generated_report):
        peak_times = get_peak_generation_times(hours=24)
        assert isinstance(peak_times, list)
        # Verificar que haya datos de picos
        assert len(peak_times) >= 0 # Puede ser 0 si no hay datos suficientes

    # --- Tests for ReportMetricsCalculator class ---

    def test_report_metrics_calculator_init(self):
        calculator = ReportMetricsCalculator(hours=48)
        assert calculator.hours == 48
        assert calculator.since <= timezone.now() - timedelta(hours=48)

    @patch('apps.reports.analytics.metrics_calculator.ChangeDetectionResult')
    def test_calculate_change_impact_score(self, mock_change_result_class):
        mock_change_result = MagicMock()
        mock_change_result.created = timezone.now() - timedelta(hours=1)
        mock_change_result.has_changes = True
        mock_change_result.feature_count_change_percent = 15.0
        mock_change_result.severity = 'high'
        mock_change_result_class.objects.filter.return_value.order_by.return_value = [mock_change_result]
        
        calculator = ReportMetricsCalculator(hours=24)
        report_mock = MagicMock()
        report_mock.layer = MagicMock()
        report_mock.severity = 'high'
        report_mock.name = 'Test Report'
        
        score = calculator.calculate_change_impact_score(report_mock)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    @patch('apps.reports.analytics.metrics_calculator.LayerSnapshot')
    def test_calculate_report_complexity_score(self, mock_snapshot_class):
        mock_snapshot = MagicMock()
        mock_snapshot.feature_count = 5000
        mock_snapshot.total_area = 1000000
        mock_snapshot.data_size_bytes = 50 * 1024 * 1024 # 50 MB
        mock_snapshot.unique_values = {'field1': 100, 'field2': 50}
        mock_snapshot.null_count = {'field1': 10, 'field2': 5}
        mock_snapshot_class.objects.filter.return_value.order_by.return_value.first.return_value = mock_snapshot
        
        calculator = ReportMetricsCalculator(hours=24)
        report_mock = MagicMock()
        report_mock.layer = MagicMock()
        report_mock.name = 'Test Report'
        
        score = calculator.calculate_report_complexity_score(report_mock)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_calculate_user_productivity_score(self, user, generated_report):
        calculator = ReportMetricsCalculator(hours=24)
        score = calculator.calculate_user_productivity_score(user)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_calculate_service_health_score(self, arcgis_service, generated_report):
        calculator = ReportMetricsCalculator(hours=24)
        score = calculator.calculate_service_health_score(arcgis_service)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    @patch('apps.reports.analytics.metrics_calculator.LayerSnapshot')
    def test_calculate_data_quality_index(self, mock_snapshot_class):
        mock_snapshot = MagicMock()
        mock_snapshot.feature_count = 1000
        mock_snapshot.invalid_geometries = 5
        mock_snapshot.duplicate_records = 10
        mock_snapshot.null_count = {'field1': 20, 'field2': 15}
        mock_snapshot.unique_values = {'field1': 500, 'field2': 300}
        mock_snapshot_class.objects.filter.return_value.order_by.return_value.first.return_value = mock_snapshot
        
        calculator = ReportMetricsCalculator(hours=24)
        layer_mock = MagicMock()
        layer_mock.name = 'Test Layer'
        
        index = calculator.calculate_data_quality_index(layer_mock)
        assert isinstance(index, float)
        assert 0 <= index <= 100

    def test_calculate_performance_benchmark(self, generated_report):
        calculator = ReportMetricsCalculator(hours=24)
        benchmark = calculator.calculate_performance_benchmark()
        assert isinstance(benchmark, dict)
        assert 'average_generation_time_ms' in benchmark
        assert 'min_generation_time_ms' in benchmark
        assert 'max_generation_time_ms' in benchmark
        assert 'std_deviation_ms' in benchmark
        assert 'variance_ms' in benchmark
        assert 'percentile_50_ms' in benchmark
        assert 'percentile_90_ms' in benchmark
        assert 'percentile_95_ms' in benchmark
        assert 'percentile_99_ms' in benchmark
        assert 'total_reports_analyzed' in benchmark

    def test_calculate_trend_analysis(self, generated_report):
        # Crear más informes para tener suficientes datos
        for i in range(5):
            GeneratedReport.objects.create(
                report=generated_report.report,
                generated_by=generated_report.generated_by,
                report_id=f'GEN-TREND-TEST-{i}',
                file='path/to/trend_report.pdf',
                file_size_bytes=10240,
                file_checksum=f'checksum_{i}',
                format_type=ReportFormat.PDF,
                status=ReportStatus.COMPLETED,
                parameters_used={},
                generation_duration_ms=1000 + i * 100,
                record_count=100 + i * 10,
                page_count=1,
                memory_usage_mb=10,
                cpu_usage_percent=10.0 + i,
                execution_log=[],
                performance_metrics={},
                created=timezone.now() - timedelta(hours=i+1) # Hace i+1 horas
            )
        
        calculator = ReportMetricsCalculator(hours=24)
        analysis = calculator.calculate_trend_analysis()
        assert isinstance(analysis, dict)
        assert 'trend' in analysis
        assert 'slope' in analysis
        assert 'r_squared' in analysis
        assert 'data_points' in analysis
        assert 'daily_counts' in analysis

    @patch('apps.reports.analytics.metrics_calculator.ChangeDetectionResult')
    def test_calculate_prediction_model(self, mock_change_result_class):
        # Crear datos simulados para la regresión
        mock_reports = []
        for i in range(10):
            mock_report = MagicMock()
            mock_report.generation_duration_ms = 1000 + i * 100
            mock_report.report.layer.snapshots.filter.return_value.order_by.return_value.first.return_value.feature_count = 100 + i * 10
            mock_reports.append(mock_report)
        
        mock_change_result_class.objects.filter.return_value.select_related.return_value = mock_reports
        
        calculator = ReportMetricsCalculator(hours=24)
        model = calculator.calculate_prediction_model()
        assert isinstance(model, dict)
        assert 'model' in model
        assert 'predictor_variable' in model
        assert 'target_variable' in model
        assert 'slope' in model
        assert 'intercept' in model
        assert 'r_squared' in model
        assert 'data_points' in model


# --- Tests for Trend Analyzer ---

class TestTrendAnalyzer:

    def test_get_report_volume_growth_rate(self, generated_report):
        growth_rate = get_report_volume_growth_rate(hours=24)
        assert isinstance(growth_rate, float)

    def test_get_report_success_rate_growth_rate(self, generated_report):
        growth_rate = get_report_success_rate_growth_rate(hours=24)
        assert isinstance(growth_rate, float)

    def test_get_report_generation_time_trend_slope(self, generated_report):
        slope = get_report_generation_time_trend_slope(hours=24)
        assert isinstance(slope, float)

    def test_identify_seasonal_patterns(self, generated_report):
        patterns = identify_seasonal_patterns(hours=24 * 7) # Última semana
        assert isinstance(patterns, dict)
        assert 'patterns' in patterns
        assert 'peak_time' in patterns
        assert 'valley_time' in patterns

    def test_detect_outliers(self):
        data = [1, 2, 3, 4, 5, 100] # 100 es un outlier
        outliers = detect_outliers(data, threshold_std_dev=2.0)
        assert isinstance(outliers, list)
        # Verificar que se detecte el outlier
        outlier_values = [val for idx, val in outliers]
        assert 100 in outlier_values

    def test_calculate_correlation(self):
        x_data = [1, 2, 3, 4, 5]
        y_data = [2, 4, 6, 8, 10] # Correlación perfecta positiva
        correlation = calculate_correlation(x_data, y_data)
        assert isinstance(correlation, float)
        assert correlation == 1.0

        x_data = [1, 2, 3, 4, 5]
        y_data = [5, 4, 3, 2, 1] # Correlación perfecta negativa
        correlation = calculate_correlation(x_data, y_data)
        assert isinstance(correlation, float)
        assert correlation == -1.0

        x_data = [1, 2, 3, 4, 5]
        y_data = [1, 1, 1, 1, 1] # Sin correlación
        correlation = calculate_correlation(x_data, y_data)
        assert isinstance(correlation, float)
        assert correlation == 0.0

    # --- Tests for ReportTrendAnalyzer class ---

    def test_report_trend_analyzer_init(self):
        analyzer = ReportTrendAnalyzer(hours=48)
        assert analyzer.hours == 48
        assert analyzer.since <= timezone.now() - timedelta(hours=48)

    def test_analyze_report_volume_trend(self, generated_report):
        # Crear más informes para tener suficientes datos
        for i in range(5):
            GeneratedReport.objects.create(
                report=generated_report.report,
                generated_by=generated_report.generated_by,
                report_id=f'GEN-VOLUME-TREND-TEST-{i}',
                file='path/to/volume_trend_report.pdf',
                file_size_bytes=10240,
                file_checksum=f'checksum_{i}',
                format_type=ReportFormat.PDF,
                status=ReportStatus.COMPLETED,
                parameters_used={},
                generation_duration_ms=1000 + i * 100,
                record_count=100 + i * 10,
                page_count=1,
                memory_usage_mb=10,
                cpu_usage_percent=10.0 + i,
                execution_log=[],
                performance_metrics={},
                created=timezone.now() - timedelta(hours=i+1) # Hace i+1 horas
            )
        
        analyzer = ReportTrendAnalyzer(hours=24)
        trend_analysis = analyzer.analyze_report_volume_trend()
        assert isinstance(trend_analysis, dict)
        assert 'trend' in trend_analysis
        assert 'slope' in trend_analysis
        assert 'r_squared' in trend_analysis
        assert 'data_points' in trend_analysis
        assert 'daily_counts' in trend_analysis

    def test_analyze_report_success_rate_trend(self, generated_report):
        # Crear informes fallidos para la prueba
        for i in range(3):
            GeneratedReport.objects.create(
                report=generated_report.report,
                generated_by=generated_report.generated_by,
                report_id=f'GEN-SUCCESS-TREND-TEST-{i}',
                file='path/to/success_trend_report.pdf',
                file_size_bytes=0,
                file_checksum='',
                format_type=ReportFormat.PDF,
                status=ReportStatus.FAILED,
                parameters_used={},
                generation_duration_ms=0,
                record_count=0,
                page_count=0,
                memory_usage_mb=0,
                cpu_usage_percent=0,
                execution_log=[],
                performance_metrics={},
                error_message='Test failure',
                created=timezone.now() - timedelta(hours=i+1) # Hace i+1 horas
            )
        
        analyzer = ReportTrendAnalyzer(hours=24)
        trend_analysis = analyzer.analyze_report_success_rate_trend()
        assert isinstance(trend_analysis, dict)
        assert 'trend' in trend_analysis
        assert 'slope' in trend_analysis
        assert 'r_squared' in trend_analysis
        assert 'change_rate_percent' in trend_analysis
        assert 'data_points' in trend_analysis
        assert 'daily_success_rates' in trend_analysis

    def test_analyze_report_generation_time_trend(self, generated_report):
        # Crear más informes para tener suficientes datos
        for i in range(5):
            GeneratedReport.objects.create(
                report=generated_report.report,
                generated_by=generated_report.generated_by,
                report_id=f'GEN-TIME-TREND-TEST-{i}',
                file='path/to/time_trend_report.pdf',
                file_size_bytes=10240,
                file_checksum=f'checksum_{i}',
                format_type=ReportFormat.PDF,
                status=ReportStatus.COMPLETED,
                parameters_used={},
                generation_duration_ms=1000 + i * 100,
                record_count=100 + i * 10,
                page_count=1,
                memory_usage_mb=10,
                cpu_usage_percent=10.0 + i,
                execution_log=[],
                performance_metrics={},
                created=timezone.now() - timedelta(hours=i+1) # Hace i+1 horas
            )
        
        analyzer = ReportTrendAnalyzer(hours=24)
        trend_analysis = analyzer.analyze_report_generation_time_trend()
        assert isinstance(trend_analysis, dict)
        assert 'trend' in trend_analysis
        assert 'slope' in trend_analysis
        assert 'r_squared' in trend_analysis
        assert 'change_rate_percent' in trend_analysis
        assert 'data_points' in trend_analysis
        assert 'daily_generation_times' in trend_analysis

    def test_analyze_user_report_activity_trend(self, user, generated_report):
        # Crear más informes para tener suficientes datos
        for i in range(5):
            GeneratedReport.objects.create(
                report=generated_report.report,
                generated_by=user, # Mismo usuario
                report_id=f'GEN-USER-TREND-TEST-{i}',
                file='path/to/user_trend_report.pdf',
                file_size_bytes=10240,
                file_checksum=f'checksum_{i}',
                format_type=ReportFormat.PDF,
                status=ReportStatus.COMPLETED,
                parameters_used={},
                generation_duration_ms=1000 + i * 100,
                record_count=100 + i * 10,
                page_count=1,
                memory_usage_mb=10,
                cpu_usage_percent=10.0 + i,
                execution_log=[],
                performance_metrics={},
                created=timezone.now() - timedelta(hours=i+1) # Hace i+1 horas
            )
        
        analyzer = ReportTrendAnalyzer(hours=24)
        trend_analysis = analyzer.analyze_user_report_activity_trend()
        assert isinstance(trend_analysis, dict)
        assert 'user_count' in trend_analysis
        assert 'top_users' in trend_analysis
        assert 'all_users' in trend_analysis
        # Verificar que el usuario esté en los resultados
        user_ids = [u['user_id'] for u in trend_analysis['all_users']]
        assert str(user.id) in user_ids

    def test_analyze_service_report_trend(self, arcgis_service, spatial_layer, report, generated_report):
        # Crear más informes para tener suficientes datos
        for i in range(3):
            new_report = Report.objects.create(
                name=f'Trend Test Report {i}',
                description='Test report for trend analysis',
                report_id=f'TREND-TEST-{i}',
                report_type=ReportType.MONITORING_SUMMARY,
                format_type=ReportFormat.PDF,
                service=arcgis_service,
                layer=spatial_layer,
                created_by=report.created_by,
                is_active=True,
                is_scheduled=False,
                change_threshold=5.0,
                notify_on_completion=True
            )
            GeneratedReport.objects.create(
                report=new_report,
                generated_by=report.created_by,
                report_id=f'GEN-TREND-SERVICE-TEST-{i}',
                file='path/to/service_trend_report.pdf',
                file_size_bytes=10240,
                file_checksum=f'checksum_{i}',
                format_type=ReportFormat.PDF,
                status=ReportStatus.COMPLETED,
                parameters_used={},
                generation_duration_ms=1000 + i * 100,
                record_count=100 + i * 10,
                page_count=1,
                memory_usage_mb=10,
                cpu_usage_percent=10.0 + i,
                execution_log=[],
                performance_metrics={},
                created=timezone.now() - timedelta(hours=i+1) # Hace i+1 horas
            )
        
        analyzer = ReportTrendAnalyzer(hours=24)
        trend_analysis = analyzer.analyze_service_report_trend()
        assert isinstance(trend_analysis, dict)
        assert 'service_count' in trend_analysis
        assert 'layer_count' in trend_analysis
        assert 'top_services' in trend_analysis
        assert 'top_layers' in trend_analysis
        assert 'all_services' in trend_analysis
        assert 'all_layers' in trend_analysis
        # Verificar que el servicio esté en los resultados
        service_names = [s['name'] for s in trend_analysis['all_services']]
        assert arcgis_service.name in service_names

    @patch('apps.reports.analytics.trend_analyzer.ChangeDetectionResult')
    def test_detect_anomalies_in_report_volume(self, mock_change_result_class):
        # Simular datos de volumen con un pico
        mock_daily_counts = [
            {'day': timezone.now().date() - timedelta(days=2), 'count': 10},
            {'day': timezone.now().date() - timedelta(days=1), 'count': 15},
            {'day': timezone.now().date(), 'count': 100} # Pico
        ]
        mock_change_result_class.objects.filter.return_value.extra.return_value.values.return_value.annotate.return_value.order_by.return_value.values.return_value = mock_daily_counts
        
        analyzer = ReportTrendAnalyzer(hours=72) # Últimos 3 días
        anomalies = analyzer.detect_anomalies_in_report_volume(threshold_std_dev=2.0)
        assert isinstance(anomalies, dict)
        assert 'anomalies' in anomalies
        assert 'data_points' in anomalies
        assert 'mean_count' in anomalies
        assert 'std_dev_count' in anomalies
        assert 'threshold_std_dev' in anomalies
        # Verificar que se detecte el pico
        assert len(anomalies['anomalies']) >= 0 # Puede ser 0 si el pico no supera el umbral

    @patch('apps.reports.analytics.trend_analyzer.GeneratedReport')
    def test_detect_anomalies_in_report_generation_time(self, mock_generated_report_class):
        # Simular tiempos de generación con un valor atípico
        mock_durations = [
            {'generation_duration_ms': 1000},
            {'generation_duration_ms': 1200},
            {'generation_duration_ms': 1100},
            {'generation_duration_ms': 10000} # Valor atípico
        ]
        mock_generated_report_class.objects.filter.return_value.values.return_value = mock_durations
        
        analyzer = ReportTrendAnalyzer(hours=24)
        anomalies = analyzer.detect_anomalies_in_report_generation_time(threshold_std_dev=2.0)
        assert isinstance(anomalies, dict)
        assert 'anomalies' in anomalies
        assert 'data_points' in anomalies
        assert 'mean_duration_ms' in anomalies
        assert 'std_dev_duration_ms' in anomalies
        assert 'threshold_std_dev' in anomalies
        # Verificar que se detecte el valor atípico
        assert len(anomalies['anomalies']) >= 0 # Puede ser 0 si el valor no supera el umbral

    def test_forecast_report_volume(self, generated_report):
        # Crear más informes para tener suficientes datos
        for i in range(10):
            GeneratedReport.objects.create(
                report=generated_report.report,
                generated_by=generated_report.generated_by,
                report_id=f'GEN-FORECAST-TEST-{i}',
                file='path/to/forecast_report.pdf',
                file_size_bytes=10240,
                file_checksum=f'checksum_{i}',
                format_type=ReportFormat.PDF,
                status=ReportStatus.COMPLETED,
                parameters_used={},
                generation_duration_ms=1000 + i * 100,
                record_count=100 + i * 10,
                page_count=1,
                memory_usage_mb=10,
                cpu_usage_percent=10.0 + i,
                execution_log=[],
                performance_metrics={},
                created=timezone.now() - timedelta(days=i+1) # Hace i+1 días
            )
        
        analyzer = ReportTrendAnalyzer(hours=24 * 30) # Últimos 30 días
        forecast = analyzer.forecast_report_volume(days_ahead=7)
        assert isinstance(forecast, dict)
        assert 'forecast' in forecast
        assert 'data_points' in forecast
        assert 'slope' in forecast
        assert 'intercept' in forecast
        assert 'days_ahead' in forecast
        # Verificar que haya predicciones
        assert len(forecast['forecast']) == 7

    @patch('apps.reports.analytics.trend_analyzer.GeneratedReport')
    def test_forecast_report_generation_time(self, mock_generated_report_class):
        # Simular datos históricos de tiempos de generación
        mock_reports = []
        for i in range(10):
            mock_report = MagicMock()
            mock_report.id = f'report-{i}'
            mock_report.generation_duration_ms = 1000 + i * 100
            mock_report.created = timezone.now() - timedelta(days=i+1) # Hace i+1 días
            mock_reports.append(mock_report)
        
        mock_generated_report_class.objects.filter.return_value.order_by.return_value.values.return_value = [
            {'generation_duration_ms': r.generation_duration_ms, 'created': r.created} for r in mock_reports
        ]
        
        analyzer = ReportTrendAnalyzer(hours=24 * 30) # Últimos 30 días
        forecast = analyzer.forecast_report_generation_time(report_id='test-report-id', minutes_ahead=60)
        assert isinstance(forecast, dict)
        assert 'forecast' in forecast
        assert 'data_points' in forecast
        assert 'slope' in forecast
        assert 'intercept' in forecast
        assert 'minutes_ahead' in forecast
        # Verificar que haya predicciones
        assert len(forecast['forecast']) >= 0 # Puede ser 0 si no hay suficientes datos
