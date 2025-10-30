# apps/reports/analytics/trend_analyzer.py
"""
SMGI Backend - Reports Trend Analyzer
Sistema de Monitoreo Geoespacial Inteligente
Analizador de tendencias avanzadas para el sistema de informes
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import timedelta
from collections import defaultdict
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Min, Max, StdDev, Variance, Q, F
from django.utils.translation import gettext_lazy as _
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima.model import ARIMA

from apps.reports.models import (
    Report, GeneratedReport, ReportSchedule, ReportExecution,
    ReportType, ReportFormat, ReportStatus
)
# Importar modelos relacionados
from apps.authentication.models import User
from apps.gis_services.models import ArcGISService, SpatialLayer
from apps.monitoring.models import MonitoringJob
from apps.alerts.models import Alert


logger = logging.getLogger('apps.reports.analytics.trend')


class ReportTrendAnalyzer:
    """
    Analizador de tendencias avanzadas para el sistema de informes
    """

    def __init__(self, hours: int = 24):
        """
        Inicializa el analizador de tendencias

        Args:
            hours (int): Número de horas hacia atrás para analizar tendencias. Por defecto 24.
        """
        self.hours = hours
        self.since = timezone.now() - timedelta(hours=hours)
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    def analyze_report_volume_trend(self) -> Dict[str, Any]:
        """
        Analiza la tendencia del volumen de informes generados

        Returns:
            Dict[str, Any]: Diccionario con análisis de tendencia del volumen
        """
        self.logger.info(f"Analyzing report volume trend for last {self.hours} hours")
        
        try:
            # Obtener informes generados agrupados por día
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
                self.logger.info("Not enough data points for volume trend analysis")
                return {'trend': 'insufficient_data', 'slope': 0, 'r_squared': 0, 'data_points': len(daily_counts)}
            
            # Convertir a DataFrame de pandas para análisis
            df = pd.DataFrame(daily_counts)
            df['day'] = pd.to_datetime(df['day'])
            df.set_index('day', inplace=True)
            
            # Calcular tendencia lineal simple (pendiente y R^2)
            # Usar mínimos cuadrados ordinarios
            x_vals = np.arange(len(df)) # Días como 0, 1, 2, ...
            y_vals = df['count'].values
            
            # Pendiente (m) y ordenada al origen (b)
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
            r_squared = r_value ** 2
            
            # Determinar tendencia
            if slope > 0.1:
                trend = 'increasing'
            elif slope < -0.1:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Calcular crecimiento porcentual
            growth_rate_percent = 0
            if len(y_vals) >= 2 and y_vals[0] > 0:
                growth_rate_percent = ((y_vals[-1] - y_vals[0]) / y_vals[0]) * 100
            
            analysis = {
                'trend': trend,
                'slope': round(slope, 4),
                'r_squared': round(r_squared, 4),
                'growth_rate_percent': round(growth_rate_percent, 2),
                'data_points': len(daily_counts),
                'daily_counts': daily_counts
            }
            
            self.logger.info(f"Report volume trend analysis completed: {analysis}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing report volume trend: {e}")
            return {'trend': 'error', 'slope': 0, 'r_squared': 0, 'error': str(e)}

    def analyze_report_success_rate_trend(self) -> Dict[str, Any]:
        """
        Analiza la tendencia de la tasa de éxito de generación de informes

        Returns:
            Dict[str, Any]: Diccionario con análisis de tendencia de tasa de éxito
        """
        self.logger.info(f"Analyzing report success rate trend for last {self.hours} hours")
        
        try:
            # Obtener informes generados agrupados por día con conteo de éxitos y fallos
            daily_stats = list(
                GeneratedReport.objects.filter(
                    created__gte=self.since,
                    is_removed=False
                )
                .extra(select={'day': "date(created)"})
                .values('day')
                .annotate(
                    total=Count('id'),
                    successful=Count('id', filter=Q(status=ReportStatus.COMPLETED)),
                    failed=Count('id', filter=Q(status=ReportStatus.FAILED))
                )
                .order_by('day')
                .values('day', 'total', 'successful', 'failed')
            )
            
            if len(daily_stats) < 2:
                self.logger.info("Not enough data points for success rate trend analysis")
                return {'trend': 'insufficient_data', 'slope': 0, 'r_squared': 0, 'data_points': len(daily_stats)}
            
            # Calcular tasa de éxito diaria
            success_rates = []
            for day_stats in daily_stats:
                if day_stats['total'] > 0:
                    rate = (day_stats['successful'] / day_stats['total']) * 100
                else:
                    rate = 100.0 # Si no hay informes, asumir 100% éxito
                success_rates.append(rate)
            
            # Convertir a DataFrame de pandas para análisis
            df = pd.DataFrame(daily_stats)
            df['day'] = pd.to_datetime(df['day'])
            df['success_rate'] = success_rates
            df.set_index('day', inplace=True)
            
            # Calcular tendencia lineal simple (pendiente y R^2)
            x_vals = np.arange(len(df)) # Días como 0, 1, 2, ...
            y_vals = df['success_rate'].values
            
            # Pendiente (m) y ordenada al origen (b)
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
            r_squared = r_value ** 2
            
            # Determinar tendencia
            if slope > 0.1:
                trend = 'improving'
            elif slope < -0.1:
                trend = 'deteriorating'
            else:
                trend = 'stable'
            
            # Calcular cambio porcentual
            change_rate_percent = 0
            if len(y_vals) >= 2 and y_vals[0] > 0:
                change_rate_percent = ((y_vals[-1] - y_vals[0]) / y_vals[0]) * 100
            
            analysis = {
                'trend': trend,
                'slope': round(slope, 4),
                'r_squared': round(r_squared, 4),
                'change_rate_percent': round(change_rate_percent, 2),
                'data_points': len(daily_stats),
                'daily_success_rates': [{'day': ds['day'].strftime('%Y-%m-%d'), 'rate': sr} for ds, sr in zip(daily_stats, success_rates)]
            }
            
            self.logger.info(f"Report success rate trend analysis completed: {analysis}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing report success rate trend: {e}")
            return {'trend': 'error', 'slope': 0, 'r_squared': 0, 'error': str(e)}

    def analyze_report_generation_time_trend(self) -> Dict[str, Any]:
        """
        Analiza la tendencia del tiempo de generación de informes

        Returns:
            Dict[str, Any]: Diccionario con análisis de tendencia del tiempo de generación
        """
        self.logger.info(f"Analyzing report generation time trend for last {self.hours} hours")
        
        try:
            # Obtener informes completados agrupados por día con estadísticas de tiempo
            daily_times = list(
                GeneratedReport.objects.filter(
                    created__gte=self.since,
                    status=ReportStatus.COMPLETED,
                    is_removed=False
                )
                .extra(select={'day': "date(created)"})
                .values('day')
                .annotate(
                    avg_time=Avg('generation_duration_ms'),
                    min_time=Min('generation_duration_ms'),
                    max_time=Max('generation_duration_ms'),
                    count=Count('id')
                )
                .order_by('day')
                .values('day', 'avg_time', 'min_time', 'max_time', 'count')
            )
            
            if len(daily_times) < 2:
                self.logger.info("Not enough data points for generation time trend analysis")
                return {'trend': 'insufficient_data', 'slope': 0, 'r_squared': 0, 'data_points': len(daily_times)}
            
            # Convertir a DataFrame de pandas para análisis
            df = pd.DataFrame(daily_times)
            df['day'] = pd.to_datetime(df['day'])
            df.set_index('day', inplace=True)
            
            # Calcular tendencia lineal simple para el tiempo promedio (pendiente y R^2)
            x_vals = np.arange(len(df)) # Días como 0, 1, 2, ...
            y_vals = df['avg_time'].fillna(0).values # Reemplazar NaN con 0
            
            # Pendiente (m) y ordenada al origen (b)
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
            r_squared = r_value ** 2
            
            # Determinar tendencia
            if slope > 100: # 100 ms de cambio por día es significativo
                trend = 'increasing'
            elif slope < -100:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Calcular cambio porcentual
            change_rate_percent = 0
            if len(y_vals) >= 2 and y_vals[0] > 0:
                change_rate_percent = ((y_vals[-1] - y_vals[0]) / y_vals[0]) * 100
            
            analysis = {
                'trend': trend,
                'slope': round(slope, 2),
                'r_squared': round(r_squared, 4),
                'change_rate_percent': round(change_rate_percent, 2),
                'data_points': len(daily_times),
                'daily_generation_times': daily_times
            }
            
            self.logger.info(f"Report generation time trend analysis completed: {analysis}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing report generation time trend: {e}")
            return {'trend': 'error', 'slope': 0, 'r_squared': 0, 'error': str(e)}

    def analyze_user_report_activity_trend(self) -> Dict[str, Any]:
        """
        Analiza la tendencia de actividad de generación de informes por usuario

        Returns:
            Dict[str, Any]: Diccionario con análisis de tendencia de actividad por usuario
        """
        self.logger.info(f"Analyzing user report activity trend for last {self.hours} hours")
        
        try:
            # Obtener actividad de usuarios agrupada por día
            user_activity = list(
                User.objects.filter(
                    generated_reports__created__gte=self.since,
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
            
            # Obtener tendencia por usuario (más activo en los últimos días)
            user_trends = []
            for user in user_activity:
                # Obtener conteo diario de informes generados por este usuario
                daily_counts = list(
                    GeneratedReport.objects.filter(
                        generated_by_id=user['id'],
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
                    trend = 'insufficient_data'
                    slope = 0
                    r_squared = 0
                else:
                    # Calcular tendencia lineal simple
                    x_vals = np.arange(len(daily_counts)) # Días como 0, 1, 2, ...
                    y_vals = [item['count'] for item in daily_counts]
                    
                    # Pendiente (m) y ordenada al origen (b)
                    slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
                    r_squared = r_value ** 2
                    
                    if slope > 0.1:
                        trend = 'increasing'
                    elif slope < -0.1:
                        trend = 'decreasing'
                    else:
                        trend = 'stable'
                
                user_trends.append({
                    'user_id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'full_name': f"{user['first_name']} {user['last_name']}".strip(),
                    'reports_generated': user['reports_generated'],
                    'avg_generation_time_ms': round(user['avg_generation_time'] or 0, 2),
                    'trend': trend,
                    'slope': round(slope, 4),
                    'r_squared': round(r_squared, 4),
                    'daily_counts': daily_counts
                })
            
            # Ordenar por actividad (más informes generados)
            user_trends.sort(key=lambda x: x['reports_generated'], reverse=True)
            
            analysis = {
                'user_count': len(user_trends),
                'top_users': user_trends[:10], # Top 10 usuarios
                'all_users': user_trends
            }
            
            self.logger.info(f"User report activity trend analysis completed for {len(user_trends)} users")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing user report activity trend: {e}")
            return {'trend': 'error', 'error': str(e)}

    def analyze_service_report_trend(self) -> Dict[str, Any]:
        """
        Analiza la tendencia de generación de informes por servicio/layer

        Returns:
            Dict[str, Any]: Diccionario con análisis de tendencia por servicio/layer
        """
        self.logger.info(f"Analyzing service/layer report trend for last {self.hours} hours")
        
        try:
            # Obtener tendencia por servicio
            service_trends = list(
                ArcGISService.objects.filter(
                    reports__generated_reports__created__gte=self.since,
                    reports__generated_reports__is_removed=False
                )
                .annotate(
                    report_count=Count('reports__generated_reports'),
                    avg_generation_time=Avg('reports__generated_reports__generation_duration_ms')
                )
                .order_by('-report_count')
                .values(
                    'id', 'name', 'report_count', 'avg_generation_time'
                )
            )
            
            # Obtener tendencia por layer
            layer_trends = list(
                SpatialLayer.objects.filter(
                    reports__generated_reports__created__gte=self.since,
                    reports__generated_reports__is_removed=False
                )
                .annotate(
                    report_count=Count('reports__generated_reports'),
                    avg_generation_time=Avg('reports__generated_reports__generation_duration_ms')
                )
                .order_by('-report_count')
                .values(
                    'id', 'name', 'service__name', 'report_count', 'avg_generation_time'
                )
            )
            
            # Calcular crecimiento porcentual para servicios
            for service in service_trends:
                # Obtener conteo diario de informes por servicio
                daily_counts = list(
                    GeneratedReport.objects.filter(
                        report__service_id=service['id'],
                        created__gte=self.since,
                        is_removed=False
                    )
                    .extra(select={'day': "date(created)"})
                    .values('day')
                    .annotate(count=Count('id'))
                    .order_by('day')
                    .values('day', 'count')
                )
                
                if len(daily_counts) >= 2:
                    first_count = daily_counts[0]['count']
                    last_count = daily_counts[-1]['count']
                    if first_count > 0:
                        service['growth_rate_percent'] = round(((last_count - first_count) / first_count) * 100, 2)
                    else:
                        service['growth_rate_percent'] = 100.0 if last_count > 0 else 0.0
                else:
                    service['growth_rate_percent'] = 0.0
                
                service['daily_counts'] = daily_counts
            
            # Calcular crecimiento porcentual para layers
            for layer in layer_trends:
                # Obtener conteo diario de informes por layer
                daily_counts = list(
                    GeneratedReport.objects.filter(
                        report__layer_id=layer['id'],
                        created__gte=self.since,
                        is_removed=False
                    )
                    .extra(select={'day': "date(created)"})
                    .values('day')
                    .annotate(count=Count('id'))
                    .order_by('day')
                    .values('day', 'count')
                )
                
                if len(daily_counts) >= 2:
                    first_count = daily_counts[0]['count']
                    last_count = daily_counts[-1]['count']
                    if first_count > 0:
                        layer['growth_rate_percent'] = round(((last_count - first_count) / first_count) * 100, 2)
                    else:
                        layer['growth_rate_percent'] = 100.0 if last_count > 0 else 0.0
                else:
                    layer['growth_rate_percent'] = 0.0
                
                layer['daily_counts'] = daily_counts
            
            analysis = {
                'service_count': len(service_trends),
                'layer_count': len(layer_trends),
                'top_services': service_trends[:10], # Top 10 servicios
                'top_layers': layer_trends[:10], # Top 10 capas
                'all_services': service_trends,
                'all_layers': layer_trends
            }
            
            self.logger.info(f"Service/layer report trend analysis completed")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing service/layer report trend: {e}")
            return {'trend': 'error', 'error': str(e)}

    def detect_anomalies_in_report_volume(self, threshold_std_dev: float = 2.0) -> Dict[str, Any]:
        """
        Detecta anomalías (picos, caídas) en el volumen de informes generados

        Args:
            threshold_std_dev (float): Umbral de desviación estándar para detectar anomalías. Por defecto 2.0.

        Returns:
            Dict[str, Any]: Diccionario con análisis de anomalías en el volumen
        """
        self.logger.info(f"Detecting anomalies in report volume for last {self.hours} hours")
        
        try:
            # Obtener informes generados agrupados por día
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
            
            if len(daily_counts) < 3: # Necesitamos al menos 3 puntos para calcular std dev
                self.logger.info("Not enough data points for anomaly detection")
                return {'anomalies': [], 'data_points': len(daily_counts)}
            
            # Calcular media y desviación estándar
            counts = [item['count'] for item in daily_counts]
            mean_count = np.mean(counts)
            std_dev = np.std(counts)
            
            # Detectar anomalías
            anomalies = []
            for item in daily_counts:
                z_score = abs(item['count'] - mean_count) / std_dev if std_dev > 0 else 0
                if z_score > threshold_std_dev:
                    anomaly_type = 'spike' if item['count'] > mean_count else 'drop'
                    anomalies.append({
                        'day': item['day'].strftime('%Y-%m-%d'),
                        'count': item['count'],
                        'mean': round(mean_count, 2),
                        'std_dev': round(std_dev, 2),
                        'z_score': round(z_score, 2),
                        'type': anomaly_type
                    })
            
            analysis = {
                'anomalies': anomalies,
                'data_points': len(daily_counts),
                'mean_count': round(mean_count, 2),
                'std_dev_count': round(std_dev, 2),
                'threshold_std_dev': threshold_std_dev
            }
            
            self.logger.info(f"Anomaly detection completed. Found {len(anomalies)} anomalies")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies in report volume: {e}")
            return {'anomalies': [], 'error': str(e)}

    def detect_anomalies_in_report_generation_time(self, threshold_std_dev: float = 2.0) -> Dict[str, Any]:
        """
        Detecta anomalías en los tiempos de generación de informes

        Args:
            threshold_std_dev (float): Umbral de desviación estándar para detectar anomalías. Por defecto 2.0.

        Returns:
            Dict[str, Any]: Diccionario con análisis de anomalías en tiempos de generación
        """
        self.logger.info(f"Detecting anomalies in report generation time for last {self.hours} hours")
        
        try:
            # Obtener informes completados con tiempos de generación
            completed_reports = GeneratedReport.objects.filter(
                created__gte=self.since,
                status=ReportStatus.COMPLETED,
                is_removed=False
            ).values('generation_duration_ms')
            
            if completed_reports.count() < 3:
                self.logger.info("Not enough completed reports for generation time anomaly detection")
                return {'anomalies': [], 'data_points': completed_reports.count()}
            
            # Calcular media y desviación estándar
            durations = [item['generation_duration_ms'] for item in completed_reports if item['generation_duration_ms'] is not None]
            if len(durations) < 3:
                self.logger.info("Not enough valid durations for generation time anomaly detection")
                return {'anomalies': [], 'data_points': len(durations)}
            
            mean_duration = np.mean(durations)
            std_dev = np.std(durations)
            
            # Detectar anomalías
            anomalies = []
            for item in completed_reports:
                duration = item['generation_duration_ms']
                if duration is None:
                    continue
                z_score = abs(duration - mean_duration) / std_dev if std_dev > 0 else 0
                if z_score > threshold_std_dev:
                    anomaly_type = 'slow' if duration > mean_duration else 'fast'
                    anomalies.append({
                        'report_id': str(item['id']) if 'id' in item else 'N/A',
                        'duration_ms': duration,
                        'mean_ms': round(mean_duration, 2),
                        'std_dev_ms': round(std_dev, 2),
                        'z_score': round(z_score, 2),
                        'type': anomaly_type
                    })
            
            analysis = {
                'anomalies': anomalies,
                'data_points': len(durations),
                'mean_duration_ms': round(mean_duration, 2),
                'std_dev_duration_ms': round(std_dev, 2),
                'threshold_std_dev': threshold_std_dev
            }
            
            self.logger.info(f"Generation time anomaly detection completed. Found {len(anomalies)} anomalies")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies in report generation time: {e}")
            return {'anomalies': [], 'error': str(e)}

    def forecast_report_volume(self, days_ahead: int = 7) -> Dict[str, Any]:
        """
        (Avanzado) Predice el volumen de informes para un período futuro
        Usa un modelo ARIMA simple para la predicción

        Args:
            days_ahead (int): Número de días hacia adelante para predecir. Por defecto 7.

        Returns:
            Dict[str, Any]: Diccionario con predicción de volumen
        """
        self.logger.info(f"Forecasting report volume for next {days_ahead} days")
        
        try:
            # Obtener informes generados agrupados por día
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
            
            if len(daily_counts) < 10: # Necesitamos suficientes datos para ARIMA
                self.logger.info("Not enough data points for volume forecasting")
                return {'forecast': [], 'data_points': len(daily_counts)}
            
            # Convertir a Series de pandas
            df = pd.DataFrame(daily_counts)
            df['day'] = pd.to_datetime(df['day'])
            df.set_index('day', inplace=True)
            
            # Crear una serie temporal diaria completa (rellenar días sin datos con 0)
            full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
            ts = df.reindex(full_range, fill_value=0)['count']
            
            # Ajustar modelo ARIMA (p, d, q)
            # p: número de términos autorregresivos
            # d: número de diferencias no estacionales
            # q: número de términos de media móvil
            # Valores típicos para datos diarios: (1, 1, 1) o (2, 1, 2)
            model = ARIMA(ts, order=(1, 1, 1))
            fitted_model = model.fit()
            
            # Generar predicción
            forecast = fitted_model.forecast(steps=days_ahead)
            
            # Preparar resultados
            last_day = ts.index[-1]
            forecast_dates = [last_day + timedelta(days=i+1) for i in range(days_ahead)]
            forecast_data = [
                {'day': date.strftime('%Y-%m-%d'), 'predicted_count': int(round(count))}
                for date, count in zip(forecast_dates, forecast)
            ]
            
            analysis = {
                'forecast': forecast_data,
                'data_points': len(ts),
                'days_ahead': days_ahead,
                'model_order': '(1, 1, 1)',
                'aic': fitted_model.aic, # Criterio de información Akaike
                'bic': fitted_model.bic  # Criterio de información Bayesiano
            }
            
            self.logger.info(f"Report volume forecast completed for next {days_ahead} days")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error forecasting report volume: {e}")
            return {'forecast': [], 'error': str(e)}

    def forecast_report_generation_time(self, report_id: str, minutes_ahead: int = 60) -> Dict[str, Any]:
        """
        (Avanzado) Predice el tiempo de generación para un informe específico
        Usa una regresión lineal simple basada en el historial de generación

        Args:
            report_id (str): ID del informe
            minutes_ahead (int): Número de minutos hacia adelante para predecir. Por defecto 60.

        Returns:
            Dict[str, Any]: Diccionario con predicción de tiempo de generación
        """
        self.logger.info(f"Forecasting generation time for report {report_id} for next {minutes_ahead} minutes")
        
        try:
            # Obtener informes generados para este informe específico
            report_reports = GeneratedReport.objects.filter(
                report_id=report_id,
                status=ReportStatus.COMPLETED,
                is_removed=False
            ).order_by('created').values('generation_duration_ms', 'created')
            
            if report_reports.count() < 5: # Necesitamos suficientes datos para regresión
                self.logger.info(f"Not enough data points for generation time forecasting for report {report_id}")
                return {'forecast': [], 'data_points': report_reports.count()}
            
            # Calcular tendencia lineal simple (pendiente y ordenada al origen)
            # Usar minutos transcurridos desde el primer informe como variable independiente
            first_report_time = report_reports.first()['created']
            data_points = []
            for rr in report_reports:
                elapsed_minutes = (rr['created'] - first_report_time).total_seconds() / 60
                duration_ms = rr['generation_duration_ms']
                if duration_ms is not None:
                    data_points.append((elapsed_minutes, duration_ms))
            
            if len(data_points) < 5:
                self.logger.info(f"Not enough valid data points for generation time forecasting for report {report_id}")
                return {'forecast': [], 'data_points': len(data_points)}
            
            x_vals = np.array([point[0] for point in data_points]) # Minutos transcurridos
            y_vals = np.array([point[1] for point in data_points]) # Duración en ms
            
            # Pendiente (m) y ordenada al origen (b)
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
            r_squared = r_value ** 2
            
            # Generar predicción para los próximos minutos
            forecast = []
            last_elapsed_minutes = data_points[-1][0]
            for i in range(1, minutes_ahead + 1):
                predicted_duration_ms = max(0, round(slope * (last_elapsed_minutes + i) + intercept)) # No negativos
                forecast.append({
                    'minute': int(last_elapsed_minutes + i),
                    'predicted_duration_ms': predicted_duration_ms
                })
            
            analysis = {
                'forecast': forecast,
                'data_points': len(data_points),
                'slope': round(slope, 4),
                'intercept': round(intercept, 2),
                'r_squared': round(r_squared, 4),
                'minutes_ahead': minutes_ahead
            }
            
            self.logger.info(f"Generation time forecast completed for report {report_id} for next {minutes_ahead} minutes")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error forecasting generation time for report {report_id}: {e}")
            return {'forecast': [], 'error': str(e)}


# --- Funciones Independientes ---

def get_report_volume_growth_rate(hours: int = 24) -> float:
    """
    Calcula la tasa de crecimiento del volumen de informes

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.

    Returns:
        float: Tasa de crecimiento como porcentaje (positivo o negativo)
    """
    logger.info(f"Calculating report volume growth rate for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Obtener conteo de informes en el primer y último día del período
        daily_counts = list(
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
        
        if len(daily_counts) < 2:
            logger.info("Not enough data points for volume growth rate calculation")
            return 0.0
        
        first_count = daily_counts[0]['count']
        last_count = daily_counts[-1]['count']
        
        growth_rate = 0.0
        if first_count > 0:
            growth_rate = ((last_count - first_count) / first_count) * 100
        
        logger.info(f"Report volume growth rate: {growth_rate:.2f}%")
        return round(growth_rate, 2)
        
    except Exception as e:
        logger.error(f"Error calculating report volume growth rate: {e}")
        return 0.0


def get_report_success_rate_growth_rate(hours: int = 24) -> float:
    """
    Calcula la tasa de crecimiento de la tasa de éxito de informes

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.

    Returns:
        float: Tasa de crecimiento de la tasa de éxito como porcentaje
    """
    logger.info(f"Calculating report success rate growth rate for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Obtener tasas de éxito en el primer y último día del período
        daily_stats = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                is_removed=False
            )
            .extra(select={'day': "date(created)"})
            .values('day')
            .annotate(
                total=Count('id'),
                successful=Count('id', filter=Q(status=ReportStatus.COMPLETED))
            )
            .order_by('day')
            .values('day', 'total', 'successful')
        )
        
        if len(daily_stats) < 2:
            logger.info("Not enough data points for success rate growth rate calculation")
            return 0.0
        
        first_stats = daily_stats[0]
        last_stats = daily_stats[-1]
        
        first_rate = (first_stats['successful'] / first_stats['total']) * 100 if first_stats['total'] > 0 else 100.0
        last_rate = (last_stats['successful'] / last_stats['total']) * 100 if last_stats['total'] > 0 else 100.0
        
        growth_rate = 0.0
        if first_rate > 0:
            growth_rate = ((last_rate - first_rate) / first_rate) * 100
        
        logger.info(f"Report success rate growth rate: {growth_rate:.2f}%")
        return round(growth_rate, 2)
        
    except Exception as e:
        logger.error(f"Error calculating report success rate growth rate: {e}")
        return 0.0


def get_report_generation_time_trend_slope(hours: int = 24) -> float:
    """
    Calcula la pendiente de la tendencia del tiempo de generación de informes

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 24.

    Returns:
        float: Pendiente de la tendencia (ms por día)
    """
    logger.info(f"Calculating report generation time trend slope for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Obtener tiempos de generación promedio por día
        daily_times = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                status=ReportStatus.COMPLETED,
                is_removed=False
            )
            .extra(select={'day': "date(created)"})
            .values('day')
            .annotate(avg_time=Avg('generation_duration_ms'))
            .order_by('day')
            .values('day', 'avg_time')
        )
        
        if len(daily_times) < 2:
            logger.info("Not enough data points for generation time trend slope calculation")
            return 0.0
        
        # Calcular pendiente lineal simple
        x_vals = np.arange(len(daily_times)) # Días como 0, 1, 2, ...
        y_vals = [item['avg_time'] for item in daily_times if item['avg_time'] is not None]
        
        if len(y_vals) < 2:
            logger.info("Not enough valid data points for generation time trend slope calculation")
            return 0.0
        
        # Pendiente (m) y ordenada al origen (b)
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
        
        logger.info(f"Report generation time trend slope: {slope:.2f} ms/day")
        return round(slope, 2)
        
    except Exception as e:
        logger.error(f"Error calculating report generation time trend slope: {e}")
        return 0.0


def identify_seasonal_patterns(hours: int = 24 * 7) -> Dict[str, Any]: # Última semana por defecto
    """
    Identifica patrones estacionales en la generación de informes

    Args:
        hours (int): Número de horas hacia atrás. Por defecto 168 (7 días)

    Returns:
        Dict[str, Any]: Diccionario con patrones estacionales identificados
    """
    logger.info(f"Identifying seasonal patterns in report generation for last {hours} hours")
    
    try:
        since = timezone.now() - timedelta(hours=hours)
        
        # Agrupar por día de la semana y hora del día
        weekday_patterns = list(
            GeneratedReport.objects.filter(
                created__gte=since,
                is_removed=False
            )
            .extra(select={
                'weekday': "EXTRACT(dow FROM created)", # 0=Domingo, 6=Sábado
                'hour': "EXTRACT(hour FROM created)"
            })
            .values('weekday', 'hour')
            .annotate(count=Count('id'))
            .order_by('weekday', 'hour')
            .values('weekday', 'hour', 'count')
        )
        
        # Convertir a diccionario para fácil acceso
        patterns_dict = defaultdict(lambda: defaultdict(int))
        for item in weekday_patterns:
            patterns_dict[item['weekday']][item['hour']] = item['count']
        
        # Identificar picos y valles
        peak_weekday = None
        peak_hour = None
        peak_count = 0
        valley_weekday = None
        valley_hour = None
        valley_count = float('inf')
        
        for weekday, hours_dict in patterns_dict.items():
            for hour, count in hours_dict.items():
                if count > peak_count:
                    peak_count = count
                    peak_weekday = weekday
                    peak_hour = hour
                if count < valley_count:
                    valley_count = count
                    valley_weekday = weekday
                    valley_hour = hour
        
        analysis = {
            'patterns': dict(patterns_dict), # Convertir defaultdict a dict
            'peak_time': {
                'weekday': peak_weekday,
                'hour': peak_hour,
                'count': peak_count
            } if peak_weekday is not None else None,
            'valley_time': {
                'weekday': valley_weekday,
                'hour': valley_hour,
                'count': valley_count
            } if valley_weekday is not None else None
        }
        
        logger.info(f"Seasonal patterns identified: Peak at weekday {peak_weekday}, hour {peak_hour}")
        return analysis
        
    except Exception as e:
        logger.error(f"Error identifying seasonal patterns: {e}")
        return {'patterns': {}, 'error': str(e)}


def detect_outliers( List[float], threshold_std_dev: float = 2.0) -> List[Tuple[int, float]]:
    """
    Detecta valores atípicos en una serie de datos

    Args:
        data (List[float]): Serie de datos numéricos
        threshold_std_dev (float): Umbral de desviación estándar para detectar outliers. Por defecto 2.0

    Returns:
        List[Tuple[int, float]]: Lista de tuplas (índice, valor) de los outliers detectados
    """
    logger.info(f"Detecting outliers in data series with threshold {threshold_std_dev} std devs")
    
    try:
        if len(data) < 3:
            logger.info("Not enough data points for outlier detection")
            return []
        
        # Calcular media y desviación estándar
        mean = np.mean(data)
        std_dev = np.std(data)
        
        if std_dev == 0:
            logger.info("Standard deviation is zero, no outliers detected")
            return []
        
        # Detectar outliers
        outliers = []
        for i, value in enumerate(data):
            z_score = abs(value - mean) / std_dev if std_dev > 0 else 0
            if z_score > threshold_std_dev:
                outliers.append((i, value))
        
        logger.info(f"Outlier detection completed. Found {len(outliers)} outliers")
        return outliers
        
    except Exception as e:
        logger.error(f"Error detecting outliers: {e}")
        return []


def calculate_correlation(x_ List[float], y_ List[float]) -> float:
    """
    Calcula la correlación de Pearson entre dos series de datos

    Args:
        x_data (List[float]): Primera serie de datos
        y_data (List[float]): Segunda serie de datos

    Returns:
        float: Coeficiente de correlación de Pearson (-1.0 a 1.0)
    """
    logger.info("Calculating Pearson correlation coefficient")
    
    try:
        if len(x_data) != len(y_data) or len(x_data) < 2:
            logger.info("Data series must have same length and at least 2 points")
            return 0.0
        
        # Calcular correlación de Pearson
        correlation = np.corrcoef(x_data, y_data)[0, 1]
        
        logger.info(f"Pearson correlation coefficient calculated: {correlation:.4f}")
        return round(correlation, 4)
        
    except Exception as e:
        logger.error(f"Error calculating Pearson correlation: {e}")
        return 0.0
