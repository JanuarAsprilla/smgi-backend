# apps/reports/analytics/metrics_calculator.py
"""
SMGI Backend - Reports Metrics Calculator
Sistema de Monitoreo Geoespacial Inteligente
Calculadora de métricas avanzadas para el sistema de informes
"""
import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from django.db.models import Avg, Count, Sum, Min, Max, StdDev, Variance, Q, F
from django.utils.translation import gettext_lazy as _

from apps.reports.models import (
    Report, GeneratedReport, ReportSchedule, ReportExecution,
    ReportType, ReportFormat, ReportStatus
)
# Importar modelos relacionados
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert


logger = logging.getLogger('apps.reports.analytics.metrics')


class ReportMetricsCalculator:
    """
    Calculadora de métricas avanzadas para el sistema de informes.
    """

    def __init__(self, hours: int = 24):
        """
        Inicializa la calculadora de métricas.

        Args:
            hours (int): Número de horas hacia atrás para calcular métricas. Por defecto 24.
        """
        self.hours = hours
        self.since = timezone.now() - timedelta(hours=hours)
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    def calculate_change_impact_score(self, report: Report) -> float:
        """
        Calcula una puntuación de impacto basada en el cambio porcentual,
        severidad, frecuencia, etc.

        Args:
            report (Report): Instancia del informe.

        Returns:
            float: Puntuación de impacto (0.0 a 100.0).
        """
        self.logger.info(f"Calculating change impact score for report {report.name}")
        
        try:
            # Obtener cambios recientes relacionados con este informe
            recent_changes = ChangeDetectionResult.objects.filter(
                alert__layer=report.layer,
                created__gte=self.since,
                has_changes=True,
                is_removed=False
            ).order_by('-created')
            
            if not recent_changes.exists():
                self.logger.info(f"No recent changes found for report {report.name}")
                return 0.0
            
            # Calcular métricas de cambio
            total_changes = recent_changes.count()
            avg_change_percent = recent_changes.aggregate(
                avg_percent=Avg('feature_count_change_percent')
            )['avg_percent'] or 0
            
            # Normalizar el porcentaje de cambio (asumir que 100% es el máximo impacto)
            normalized_change_percent = min(abs(avg_change_percent) / 100.0, 1.0)
            
            # Calcular frecuencia de cambios (cambios por hora)
            change_frequency = total_changes / self.hours
            
            # Normalizar la frecuencia (asumir que 10 cambios/hora es el máximo)
            normalized_frequency = min(change_frequency / 10.0, 1.0)
            
            # Combinar métricas (pesos arbitrarios)
            impact_score = (
                normalized_change_percent * 0.5 +
                normalized_frequency * 0.3 +
                (1 if report.severity == AlertSeverity.CRITICAL else 0.5 if report.severity == AlertSeverity.HIGH else 0.2) * 0.2
            ) * 100
            
            self.logger.info(f"Change impact score for {report.name}: {impact_score:.2f}")
            return round(impact_score, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating change impact score for {report.name}: {e}")
            return 0.0

    def calculate_report_complexity_score(self, report: Report) -> float:
        """
        Calcula una puntuación de complejidad basada en el número de features,
        tamaño de datos, tipos de capas, etc.

        Args:
            report (Report): Instancia del informe.

        Returns:
            float: Puntuación de complejidad (0.0 a 100.0).
        """
        self.logger.info(f"Calculating complexity score for report {report.name}")
        
        try:
            # Obtener el último snapshot de la capa del informe
            last_snapshot = LayerSnapshot.objects.filter(
                layer=report.layer,
                is_valid=True,
                is_removed=False
            ).order_by('-created').first()
            
            if not last_snapshot:
                self.logger.info(f"No snapshot found for layer {report.layer.name}")
                return 0.0
            
            # Métricas de complejidad
            feature_count = last_snapshot.feature_count or 0
            total_area = last_snapshot.total_area or 0
            data_size_bytes = last_snapshot.data_size_bytes or 0
            unique_values_count = sum(last_snapshot.unique_values.values()) if last_snapshot.unique_values else 0
            null_count_total = sum(last_snapshot.null_count.values()) if last_snapshot.null_count else 0
            
            # Normalizar métricas
            # Asumir máximos razonables para normalización
            max_features = 100000
            max_area = 1000000000 # 1 billón de unidades cuadradas
            max_data_size = 100 * 1024 * 1024 # 100 MB
            max_unique_values = 10000
            max_nulls = 10000
            
            normalized_feature_count = min(feature_count / max_features, 1.0)
            normalized_area = min(total_area / max_area, 1.0)
            normalized_data_size = min(data_size_bytes / max_data_size, 1.0)
            normalized_unique_values = min(unique_values_count / max_unique_values, 1.0)
            normalized_nulls = min(null_count_total / max_nulls, 1.0)
            
            # Combinar métricas (pesos arbitrarios)
            complexity_score = (
                normalized_feature_count * 0.3 +
                normalized_area * 0.2 +
                normalized_data_size * 0.2 +
                normalized_unique_values * 0.15 +
                normalized_nulls * 0.15
            ) * 100
            
            self.logger.info(f"Complexity score for {report.name}: {complexity_score:.2f}")
            return round(complexity_score, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating complexity score for {report.name}: {e}")
            return 0.0

    def calculate_user_productivity_score(self, user: User) -> float:
        """
        Calcula una puntuación de productividad del usuario basada en
        informes generados, tiempo promedio, etc.

        Args:
            user (User): Instancia del usuario.

        Returns:
            float: Puntuación de productividad (0.0 a 100.0).
        """
        self.logger.info(f"Calculating productivity score for user {user.email}")
        
        try:
            # Obtener informes generados por el usuario en el período
            user_reports = GeneratedReport.objects.filter(
                generated_by=user,
                created__gte=self.since,
                is_removed=False
            )
            
            if not user_reports.exists():
                self.logger.info(f"No reports generated by user {user.email} in the last {self.hours} hours")
                return 0.0
            
            # Métricas de productividad
            total_reports = user_reports.count()
            avg_generation_time = user_reports.aggregate(
                avg_time=Avg('generation_duration_ms')
            )['avg_time'] or 0
            
            # Normalizar métricas
            # Asumir máximos razonables para normalización
            max_reports = 50 # Informes en 24 horas
            max_avg_time = 60000 # 60 segundos en ms
            
            normalized_reports = min(total_reports / max_reports, 1.0)
            # Invertir el tiempo promedio: menor tiempo = mayor productividad
            normalized_time = 1.0 - min(avg_generation_time / max_avg_time, 1.0)
            
            # Combinar métricas (pesos arbitrarios)
            productivity_score = (
                normalized_reports * 0.6 +
                normalized_time * 0.4
            ) * 100
            
            self.logger.info(f"Productivity score for {user.email}: {productivity_score:.2f}")
            return round(productivity_score, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating productivity score for user {user.email}: {e}")
            return 0.0

    def calculate_service_health_score(self, service: ArcGISService) -> float:
        """
        Calcula una puntuación de salud del servicio basada en disponibilidad,
        tiempo de respuesta, errores, etc.

        Args:
            service (ArcGISService): Instancia del servicio GIS.

        Returns:
            float: Puntuación de salud (0.0 a 100.0).
        """
        self.logger.info(f"Calculating health score for service {service.name}")
        
        try:
            # Obtener métricas de salud del servicio en el período
            # Asumir que hay un modelo ServiceHealthMetric en gis_services
            # que almacena métricas de salud del servicio.
            # from apps.gis_services.models import ServiceHealthMetric
            # health_metrics = ServiceHealthMetric.objects.filter(
            #     service=service,
            #     created__gte=self.since
            # ).order_by('-created')
            
            # if not health_metrics.exists():
            #     self.logger.info(f"No health metrics found for service {service.name}")
            #     return 0.0
            
            # # Calcular métricas promedio
            # avg_cpu = health_metrics.aggregate(avg_cpu=Avg('cpu_usage_percent'))['avg_cpu'] or 0
            # avg_memory = health_metrics.aggregate(avg_memory=Avg('memory_usage_percent'))['avg_memory'] or 0
            # avg_disk = health_metrics.aggregate(avg_disk=Avg('disk_usage_percent'))['avg_disk'] or 0
            # avg_response_time = health_metrics.aggregate(avg_response=Avg('db_query_avg_time_ms'))['avg_response'] or 0
            # avg_api_errors = health_metrics.aggregate(avg_errors=Avg('api_error_rate_percent'))['avg_errors'] or 0
            
            # # Normalizar métricas
            # # Asumir máximos razonables para normalización
            # max_cpu = 80
            # max_memory = 80
            # max_disk = 90
            # max_response_time = 5000 # 5 segundos en ms
            # max_api_errors = 5 # 5% de errores
            
            # normalized_cpu = 1.0 - min(avg_cpu / max_cpu, 1.0)
            # normalized_memory = 1.0 - min(avg_memory / max_memory, 1.0)
            # normalized_disk = 1.0 - min(avg_disk / max_disk, 1.0)
            # normalized_response = 1.0 - min(avg_response_time / max_response_time, 1.0)
            # normalized_errors = 1.0 - min(avg_api_errors / max_api_errors, 1.0)
            
            # # Combinar métricas (pesos arbitrarios)
            # health_score = (
            #     normalized_cpu * 0.2 +
            #     normalized_memory * 0.2 +
            #     normalized_disk * 0.1 +
            #     normalized_response * 0.3 +
            #     normalized_errors * 0.2
            # ) * 100
            
            # Placeholder: Usar métricas de informes generados como proxy de salud
            reports_generated = GeneratedReport.objects.filter(
                report__service=service,
                created__gte=self.since,
                is_removed=False
            ).count()
            
            reports_failed = GeneratedReport.objects.filter(
                report__service=service,
                created__gte=self.since,
                status=ReportStatus.FAILED,
                is_removed=False
            ).count()
            
            success_rate = 1.0
            if reports_generated > 0:
                success_rate = (reports_generated - reports_failed) / reports_generated
            
            # Normalizar métricas
            max_reports = 100 # Informes en 24 horas
            normalized_reports = min(reports_generated / max_reports, 1.0)
            normalized_success = success_rate
            
            # Combinar métricas (pesos arbitrarios)
            health_score = (
                normalized_reports * 0.4 +
                normalized_success * 0.6
            ) * 100
            
            self.logger.info(f"Health score for {service.name}: {health_score:.2f}")
            return round(health_score, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating health score for service {service.name}: {e}")
            return 0.0

    def calculate_data_quality_index(self, layer: SpatialLayer) -> float:
        """
        Calcula un índice de calidad de datos basado en validez, unicidad,
        completitud, etc.

        Args:
            layer (SpatialLayer): Instancia de la capa espacial.

        Returns:
            float: Índice de calidad de datos (0.0 a 100.0).
        """
        self.logger.info(f"Calculating data quality index for layer {layer.name}")
        
        try:
            # Obtener el último snapshot de la capa
            last_snapshot = LayerSnapshot.objects.filter(
                layer=layer,
                is_valid=True,
                is_removed=False
            ).order_by('-created').first()
            
            if not last_snapshot:
                self.logger.info(f"No snapshot found for layer {layer.name}")
                return 0.0
            
            # Métricas de calidad
            feature_count = last_snapshot.feature_count or 0
            invalid_geometries = last_snapshot.invalid_geometries or 0
            duplicate_records = last_snapshot.duplicate_records or 0
            null_count_total = sum(last_snapshot.null_count.values()) if last_snapshot.null_count else 0
            unique_values_count = sum(last_snapshot.unique_values.values()) if last_snapshot.unique_values else 0
            
            # Calcular puntuaciones individuales (0.0 a 1.0)
            validity_score = 1.0 - (invalid_geometries / max(feature_count, 1))
            uniqueness_score = 1.0 - (duplicate_records / max(feature_count, 1))
            completeness_score = 1.0 - (null_count_total / max(feature_count * len(last_snapshot.null_count or {}), 1))
            # Simplificación: asumir que más valores únicos = mejor calidad
            diversity_score = min(unique_values_count / max(feature_count, 1), 1.0)
            
            # Combinar métricas (pesos arbitrarios)
            quality_index = (
                validity_score * 0.3 +
                uniqueness_score * 0.2 +
                completeness_score * 0.3 +
                diversity_score * 0.2
            ) * 100
            
            self.logger.info(f"Data quality index for {layer.name}: {quality_index:.2f}")
            return round(quality_index, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating data quality index for layer {layer.name}: {e}")
            return 0.0

    def calculate_performance_benchmark(self) -> Dict[str, Any]:
        """
        Calcula benchmarks de rendimiento (percentiles, desviación estándar)
        para tiempos de generación.

        Returns:
            Dict[str, Any]: Diccionario con benchmarks de rendimiento.
        """
        self.logger.info("Calculating performance benchmarks")
        
        try:
            # Obtener informes generados en el período
            reports = GeneratedReport.objects.filter(
                created__gte=self.since,
                status=ReportStatus.COMPLETED,
                is_removed=False
            )
            
            if not reports.exists():
                self.logger.info("No completed reports found for performance benchmark")
                return {}
            
            # Calcular métricas estadísticas
            stats = reports.aggregate(
                avg_time=Avg('generation_duration_ms'),
                min_time=Min('generation_duration_ms'),
                max_time=Max('generation_duration_ms'),
                std_dev=StdDev('generation_duration_ms'),
                variance=Variance('generation_duration_ms'),
                total_reports=Count('id')
            )
            
            # Calcular percentiles (requiere ordenar y obtener valores específicos)
            # Django no tiene una función de agregación nativa para percentiles,
            # por lo que se hace manualmente.
            durations = list(reports.values_list('generation_duration_ms', flat=True).order_by('generation_duration_ms'))
            total_count = len(durations)
            
            def percentile(data, percentile_rank):
                if not data:
                    return 0
                index = int((percentile_rank / 100.0) * (len(data) - 1))
                return data[index]
            
            p50 = percentile(durations, 50)
            p90 = percentile(durations, 90)
            p95 = percentile(durations, 95)
            p99 = percentile(durations, 99)
            
            benchmark = {
                'average_generation_time_ms': round(stats['avg_time'] or 0, 2),
                'min_generation_time_ms': stats['min_time'] or 0,
                'max_generation_time_ms': stats['max_time'] or 0,
                'std_deviation_ms': round(stats['std_dev'] or 0, 2),
                'variance_ms': round(stats['variance'] or 0, 2),
                'percentile_50_ms': p50,
                'percentile_90_ms': p90,
                'percentile_95_ms': p95,
                'percentile_99_ms': p99,
                'total_reports_analyzed': stats['total_reports'] or 0
            }
            
            self.logger.info(f"Performance benchmarks calculated: {benchmark}")
            return benchmark
            
        except Exception as e:
            self.logger.error(f"Error calculating performance benchmarks: {e}")
            return {}

    def calculate_trend_analysis(self) -> Dict[str, Any]:
        """
        Realiza análisis de tendencias (crecimiento, decrecimiento, estacionalidad)
        en la generación de informes.

        Returns:
            Dict[str, Any]: Diccionario con análisis de tendencias.
        """
        self.logger.info("Calculating trend analysis")
        
        try:
            # Obtener informes generados en el período, agrupados por día
            daily_counts = list(
                GeneratedReport.objects.filter(
                    created__gte=self.since,
                    is_removed=False
                )
                .extra(select={'day': "date(created)"})
                .values('day')
                .annotate(count=Count('id'))
                .order_by('day')
                .values('day', 'count')
            )
            
            if len(daily_counts) < 2:
                self.logger.info("Not enough data points for trend analysis")
                return {'trend': 'insufficient_data', 'slope': 0, 'r_squared': 0}
            
            # Calcular tendencia lineal simple (pendiente y R^2)
            # Usar mínimos cuadrados ordinarios
            n = len(daily_counts)
            x_vals = list(range(n)) # Días como 0, 1, 2, ...
            y_vals = [item['count'] for item in daily_counts]
            
            sum_x = sum(x_vals)
            sum_y = sum(y_vals)
            sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
            sum_xx = sum(x * x for x in x_vals)
            
            # Pendiente (m) y ordenada al origen (b)
            denominator = n * sum_xx - sum_x * sum_x
            if denominator == 0:
                slope = 0
            else:
                slope = (n * sum_xy - sum_x * sum_y) / denominator
            
            # R^2 (coeficiente de determinación)
            y_mean = sum_y / n if n > 0 else 0
            ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
            ss_res = sum((y - (slope * x + (sum_y - slope * sum_x) / n)) ** 2 for x, y in zip(x_vals, y_vals))
            
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Determinar tendencia
            if slope > 0.1:
                trend = 'increasing'
            elif slope < -0.1:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            analysis = {
                'trend': trend,
                'slope': round(slope, 4),
                'r_squared': round(r_squared, 4),
                'data_points': n,
                'daily_counts': daily_counts
            }
            
            self.logger.info(f"Trend analysis completed: {analysis}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error calculating trend analysis: {e}")
            return {'trend': 'error', 'slope': 0, 'r_squared': 0}

    def calculate_prediction_model(self) -> Dict[str, Any]:
        """
        (Avanzado) Crea un modelo predictivo simple para estimar tiempos
        de generación futuros.

        Returns:
            Dict[str, Any]: Diccionario con parámetros del modelo predictivo.
        """
        self.logger.info("Calculating prediction model")
        
        try:
            # Obtener informes generados en el período con datos relevantes
            reports = GeneratedReport.objects.filter(
                created__gte=self.since,
                status=ReportStatus.COMPLETED,
                is_removed=False
            ).select_related('report__layer', 'report__service')
            
            if not reports.exists():
                self.logger.info("No completed reports found for prediction model")
                return {}
            
            # Preparar datos para regresión lineal simple
            # Predicción basada en feature_count
            x_vals = [] # feature_count
            y_vals = [] # generation_duration_ms
            
            for report in reports:
                snapshot = report.report.layer.snapshots.filter(
                    is_valid=True,
                    is_removed=False
                ).order_by('-created').first()
                
                if snapshot and snapshot.feature_count is not None:
                    x_vals.append(snapshot.feature_count)
                    y_vals.append(report.generation_duration_ms)
            
            if len(x_vals) < 2:
                self.logger.info("Not enough data points for prediction model")
                return {'model': 'insufficient_data', 'slope': 0, 'intercept': 0, 'r_squared': 0}
            
            # Calcular regresión lineal
            n = len(x_vals)
            sum_x = sum(x_vals)
            sum_y = sum(y_vals)
            sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
            sum_xx = sum(x * x for x in x_vals)
            
            denominator = n * sum_xx - sum_x * sum_x
            if denominator == 0:
                slope = 0
                intercept = sum_y / n if n > 0 else 0
            else:
                slope = (n * sum_xy - sum_x * sum_y) / denominator
                intercept = (sum_y - slope * sum_x) / n
            
            # Calcular R^2
            y_mean = sum_y / n if n > 0 else 0
            ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
            ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_vals, y_vals))
            
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            model = {
                'model': 'linear_regression',
                'predictor_variable': 'feature_count',
                'target_variable': 'generation_duration_ms',
                'slope': round(slope, 4),
                'intercept': round(intercept, 4),
                'r_squared': round(r_squared, 4),
                'data_points': n
            }
            
            self.logger.info(f"Prediction model calculated: {model}")
            return model
            
        except Exception as e:
            self.logger.error(f"Error calculating prediction model: {e}")
            return {'model': 'error', 'slope': 0, 'intercept': 0, 'r_squared': 0}


# --- Funciones Independientes ---

def get_average_generation_time(hours: int = 24) -> float:
    """
    Obtiene el tiempo promedio de generación de informes.

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.

    Returns:
        float: Tiempo promedio de generación en milisegundos.
    """
    logger.info(f"Getting average generation time for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        avg_time = GeneratedReport.objects.filter(
            created__gte=since,
            status=ReportStatus.COMPLETED,
            is_removed=False
        ).aggregate(
            avg_time=Avg('generation_duration_ms')
        )['avg_time'] or 0
        
        logger.info(f"Average generation time: {avg_time:.2f} ms")
        return round(avg_time, 2)
        
    except Exception as e:
        logger.error(f"Error getting average generation time: {e}")
        return 0.0


def get_success_rate(hours: int = 24) -> float:
    """
    Obtiene la tasa de éxito de generación de informes.

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.

    Returns:
        float: Tasa de éxito como porcentaje (0.0 a 100.0).
    """
    logger.info(f"Getting success rate for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        total_reports = GeneratedReport.objects.filter(
            created__gte=since,
            is_removed=False
        ).count()
        
        successful_reports = GeneratedReport.objects.filter(
            created__gte=since,
            status=ReportStatus.COMPLETED,
            is_removed=False
        ).count()
        
        success_rate = 0
        if total_reports > 0:
            success_rate = (successful_reports / total_reports) * 100
        
        logger.info(f"Success rate: {success_rate:.2f}%")
        return round(success_rate, 2)
        
    except Exception as e:
        logger.error(f"Error getting success rate: {e}")
        return 0.0


def get_failure_rate(hours: int = 24) -> float:
    """
    Obtiene la tasa de fallo de generación de informes.

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.

    Returns:
        float: Tasa de fallo como porcentaje (0.0 a 100.0).
    """
    logger.info(f"Getting failure rate for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        total_reports = GeneratedReport.objects.filter(
            created__gte=since,
            is_removed=False
        ).count()
        
        failed_reports = GeneratedReport.objects.filter(
            created__gte=since,
            status=ReportStatus.FAILED,
            is_removed=False
        ).count()
        
        failure_rate = 0
        if total_reports > 0:
            failure_rate = (failed_reports / total_reports) * 100
        
        logger.info(f"Failure rate: {failure_rate:.2f}%")
        return round(failure_rate, 2)
        
    except Exception as e:
        logger.error(f"Error getting failure rate: {e}")
        return 0.0


def get_top_services_by_report_count(hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Obtiene los servicios con más informes generados.

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.
        limit (int): Número máximo de servicios a devolver. Por defecto 10.

    Returns:
        List[Dict[str, Any]]: Lista de servicios con conteo de informes.
    """
    logger.info(f"Getting top services by report count for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        top_services = list(
            ArcGISService.objects.filter(
                reports__generated_reports__created__gte=since,
                reports__generated_reports__is_removed=False
            )
            .annotate(report_count=Count('reports__generated_reports'))
            .order_by('-report_count')[:limit]
            .values('id', 'name', 'report_count')
        )
        
        logger.info(f"Top {len(top_services)} services by report count retrieved")
        return top_services
        
    except Exception as e:
        logger.error(f"Error getting top services by report count: {e}")
        return []


def get_top_layers_by_report_count(hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Obtiene las capas con más informes generados.

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.
        limit (int): Número máximo de capas a devolver. Por defecto 10.

    Returns:
        List[Dict[str, Any]]: Lista de capas con conteo de informes.
    """
    logger.info(f"Getting top layers by report count for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        top_layers = list(
            SpatialLayer.objects.filter(
                reports__generated_reports__created__gte=since,
                reports__generated_reports__is_removed=False
            )
            .annotate(report_count=Count('reports__generated_reports'))
            .order_by('-report_count')[:limit]
            .values('id', 'name', 'service__name', 'report_count')
        )
        
        logger.info(f"Top {len(top_layers)} layers by report count retrieved")
        return top_layers
        
    except Exception as e:
        logger.error(f"Error getting top layers by report count: {e}")
        return []


def get_report_volume_trend(hours: int = 24) -> List[Dict[str, Any]]:
    """
    Obtiene la tendencia del volumen de informes generados.

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.

    Returns:
        List[Dict[str, Any]]: Lista de datos de tendencia (día, conteo).
    """
    logger.info(f"Getting report volume trend for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        trend_data = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                is_removed=False
            )
            .extra(select={'day': "date(created)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
            .values('day', 'count')
        )
        
        logger.info(f"Report volume trend data retrieved for {len(trend_data)} days")
        return trend_data
        
    except Exception as e:
        logger.error(f"Error getting report volume trend: {e}")
        return []


def get_peak_generation_times(hours: int = 24) -> List[Dict[str, Any]]:
    """
    Obtiene los horarios pico de generación de informes.

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.

    Returns:
        List[Dict[str, Any]]: Lista de horarios con conteo de informes.
    """
    logger.info(f"Getting peak generation times for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Agrupar por hora del día
        peak_times = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                is_removed=False
            )
            .extra(select={'hour': "EXTRACT(hour FROM created)"})
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('-count')[:10] # Top 10 horas
            .values('hour', 'count')
        )
        
        logger.info(f"Peak generation times data retrieved for {len(peak_times)} hours")
        return peak_times
        
    except Exception as e:
        logger.error(f"Error getting peak generation times: {e}")
        return []
