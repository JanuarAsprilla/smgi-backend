"""
SMGI Backend - Monitoring Tasks
Sistema de Monitoreo Geoespacial Inteligente
Tareas asíncronas para monitoreo de servicios y capas geoespaciales
"""
import logging
import time
import hashlib
import json
import psutil
from datetime import timedelta
from celery import shared_task, current_task, group, chord
from celery.exceptions import Retry
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q

from apps.gis_services.models import ArcGISService, SpatialLayer, ServiceStatus
from apps.monitoring.models import (
    LayerSnapshot, ChangeDetectionResult, MonitoringJob,
    MonitoringJobExecution, SystemHealthMetric, DataQualityRule,
    DataQualityResult, ChangeDetectionAlgorithm, AffectedFeature
)
from apps.alerts.models import Alert, AlertSeverity, AlertCategory
from apps.gis_services.clients.arcgis_client import ArcGISClient
# Importar los algoritmos de detección de cambios
from .algorithms.change_detection import (
    SimpleCountChangeDetector,
    HashComparisonChangeDetector,
    FieldComparisonChangeDetector,
    GeometricAnalysisChangeDetector,
    StatisticalAnalysisChangeDetector,
    # MLAnomalyDetectionChangeDetector # Pendiente de implementación
)


logger = logging.getLogger('apps.monitoring')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def monitor_all_active_layers(self):
    """
    Main task to monitor all active layers.
    Uses a group of tasks for each layer to improve parallelism.
    """
    start_time = time.time()
    stats = {
        'layers_processed': 0,
        'snapshots_created': 0,
        'changes_detected': 0,
        'errors': 0,
        'warnings': [],
        'total_layers_found': 0
    }
    
    try:
        logger.info("Starting monitoring of all active layers")
        
        # Get all layers that should be monitored
        layers = SpatialLayer.objects.filter(
            is_monitored=True,
            monitoring_enabled=True,
            service__is_monitored=True,
            service__status=ServiceStatus.ACTIVE,
            is_removed=False
        ).select_related('service')
        
        total_layers = layers.count()
        stats['total_layers_found'] = total_layers
        logger.info(f"Found {total_layers} layers to monitor")
        
        if total_layers == 0:
            logger.info("No layers to monitor, finishing task.")
            duration = time.time() - start_time
            return {
                'success': True,
                'duration_seconds': duration,
                **stats
            }
        
        # Create a group of tasks for monitoring each layer
        layer_monitor_tasks = [monitor_layer.s(layer.id) for layer in layers]
        job_group = group(*layer_monitor_tasks)
        
        # Execute the group
        result_group = job_group.apply_async()
        
        # Wait for all tasks in the group to complete and collect results
        results = result_group.get(propagate=True) # Propagate=True para que se lance la excepción si alguna tarea falla
        
        # Process results
        for layer_result in results:
            stats['layers_processed'] += 1
            if layer_result.get('snapshot_created'):
                stats['snapshots_created'] += 1
            if layer_result.get('changes_detected'):
                stats['changes_detected'] += 1
        
        duration = time.time() - start_time
        logger.info(f"Completed monitoring task in {duration:.2f} seconds. Stats: {stats}")
        
        # Update system metrics
        update_monitoring_metrics.delay(stats)
        
        return {
            'success': True,
            'duration_seconds': duration,
            **stats
        }
        
    except Exception as e:
        logger.error(f"Critical error in monitor_all_active_layers: {e}")
        stats['errors'] += 1
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def monitor_layer(self, layer_id):
    """
    Monitor a specific spatial layer for changes
    """
    start_time = time.time()
    logger.info(f"Starting monitoring of layer ID: {layer_id}")
    
    try:
        # Get layer with related service
        layer = SpatialLayer.objects.select_related('service').get(
            id=layer_id,
            is_removed=False
        )
        
        # Check if layer should be monitored
        if not layer.should_be_monitored:
            logger.warning(f"Layer {layer.name} should not be monitored, skipping")
            return {'success': True, 'skipped': True, 'reason': 'not_configured_for_monitoring'}
        
        # Initialize ArcGIS client
        client = ArcGISClient(layer.service)
        
        # Collect layer data (timing collection)
        collection_start_time = time.time()
        logger.info(f"Collecting data for layer: {layer.name}")
        layer_data = client.get_layer_info(layer.layer_id)
        collection_duration_ms = int((time.time() - collection_start_time) * 1000)
        
        if not layer_data:
            logger.error(f"Failed to collect data for layer {layer.name}")
            layer.record_check_failure("Failed to collect layer data")
            return {'success': False, 'error': 'data_collection_failed'}
        
        # Create snapshot
        snapshot = create_layer_snapshot(layer, layer_data, collection_duration_ms)
        
        if not snapshot:
            logger.error(f"Failed to create snapshot for layer {layer.name}")
            return {'success': False, 'error': 'snapshot_creation_failed'}
        
        # Perform change detection
        changes_detected = False
        previous_snapshot = snapshot.get_previous_snapshot()
        
        if previous_snapshot:
            logger.info(f"Performing change detection for layer: {layer.name}")
            detection_result = perform_change_detection(snapshot, previous_snapshot, layer)
            
            if detection_result and detection_result.has_changes:
                changes_detected = True
                logger.info(f"Changes detected in layer {layer.name}: {detection_result.get_change_summary()}")
                
                # Create alert if threshold exceeded
                if detection_result.exceeds_threshold:
                    create_change_alert.delay(detection_result.id)
        
        # Update layer statistics
        layer.update_feature_count(layer_data.get('count', 0))
        
        duration = time.time() - start_time
        logger.info(f"Successfully monitored layer {layer.name} in {duration:.2f} seconds")
        
        return {
            'success': True,
            'layer_id': layer_id,
            'layer_name': layer.name,
            'snapshot_created': True,
            'changes_detected': changes_detected,
            'feature_count': layer_data.get('count', 0),
            'duration_seconds': duration
        }
        
    except SpatialLayer.DoesNotExist:
        logger.error(f"Layer with ID {layer_id} not found")
        return {'success': False, 'error': 'layer_not_found'}
    
    except Exception as e:
        logger.error(f"Error monitoring layer {layer_id}: {e}")
        
        # Record failure in layer if we can access it
        try:
            layer = SpatialLayer.objects.get(id=layer_id)
            layer.record_check_failure(str(e))
        except SpatialLayer.DoesNotExist:
            pass # Layer no existe, no se puede actualizar su fallo
        except Exception as inner_e:
            logger.error(f"Could not record check failure for layer {layer_id}: {inner_e}")
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@shared_task
def create_layer_snapshot(layer, layer_data, collection_duration_ms):
    """
    Create a snapshot of layer data for change detection.
    NOTE: The geometric statistics (total_area, centroid) are calculated
    based on the layer's extent, not the individual features' geometries.
    For precise feature-based statistics, a more expensive process is needed.
    """
    try:
        logger.info(f"Creating snapshot for layer: {layer.name}")
        
        # Calculate basic statistics
        feature_count = layer_data.get('count', 0)
        extent = layer_data.get('extent', {})
        
        # Create data hash for change detection
        data_for_hash = {
            'count': feature_count,
            'extent': extent,
            'fields': layer_data.get('fields', []),
            'timestamp': timezone.now().isoformat()
        }
        
        snapshot_hash = hashlib.sha256(
            json.dumps(data_for_hash, sort_keys=True).encode()
        ).hexdigest()
        
        # Calculate geometric statistics based on extent (approximation)
        total_area = None
        centroid = None
        
        if extent and all(k in extent for k in ['xmin', 'ymin', 'xmax', 'ymax']):
            # Calculate approximate area based on extent (not individual features)
            width = extent['xmax'] - extent['xmin']
            height = extent['ymax'] - extent['ymin']
            # This is a very rough approximation and depends on the SRID
            # For precise area, the sum of individual feature areas would be needed
            total_area = width * height
            
            # Calculate centroid of the extent
            from django.contrib.gis.geos import Point
            centroid = Point(
                (extent['xmin'] + extent['xmax']) / 2,
                (extent['ymin'] + extent['ymax']) / 2,
                srid=4326
            )
        
        # Collect attribute statistics (placeholder for future implementation)
        attribute_stats = {}
        unique_values = {}
        null_count = {}
        
        # This would be enhanced with actual field analysis in a full implementation
        # for field in layer_data.get('fields', []):
        #     field_name = field.get('name')
        #     if field_name:
        #         # Calculate actual nulls, min, max, avg, unique values per field
        #         pass
        
        # Create snapshot record
        with transaction.atomic():
            snapshot = LayerSnapshot.objects.create(
                layer=layer,
                snapshot_hash=snapshot_hash,
                feature_count=feature_count,
                total_area=total_area,
                extent_bounds={
                    'xmin': extent.get('xmin'),
                    'ymin': extent.get('ymin'),
                    'xmax': extent.get('xmax'),
                    'ymax': extent.get('ymax')
                } if extent else {},
                centroid=centroid,
                attribute_stats=attribute_stats,
                unique_values=unique_values,
                null_count=null_count,
                data_checksum=snapshot_hash,
                collection_duration_ms=collection_duration_ms, # Corregido
                data_size_bytes=len(json.dumps(layer_data)),
                is_valid=True
            )
        
        logger.info(f"Created snapshot {snapshot.id} for layer {layer.name}")
        return snapshot
        
    except Exception as e:
        logger.error(f"Error creating snapshot for layer {layer.name}: {e}")
        return None


@shared_task
def perform_change_detection(current_snapshot, previous_snapshot, layer):
    """
    Perform change detection between two snapshots using the configured algorithm.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Performing change detection for layer: {layer.name} using algorithm {layer.detection_algorithm}")
        
        # Determine algorithm to use from the layer's configuration
        algorithm_name = layer.detection_algorithm # Asumiendo que detection_algorithm es un campo en SpatialLayer o se pasa
        
        # Seleccionar el detector basado en el nombre
        # Opcional: Crear una fábrica de detectores
        detector_map = {
            ChangeDetectionAlgorithm.SIMPLE_COUNT: SimpleCountChangeDetector,
            ChangeDetectionAlgorithm.HASH_COMPARISON: HashComparisonChangeDetector,
            ChangeDetectionAlgorithm.FIELD_COMPARISON: FieldComparisonChangeDetector,
            ChangeDetectionAlgorithm.GEOMETRIC_ANALYSIS: GeometricAnalysisChangeDetector,
            ChangeDetectionAlgorithm.STATISTICAL_ANALYSIS: StatisticalAnalysisChangeDetector,
            # ChangeDetectionAlgorithm.ML_ANOMALY_DETECTION: MLAnomalyDetectionChangeDetector,
        }
        
        DetectorClass = detector_map.get(algorithm_name, SimpleCountChangeDetector)
        detector = DetectorClass()
        
        # Ejecutar la detección de cambios
        detection_result_data = detector.detect(current_snapshot, previous_snapshot, layer)
        
        # Crear el objeto ChangeDetectionResult con los datos obtenidos
        with transaction.atomic():
            result = ChangeDetectionResult.objects.create(
                current_snapshot=current_snapshot,
                previous_snapshot=previous_snapshot,
                algorithm_used=algorithm_name,
                detection_duration_ms=int((time.time() - start_time) * 1000),
                confidence_score=detection_result_data.get('confidence_score', 0.9),
                has_changes=detection_result_data.get('has_changes', False),
                change_types=detection_result_data.get('change_types', []),
                feature_count_change=detection_result_data.get('feature_count_change', 0),
                feature_count_change_percent=detection_result_data.get('feature_count_change_percent', 0.0),
                area_change=detection_result_data.get('area_change', 0.0),
                area_change_percent=detection_result_data.get('area_change_percent', 0.0),
                centroid_displacement=detection_result_data.get('centroid_displacement', 0.0),
                new_features=detection_result_data.get('new_features', 0),
                deleted_features=detection_result_data.get('deleted_features', 0),
                modified_features=detection_result_data.get('modified_features', 0),
                data_quality_score=detection_result_data.get('data_quality_score', 1.0),
                data_quality_change=detection_result_data.get('data_quality_change', 0.0),
                change_details=detection_result_data.get('change_details', {}),
                exceeds_threshold=detection_result_data.get('exceeds_threshold', False),
                threshold_values=detection_result_data.get('threshold_values', {}),
                processing_status='completed'
            )
        
        # Si el detector devolvió IDs de features afectadas, crear los objetos AffectedFeature
        affected_feature_ids = detection_result_data.get('affected_feature_ids', [])
        for fid in affected_feature_ids:
            AffectedFeature.objects.create(change_result=result, feature_id=fid)
        
        logger.info(f"Change detection completed for layer {layer.name}. Changes: {result.has_changes}")
        return result
        
    except Exception as e:
        logger.error(f"Error in change detection for layer {layer.name}: {e}")
        
        # Create failed result record
        try:
            result = ChangeDetectionResult.objects.create(
                current_snapshot=current_snapshot,
                previous_snapshot=previous_snapshot,
                processing_status='failed',
                error_message=str(e),
                has_changes=False,
                confidence_score=0.0
            )
            return result
        except Exception as inner_e:
            logger.error(f"Could not create failed ChangeDetectionResult: {inner_e}")
            return None


@shared_task
def create_change_alert(detection_result_id):
    """
    Create alert based on change detection result
    """
    try:
        result = ChangeDetectionResult.objects.get(id=detection_result_id)
        layer = result.layer
        
        # Determine alert severity based on change magnitude and result severity
        # Prioritize the severity calculated by the detection algorithm
        result_severity = result.change_severity
        severity_map = {
            'critical': AlertSeverity.CRITICAL,
            'high': AlertSeverity.HIGH,
            'medium': AlertSeverity.MEDIUM,
            'low': AlertSeverity.LOW,
            'none': AlertSeverity.LOW, # Default low if no changes
        }
        severity = severity_map.get(result_severity, AlertSeverity.MEDIUM)
        
        # Create alert
        alert = Alert.objects.create(
            title=f"Change detected in layer: {layer.name}",
            description=result.get_change_summary(),
            alert_id=f"change_detection_{layer.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            category=AlertCategory.CHANGE_DETECTION,
            severity=severity,
            service=layer.service,
            layer=layer,
            affected_features_count=result.total_features_affected,
            change_percentage=result.feature_count_change_percent,
            threshold_value=layer.change_threshold,
            actual_value=abs(result.feature_count_change_percent),
            metadata={
                'detection_result_id': str(result.id),
                'algorithm_used': result.algorithm_used,
                'confidence_score': result.confidence_score,
                'change_types': result.change_types,
                'detection_timestamp': result.created.isoformat()
            },
            auto_resolve=True,
            auto_resolve_duration=24
        )
        
        logger.info(f"Created change detection alert: {alert.alert_id}")
        
        # Send notifications
        send_alert_notifications.delay(alert.id)
        
        return alert.id
        
    except ChangeDetectionResult.DoesNotExist:
        logger.error(f"ChangeDetectionResult with ID {detection_result_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error creating change alert for result {detection_result_id}: {e}")
        return None


@shared_task
def send_alert_notifications(alert_id):
    """
    Send notifications for an alert
    """
    try:
        from apps.notifications.tasks import process_alert_notification
        
        alert = Alert.objects.get(id=alert_id)
        
        # Check if notifications should be suppressed
        if alert.should_suppress_notifications():
            logger.info(f"Suppressing notifications for similar alert: {alert.alert_id}")
            return {'suppressed': True}
        
        # Process notification
        result = process_alert_notification.delay(alert_id)
        
        # Mark notification as sent
        alert.increment_notification_count()
        
        logger.info(f"Initiated notification process for alert: {alert.alert_id}")
        return {'notification_initiated': True}
        
    except Alert.DoesNotExist:
        logger.error(f"Alert with ID {alert_id} not found")
        return {'error': 'alert_not_found'}
    except Exception as e:
        logger.error(f"Error sending notifications for alert {alert_id}: {e}")
        return {'error': str(e)}


@shared_task
def cleanup_old_snapshots(days_to_keep=30):
    """
    Clean up old snapshots to manage storage
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        old_snapshots = LayerSnapshot.objects.filter(
            created__lt=cutoff_date
        ).exclude(
            # Keep snapshots that are referenced by active alerts
            layer__alerts__status__in=['active', 'acknowledged']
        )
        
        count = old_snapshots.count()
        deleted_count = 0
        
        # Delete in batches to avoid memory issues
        batch_size = 100
        while old_snapshots.exists():
            batch_ids = list(old_snapshots.values_list('id', flat=True)[:batch_size])
            batch_deleted = LayerSnapshot.objects.filter(id__in=batch_ids).delete()[0]
            deleted_count += batch_deleted
            
            if batch_deleted < batch_size:
                break
        
        logger.info(f"Cleaned up {deleted_count} old snapshots (older than {days_to_keep} days)")
        
        return {
            'success': True,
            'snapshots_deleted': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old snapshots: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def system_health_check():
    """
    Perform comprehensive system health check
    """
    try:
        logger.info("Performing system health check")
        
        # Get system metrics using psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database metrics (placeholder - real implementation depends on DB driver)
        # from django.db import connection
        # db_queries = len(connection.queries) # No es útil aquí, es por request
        # db_conn_count = ... # Requiere query específica al motor de BD
        db_connections_active = 0 # Placeholder
        db_connections_idle = 0 # Placeholder
        db_query_avg_time_ms = 0 # Placeholder
        
        # Redis metrics (placeholder - requires direct Redis connection)
        redis_memory_usage_mb = 0 # Placeholder
        redis_connected_clients = 0 # Placeholder
        redis_operations_per_sec = 0 # Placeholder
        try:
            from django.core.cache import cache
            # Test connectivity and get basic info if possible
            cache.get('health_check_key') # Simple connectivity test
            # Example of getting Redis info if using redis-py directly:
            # redis_client = cache.client.get_client() # If using django-redis
            # redis_info = redis_client.info()
            # redis_memory_usage_mb = redis_info.get('used_memory', 0) / (1024 * 1024)
            # redis_connected_clients = redis_info.get('connected_clients', 0)
            redis_connected = True
        except:
            redis_connected = False
        
        # Celery metrics (placeholder - requires Celery Inspect)
        from celery import current_app
        inspect = current_app.control.inspect()
        
        try:
            active_tasks = inspect.active()
            reserved_tasks = inspect.reserved()
            celery_active_tasks = sum(len(tasks) for tasks in (active_tasks or {}).values())
            celery_reserved_tasks = sum(len(tasks) for tasks in (reserved_tasks or {}).values())
            # pending = inspect.scheduled() # No es exactamente pending, es scheduled
            # failed = ... # No disponible directamente con inspect, se usa backend como RabbitMQ/Redis o Flower
            celery_pending_tasks = 0 # Placeholder
            celery_failed_tasks = 0 # Placeholder
        except Exception as inspect_e:
            logger.error(f"Error inspecting Celery: {inspect_e}")
            celery_active_tasks = 0
            celery_pending_tasks = 0
            celery_failed_tasks = 0
        
        # Application metrics (from cache or other sources)
        active_users = cache.get('active_users_count', 0)
        api_requests = cache.get('api_requests_last_minute', 0)
        api_errors = cache.get('api_errors_last_minute', 0)
        api_error_rate = (api_errors / max(api_requests, 1)) * 100 if api_requests > 0 else 0.0
        
        # Determine overall health
        health_score = 100
        
        if cpu_percent > 80:
            health_score -= 20
        elif cpu_percent > 60:
            health_score -= 10
        
        if memory.percent > 85:
            health_score -= 20
        elif memory.percent > 70:
            health_score -= 10
        
        if disk.percent > 90:
            health_score -= 25
        elif disk.percent > 80:
            health_score -= 15
        
        if not redis_connected:
            health_score -= 30
        
        if api_error_rate > 10:
            health_score -= 15
        elif api_error_rate > 5:
            health_score -= 10
        
        # Determine health status
        if health_score >= 90:
            overall_health = 'excellent'
        elif health_score >= 75:
            overall_health = 'good'
        elif health_score >= 60:
            overall_health = 'warning'
        elif health_score >= 40:
            overall_health = 'critical'
        else:
            overall_health = 'error'
        
        # Create health metric record
        health_metric = SystemHealthMetric.objects.create(
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory.percent,
            disk_usage_percent=disk.percent,
            db_connections_active=db_connections_active,
            db_connections_idle=db_connections_idle,
            db_query_avg_time_ms=db_query_avg_time_ms,
            redis_memory_usage_mb=redis_memory_usage_mb,
            redis_connected_clients=redis_connected_clients,
            redis_operations_per_sec=redis_operations_per_sec,
            celery_active_tasks=celery_active_tasks,
            celery_pending_tasks=celery_pending_tasks,
            celery_failed_tasks=celery_failed_tasks,
            active_users=active_users,
            api_requests_per_minute=api_requests,
            api_error_rate_percent=api_error_rate,
            overall_health=overall_health
        )
        
        # Create alert if health is critical
        if overall_health in ['critical', 'error']:
            Alert.objects.create(
                title=f"System health {overall_health}",
                description=f"System health score: {health_score}/100. CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%",
                alert_id=f"system_health_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                category=AlertCategory.SYSTEM_HEALTH,
                severity=AlertSeverity.CRITICAL if overall_health == 'error' else AlertSeverity.HIGH,
                metadata={
                    'health_score': health_score,
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'redis_connected': redis_connected
                }
            )
        
        logger.info(f"System health check completed. Status: {overall_health} ({health_score}/100)")
        
        return {
            'success': True,
            'health_status': overall_health,
            'health_score': health_score,
            'metrics': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'redis_connected': redis_connected,
                'celery_active_tasks': celery_active_tasks
            }
        }
        
    except Exception as e:
        logger.error(f"Error in system health check: {e}")
        
        # Create critical alert for health check failure
        try:
            Alert.objects.create(
                title="System health check failed",
                description=f"Unable to perform system health check: {str(e)}",
                alert_id=f"health_check_failed_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                category=AlertCategory.SYSTEM_HEALTH,
                severity=AlertSeverity.CRITICAL,
                metadata={'error': str(e)}
            )
        except Exception as alert_e:
            logger.error(f"Could not create health check failure alert: {alert_e}")
        
        return {'success': False, 'error': str(e)}


@shared_task
def update_monitoring_metrics(stats):
    """
    Update monitoring performance metrics
    """
    try:
        # Update cache with recent statistics
        cache.set('monitoring_stats', stats, 3600)  # 1 hour
        cache.set('last_monitoring_run', timezone.now().isoformat(), 3600)
        
        # Update service status based on monitoring results
        if stats.get('errors', 0) > 0:
            # Mark services as having issues if too many errors
            error_threshold = stats.get('layers_processed', 1) * 0.2  # 20% error rate
            
            if stats['errors'] >= error_threshold:
                logger.warning(f"High error rate in monitoring: {stats['errors']}/{stats['layers_processed']}")
                
                # This could trigger an alert or update service statuses
                # Implementation would depend on specific requirements
        
        logger.info(f"Updated monitoring metrics: {stats}")
        return {'success': True, 'stats': stats}
        
    except Exception as e:
        logger.error(f"Error updating monitoring metrics: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def run_data_quality_checks():
    """
    Run all active data quality rules.
    This is a simplified version. A full implementation would evaluate rule_expression.
    """
    try:
        logger.info("Starting data quality checks")
        
        # Get all active rules that need checking
        rules = DataQualityRule.objects.filter(
            is_active=True
        ).select_related('layer', 'service')
        
        results = []
        
        for rule in rules:
            if rule.needs_check:
                try:
                    logger.info(f"Running quality check: {rule.name}")
                    
                    # --- LÓGICA SIMULADA DE EVALUACIÓN DE REGLA ---
                    # En una implementación real, aquí se interpretaría rule.rule_expression
                    # y se ejecutaría la lógica contra los datos de la capa/servicio.
                    # Por ejemplo, podría ser una consulta SQL, una regla en un lenguaje específico,
                    # o una llamada a una función personalizada.
                    # Por ahora, simulamos un puntaje basado en placeholders o reglas simples.
                    
                    # Placeholder: Simular una evaluación
                    # Esto DEBE ser reemplazado por la lógica real de evaluación de la regla
                    total_records = 1000  # Obtener del servicio/capa
                    invalid_records = 50  # Determinado por la regla
                    valid_records = total_records - invalid_records
                    quality_score = valid_records / total_records if total_records > 0 else 1.0
                    
                    issues_found = []
                    recommendations = []
                    
                    if quality_score < rule.error_threshold:
                        issues_found.append("Quality score below error threshold")
                        recommendations.append("Review data source and cleaning processes.")
                    elif quality_score < rule.warning_threshold:
                        issues_found.append("Quality score below warning threshold")
                        recommendations.append("Monitor data quality closely.")
                    
                    # --- FIN LÓGICA SIMULADA ---
                    
                    # Create quality result
                    result = DataQualityResult.objects.create(
                        rule=rule,
                        quality_score=quality_score,
                        passed=quality_score >= rule.error_threshold,
                        total_records=total_records,
                        valid_records=valid_records,
                        invalid_records=invalid_records,
                        issues_found=issues_found,
                        recommendations=recommendations
                    )
                    
                    # Update rule's last check and score
                    rule.last_check = timezone.now()
                    rule.last_score = quality_score
                    rule.save(update_fields=['last_check', 'last_score'])
                    
                    results.append({
                        'rule_name': rule.name,
                        'quality_score': quality_score,
                        'passed': result.passed
                    })
                    
                    logger.info(f"Quality check completed: {rule.name} - Score: {quality_score}")
                    
                except Exception as e:
                    logger.error(f"Error running quality check {rule.name}: {e}")
                    # Opcional: Crear un resultado de error
                    # DataQualityResult.objects.create(rule=rule, quality_score=0.0, passed=False, error_message=str(e))
        
        logger.info(f"Completed {len(results)} data quality checks")
        return {
            'success': True,
            'checks_completed': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error in data quality checks: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def process_monitoring_job(job_id):
    """
    Process a specific monitoring job.
    Uses a group of tasks for each layer in the job to improve parallelism.
    """
    try:
        job = MonitoringJob.objects.get(id=job_id)
        
        # Create execution record
        execution = MonitoringJobExecution.objects.create(
            job=job,
            started_at=timezone.now()
        )
        
        execution.add_log_entry('INFO', f'Starting execution of job: {job.name}')
        
        try:
            # Get layers for this job
            layers = job.layers.filter(is_removed=False)
            total_layers = layers.count()
            
            if total_layers == 0:
                 execution.add_log_entry('INFO', f'No layers found for job: {job.name}')
                 execution.mark_completed(success=True)
                 job.record_execution(success=True)
                 logger.info(f"Monitoring job {job.name} completed successfully (no layers).")
                 return {
                    'success': True,
                    'job_name': job.name,
                    'layers_processed': 0,
                    'snapshots_created': 0,
                    'changes_detected': 0,
                    'alerts_created': 0
                }

            # Create a group of tasks for monitoring each layer in the job
            layer_monitor_tasks = [monitor_layer.s(layer.id) for layer in layers]
            job_group = group(*layer_monitor_tasks)
            
            # Execute the group
            result_group = job_group.apply_async()
            
            # Wait for all tasks in the group to complete and collect results
            layer_results = result_group.get(propagate=True)
            
            # Process results from the group
            layers_processed = len(layer_results)
            snapshots_created = sum(1 for lr in layer_results if lr.get('snapshot_created'))
            changes_detected = sum(1 for lr in layer_results if lr.get('changes_detected'))
            # alerts_created se contabiliza dentro de create_change_alert, no aquí directamente
            
            execution.layers_processed = layers_processed
            execution.snapshots_created = snapshots_created
            execution.changes_detected = changes_detected
            # alerts_created: Se podría rastrear cuántas tareas create_change_alert se lanzaron,
            # pero no cuántas se crearon exitosamente sin esperarlas también.
            # Por ahora, lo dejamos en 0 o lo calculamos de otra manera si es crítico.
            execution.alerts_created = 0 # Placeholder, se contabiliza en otro lado
            
            # Mark as completed
            execution.mark_completed(success=True)
            execution.add_log_entry('INFO', f'Job completed successfully. Processed {layers_processed} layers.')
            
            # Update job record
            job.record_execution(success=True)
            
            logger.info(f"Monitoring job {job.name} completed successfully")
            
            return {
                'success': True,
                'job_name': job.name,
                'layers_processed': layers_processed,
                'snapshots_created': snapshots_created,
                'changes_detected': changes_detected,
                'alerts_created': execution.alerts_created # Será 0 con este enfoque
            }
            
        except Exception as e:
            # Mark execution as failed
            execution.mark_completed(success=False, error_message=str(e))
            execution.add_log_entry('ERROR', f'Job failed: {str(e)}')
            
            # Update job record
            job.record_execution(success=False, error_message=str(e))
            
            logger.error(f"Monitoring job {job.name} failed: {e}")
            raise
        
    except MonitoringJob.DoesNotExist:
        logger.error(f"Monitoring job with ID {job_id} not found")
        return {'success': False, 'error': 'job_not_found'}
    
    except Exception as e:
        logger.error(f"Error processing monitoring job {job_id}: {e}")
        return {'success': False, 'error': str(e)}
