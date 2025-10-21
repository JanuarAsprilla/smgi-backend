# apps/reports/analytics/dashboard_data.py
"""
SMGI Backend - Reports Analytics & Dashboard Data
Sistema de Monitoreo Geoespacial Inteligente
Funciones y clases para preparar datos analíticos y de dashboard para informes
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from django.db.models import Avg, Count, Sum, Min, Max, Q, F
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


logger = logging.getLogger('apps.reports.analytics')


def get_report_statistics(hours: int = 24) -> Dict[str, Any]:
    """
    Obtiene estadísticas generales de informes para un período de tiempo.

    Args:
        hours (int): Número de horas hacia atrás para calcular estadísticas. Por defecto 24.

    Returns:
        Dict[str, Any]: Diccionario con estadísticas de informes.
    """
    logger.info(f"Calculating report statistics for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Informes totales
        total_reports = Report.objects.filter(is_removed=False).count()
        
        # Informes activos
        active_reports = Report.objects.filter(
            is_active=True,
            is_removed=False
        ).count()
        
        # Informes generados en el período
        generated_reports = GeneratedReport.objects.filter(
            created__gte=since,
            is_removed=False
        ).count()
        
        # Informes generados hoy
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        generated_today = GeneratedReport.objects.filter(
            created__gte=today_start,
            is_removed=False
        ).count()
        
        # Informes fallidos en el período
        failed_reports = GeneratedReport.objects.filter(
            created__gte=since,
            status=ReportStatus.FAILED,
            is_removed=False
        ).count()
        
        # Informes completados en el período
        completed_reports = GeneratedReport.objects.filter(
            created__gte=since,
            status=ReportStatus.COMPLETED,
            is_removed=False
        ).count()
        
        # Tasa de éxito
        success_rate = 0
        if generated_reports > 0:
            success_rate = (completed_reports / generated_reports) * 100
        
        # Tiempo promedio de generación (ms)
        avg_generation_time = GeneratedReport.objects.filter(
            created__gte=since,
            status=ReportStatus.COMPLETED,
            is_removed=False
        ).aggregate(
            avg_time=Avg('generation_duration_ms')
        )['avg_time'] or 0
        
        # Informes por tipo
        reports_by_type = dict(
            Report.objects.filter(is_removed=False)
            .values('report_type')
            .annotate(count=Count('id'))
            .values_list('report_type', 'count')
        )
        
        # Informes por formato
        reports_by_format = dict(
            GeneratedReport.objects.filter(is_removed=False)
            .values('format_type')
            .annotate(count=Count('id'))
            .values_list('format_type', 'count')
        )
        
        # Top 5 servicios con más informes
        top_services = list(
            ArcGISService.objects.filter(
                reports__is_removed=False,
                reports__created__gte=since
            )
            .annotate(report_count=Count('reports'))
            .order_by('-report_count')[:5]
            .values('name', 'report_count')
        )
        
        stats = {
            'total_reports': total_reports,
            'active_reports': active_reports,
            'generated_reports': generated_reports,
            'generated_today': generated_today,
            'failed_reports': failed_reports,
            'completed_reports': completed_reports,
            'success_rate_percent': round(success_rate, 2),
            'average_generation_time_ms': round(avg_generation_time, 2),
            'reports_by_type': reports_by_type,
            'reports_by_format': reports_by_format,
            'top_services_with_reports': top_services
        }
        
        logger.info(f"Report statistics calculated: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating report statistics: {e}")
        return {}


def get_report_trends(days: int = 30) -> Dict[str, Any]:
    """
    Obtiene datos de tendencia de generación de informes.

    Args:
        days (int): Número de días hacia atrás para calcular tendencias. Por defecto 30.

    Returns:
        Dict[str, Any]: Diccionario con datos de tendencia.
    """
    logger.info(f"Calculating report trends for last {days} days")
    
    try:
        since = timezone.now() - timedelta(days=days)
        
        # Agrupar por día
        daily_trend = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                is_removed=False
            )
            .extra(select={'day': "date(created)"}) # Extraer solo la fecha
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
            .values('day', 'count')
        )
        
        # Agrupar por semana
        weekly_trend = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                is_removed=False
            )
            .extra(select={'week': "date_trunc('week', created)"}) # Extraer inicio de semana
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
            .values('week', 'count')
        )
        
        # Agrupar por mes
        monthly_trend = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                is_removed=False
            )
            .extra(select={'month': "date_trunc('month', created)"}) # Extraer inicio de mes
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
        
        logger.info(f"Report trends calculated for {days} days")
        return trends
        
    except Exception as e:
        logger.error(f"Error calculating report trends: {e}")
        return {}


def get_top_reports(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Obtiene los informes más generados.

    Args:
        limit (int): Número máximo de informes a devolver. Por defecto 10.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con información de los top informes.
    """
    logger.info(f"Getting top {limit} reports")
    
    try:
        top_reports = list(
            Report.objects.filter(is_removed=False)
            .annotate(generated_count=Count('generated_reports'))
            .order_by('-generated_count')[:limit]
            .values(
                'id', 'name', 'report_type', 'service__name', 'layer__name',
                'generated_count'
            )
        )
        
        logger.info(f"Retrieved top {len(top_reports)} reports")
        return top_reports
        
    except Exception as e:
        logger.error(f"Error getting top reports: {e}")
        return []


def get_report_performance(hours: int = 24) -> Dict[str, Any]:
    """
    Obtiene métricas de rendimiento de generación de informes.

    Args:
        hours (int): Número de horas hacia atrás para calcular rendimiento. Por defecto 24.

    Returns:
        Dict[str, Any]: Diccionario con métricas de rendimiento.
    """
    logger.info(f"Calculating report performance metrics for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Métricas de tiempo
        time_metrics = GeneratedReport.objects.filter(
            created__gte=since,
            status=ReportStatus.COMPLETED,
            is_removed=False
        ).aggregate(
            avg_duration=Avg('generation_duration_ms'),
            min_duration=Min('generation_duration_ms'),
            max_duration=Max('generation_duration_ms'),
            total_duration=Sum('generation_duration_ms')
        )
        
        # Métricas de tamaño
        size_metrics = GeneratedReport.objects.filter(
            created__gte=since,
            is_removed=False
        ).aggregate(
            avg_size=Avg('file_size_bytes'),
            min_size=Min('file_size_bytes'),
            max_size=Max('file_size_bytes'),
            total_size=Sum('file_size_bytes')
        )
        
        # Métricas de conteo
        count_metrics = GeneratedReport.objects.filter(
            created__gte=since,
            is_removed=False
        ).aggregate(
            total_reports=Count('id'),
            completed_reports=Count('id', filter=Q(status=ReportStatus.COMPLETED)),
            failed_reports=Count('id', filter=Q(status=ReportStatus.FAILED))
        )
        
        # Tasa de éxito
        success_rate = 0
        if count_metrics['total_reports'] > 0:
            success_rate = (count_metrics['completed_reports'] / count_metrics['total_reports']) * 100
        
        # Métricas por formato
        format_metrics = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                is_removed=False
            )
            .values('format_type')
            .annotate(
                avg_duration=Avg('generation_duration_ms'),
                avg_size=Avg('file_size_bytes'),
                total_reports=Count('id'),
                completed_reports=Count('id', filter=Q(status=ReportStatus.COMPLETED)),
                failed_reports=Count('id', filter=Q(status=ReportStatus.FAILED))
            )
            .order_by('-total_reports')
        )
        
        performance = {
            'time_metrics': {
                'average_duration_ms': round(time_metrics['avg_duration'] or 0, 2),
                'min_duration_ms': time_metrics['min_duration'] or 0,
                'max_duration_ms': time_metrics['max_duration'] or 0,
                'total_duration_ms': time_metrics['total_duration'] or 0
            },
            'size_metrics': {
                'average_size_bytes': round(size_metrics['avg_size'] or 0, 2),
                'min_size_bytes': size_metrics['min_size'] or 0,
                'max_size_bytes': size_metrics['max_size'] or 0,
                'total_size_bytes': size_metrics['total_size'] or 0
            },
            'count_metrics': {
                'total_reports': count_metrics['total_reports'] or 0,
                'completed_reports': count_metrics['completed_reports'] or 0,
                'failed_reports': count_metrics['failed_reports'] or 0,
                'success_rate_percent': round(success_rate, 2)
            },
            'format_metrics': format_metrics
        }
        
        logger.info(f"Report performance metrics calculated")
        return performance
        
    except Exception as e:
        logger.error(f"Error calculating report performance metrics: {e}")
        return {}


def get_user_report_activity(hours: int = 24) -> List[Dict[str, Any]]:
    """
    Obtiene actividad de generación de informes por usuario.

    Args:
        hours (int): Número de horas hacia atrás para calcular actividad. Por defecto 24.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con actividad por usuario.
    """
    logger.info(f"Calculating user report activity for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        user_activity = list(
            User.objects.filter(
                generated_reports__created__gte=since,
                generated_reports__is_removed=False
            )
            .annotate(
                reports_generated=Count('generated_reports'),
                avg_generation_time=Avg('generated_reports__generation_duration_ms')
            )
            .order_by('-reports_generated')
            .values(
                'id', 'username', 'email', 'first_name', 'last_name',
                'reports_generated', 'avg_generation_time'
            )
        )
        
        logger.info(f"Calculated user report activity for {len(user_activity)} users")
        return user_activity
        
    except Exception as e:
        logger.error(f"Error calculating user report activity: {e}")
        return []


def get_service_report_distribution() -> List[Dict[str, Any]]:
    """
    Obtiene la distribución de informes por servicio/layer.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con distribución por servicio/layer.
    """
    logger.info("Calculating service/layer report distribution")
    
    try:
        # Distribución por servicio
        service_distribution = list(
            ArcGISService.objects.filter(
                reports__is_removed=False
            )
            .annotate(report_count=Count('reports'))
            .order_by('-report_count')
            .values('id', 'name', 'report_count')
        )
        
        # Distribución por layer
        layer_distribution = list(
            SpatialLayer.objects.filter(
                reports__is_removed=False
            )
            .annotate(report_count=Count('reports'))
            .order_by('-report_count')
            .values('id', 'name', 'service__name', 'report_count')
        )
        
        distribution = {
            'by_service': service_distribution,
            'by_layer': layer_distribution
        }
        
        logger.info(f"Calculated service/layer report distribution")
        return distribution
        
    except Exception as e:
        logger.error(f"Error calculating service/layer report distribution: {e}")
        return {}


def get_schedule_efficiency(hours: int = 24) -> Dict[str, Any]:
    """
    Obtiene métricas de eficiencia de las programaciones de informes.

    Args:
        hours (int): Número de horas hacia atrás para calcular eficiencia. Por defecto 24.

    Returns:
        Dict[str, Any]: Diccionario con métricas de eficiencia de programaciones.
    """
    logger.info(f"Calculating report schedule efficiency for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Métricas de ejecuciones
        execution_metrics = ReportExecution.objects.filter(
            started_at__gte=since,
            is_removed=False
        ).aggregate(
            total_executions=Count('id'),
            successful_executions=Count('id', filter=Q(success=True)),
            failed_executions=Count('id', filter=Q(success=False)),
            avg_duration=Avg('duration_seconds'),
            min_duration=Min('duration_seconds'),
            max_duration=Max('duration_seconds')
        )
        
        # Tasa de éxito
        success_rate = 0
        if execution_metrics['total_executions'] > 0:
            success_rate = (execution_metrics['successful_executions'] / execution_metrics['total_executions']) * 100
        
        # Programaciones activas
        active_schedules = ReportSchedule.objects.filter(
            is_active=True,
            is_removed=False
        ).count()
        
        # Programaciones con fallos consecutivos
        failing_schedules = ReportSchedule.objects.filter(
            is_active=True,
            is_removed=False,
            consecutive_failures__gte=3 # Umbral arbitrario
        ).count()
        
        # Ejecuciones retrasadas
        delayed_executions = ReportExecution.objects.filter(
            started_at__gte=since,
            is_removed=False,
            started_at__gt=F('schedule__next_run') + timedelta(minutes=5) # Retraso de 5 minutos
        ).count()
        
        efficiency = {
            'execution_metrics': {
                'total_executions': execution_metrics['total_executions'] or 0,
                'successful_executions': execution_metrics['successful_executions'] or 0,
                'failed_executions': execution_metrics['failed_executions'] or 0,
                'success_rate_percent': round(success_rate, 2),
                'average_duration_seconds': round(execution_metrics['avg_duration'] or 0, 2),
                'min_duration_seconds': execution_metrics['min_duration'] or 0,
                'max_duration_seconds': execution_metrics['max_duration'] or 0
            },
            'schedule_metrics': {
                'active_schedules': active_schedules,
                'failing_schedules': failing_schedules,
                'delayed_executions': delayed_executions
            }
        }
        
        logger.info(f"Report schedule efficiency metrics calculated")
        return efficiency
        
    except Exception as e:
        logger.error(f"Error calculating report schedule efficiency metrics: {e}")
        return {}


def get_system_health_metrics(hours: int = 24) -> Dict[str, Any]:
    """
    Obtiene métricas de salud del sistema de reportes.

    Args:
        hours (int): Número de horas hacia atrás para calcular salud. Por defecto 24.

    Returns:
        Dict[str, Any]: Diccionario con métricas de salud del sistema.
    """
    logger.info(f"Calculating system health metrics for reports for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Métricas de recursos (simuladas, requerirían integración real con psutil, etc.)
        # En una implementación real, estas vendrían de SystemHealthMetric o de una tarea de monitoreo del sistema.
        cpu_usage_percent = 0 # Placeholder
        memory_usage_percent = 0 # Placeholder
        disk_usage_percent = 0 # Placeholder
        
        # Métricas de errores en generación
        generation_errors = GeneratedReport.objects.filter(
            created__gte=since,
            status=ReportStatus.FAILED,
            is_removed=False
        ).count()
        
        # Métricas de errores en ejecuciones
        execution_errors = ReportExecution.objects.filter(
            started_at__gte=since,
            success=False,
            is_removed=False
        ).count()
        
        # Métricas de alertas críticas relacionadas con informes (simuladas)
        # En una implementación real, se filtrarían Alert por categoría y severidad.
        critical_alerts = 0 # Placeholder
        
        # Métricas de usuarios activos (simuladas)
        # En una implementación real, se calcularía desde logs de actividad o sesiones.
        active_users = 0 # Placeholder
        
        health = {
            'resource_metrics': {
                'cpu_usage_percent': cpu_usage_percent,
                'memory_usage_percent': memory_usage_percent,
                'disk_usage_percent': disk_usage_percent
            },
            'error_metrics': {
                'generation_errors': generation_errors,
                'execution_errors': execution_errors,
                'critical_alerts': critical_alerts
            },
            'user_metrics': {
                'active_users': active_users
            }
        }
        
        logger.info(f"System health metrics for reports calculated")
        return health
        
    except Exception as e:
        logger.error(f"Error calculating system health metrics for reports: {e}")
        return {}

# --- Clases de Procesadores de Datos (Opcional) ---

class ReportAnalyticsProcessor:
    """
    Clase para procesar y analizar datos de informes.
    """
    
    def __init__(self, hours: int = 24):
        self.hours = hours
        self.since = timezone.now() - timedelta(hours=hours)
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
    
    def get_all_analytics(self) -> Dict[str, Any]:
        """
        Obtiene todas las métricas analíticas disponibles.
        
        Returns:
            Dict[str, Any]: Diccionario con todas las métricas.
        """
        self.logger.info("Getting all analytics data")
        
        analytics_data = {
            'statistics': get_report_statistics(self.hours),
            'trends': get_report_trends(days=self.hours // 24 if self.hours >= 24 else 1),
            'top_reports': get_top_reports(limit=10),
            'performance': get_report_performance(self.hours),
            'user_activity': get_user_report_activity(self.hours),
            'distribution': get_service_report_distribution(),
            'schedule_efficiency': get_schedule_efficiency(self.hours),
            'system_health': get_system_health_metrics(self.hours)
        }
        
        self.logger.info("All analytics data retrieved")
        return analytics_data


class DashboardDataAggregator:
    """
    Clase para agregar datos de múltiples fuentes para dashboards.
    """
    
    def __init__(self, hours: int = 24):
        self.hours = hours
        self.since = timezone.now() - timedelta(hours=hours)
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
    
    def aggregate_dashboard_data(self) -> Dict[str, Any]:
        """
        Agrega todos los datos necesarios para un dashboard de reportes.
        
        Returns:
            Dict[str, Any]: Diccionario con datos agregados para el dashboard.
        """
        self.logger.info("Aggregating dashboard data")
        
        # Obtener datos de analytics
        analytics_processor = ReportAnalyticsProcessor(hours=self.hours)
        analytics_data = analytics_processor.get_all_analytics()
        
        # Preparar datos para el dashboard
        dashboard_data = {
            'period_hours': self.hours,
            'generated_at': timezone.now().isoformat(),
            'statistics': analytics_data.get('statistics', {}),
            'trends': analytics_data.get('trends', {}),
            'top_reports': analytics_data.get('top_reports', []),
            'performance': analytics_data.get('performance', {}),
            'user_activity': analytics_data.get('user_activity', []),
            'distribution': analytics_data.get('distribution', {}),
            'schedule_efficiency': analytics_data.get('schedule_efficiency', {}),
            'system_health': analytics_data.get('system_health', {})
        }
        
        self.logger.info("Dashboard data aggregated")
        return dashboard_data
