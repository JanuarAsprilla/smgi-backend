"""
Celery tasks for Geodata app.
"""
from celery import shared_task
from django.utils import timezone
from .models import DataSource, Layer, Feature, SyncLog
import logging
import requests
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def sync_data_source(data_source_id):
    """
    Synchronize data from a data source.
    
    Args:
        data_source_id: ID of the DataSource to sync
    """
    try:
        data_source = DataSource.objects.get(id=data_source_id)
        
        # Create sync log
        sync_log = SyncLog.objects.create(
            data_source=data_source,
            status=SyncLog.Status.FAILED  # Default to failed, update on success
        )
        
        logger.info(f"Starting sync for data source: {data_source.name}")
        
        # Perform sync based on source type
        if data_source.source_type == DataSource.SourceType.WFS:
            result = sync_wfs_source(data_source, sync_log)
        elif data_source.source_type == DataSource.SourceType.API:
            result = sync_api_source(data_source, sync_log)
        elif data_source.source_type == DataSource.SourceType.WMS:
            result = sync_wms_source(data_source, sync_log)
        else:
            result = {
                'status': 'failed',
                'error': f'Sync not implemented for type: {data_source.source_type}'
            }
        
        # Update sync log
        sync_log.completed_at = timezone.now()
        sync_log.status = SyncLog.Status.SUCCESS if result['status'] == 'success' else SyncLog.Status.FAILED
        sync_log.records_processed = result.get('processed', 0)
        sync_log.records_added = result.get('added', 0)
        sync_log.records_updated = result.get('updated', 0)
        sync_log.records_failed = result.get('failed', 0)
        sync_log.error_message = result.get('error', '')
        sync_log.details = result.get('details', {})
        sync_log.save()
        
        # Update data source last_sync
        data_source.last_sync = timezone.now()
        data_source.status = DataSource.Status.ACTIVE if result['status'] == 'success' else DataSource.Status.ERROR
        data_source.save()
        
        logger.info(f"Sync completed for {data_source.name}: {result['status']}")
        return result
        
    except DataSource.DoesNotExist:
        logger.error(f"DataSource {data_source_id} not found")
        return {'status': 'failed', 'error': 'DataSource not found'}
    except Exception as e:
        logger.error(f"Error syncing data source {data_source_id}: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


def sync_wfs_source(data_source, sync_log):
    """
    Sync data from a WFS (Web Feature Service) source.
    """
    try:
        # TODO: Implement actual WFS sync logic
        # This is a placeholder implementation
        
        logger.info(f"Syncing WFS source: {data_source.url}")
        
        # Example: Get features from WFS
        # params = {
        #     'service': 'WFS',
        #     'version': '2.0.0',
        #     'request': 'GetFeature',
        #     'typeName': data_source.configuration.get('layer_name'),
        #     'outputFormat': 'application/json'
        # }
        # response = requests.get(data_source.url, params=params, timeout=30)
        # response.raise_for_status()
        # geojson_data = response.json()
        
        # Process features...
        
        return {
            'status': 'success',
            'processed': 0,
            'added': 0,
            'updated': 0,
            'failed': 0,
            'details': {'message': 'WFS sync placeholder'}
        }
        
    except Exception as e:
        logger.error(f"Error syncing WFS source: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'processed': 0,
            'added': 0,
            'updated': 0,
            'failed': 0
        }


def sync_api_source(data_source, sync_log):
    """
    Sync data from a REST API source.
    """
    try:
        logger.info(f"Syncing API source: {data_source.url}")
        
        # Get authentication headers if needed
        headers = {}
        if 'api_key' in data_source.credentials:
            headers['Authorization'] = f"Bearer {data_source.credentials['api_key']}"
        
        # Make API request
        response = requests.get(
            data_source.url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # TODO: Process API response and create/update features
        # This depends on the API structure
        
        return {
            'status': 'success',
            'processed': 0,
            'added': 0,
            'updated': 0,
            'failed': 0,
            'details': {'message': 'API sync placeholder'}
        }
        
    except Exception as e:
        logger.error(f"Error syncing API source: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'processed': 0,
            'added': 0,
            'updated': 0,
            'failed': 0
        }


def sync_wms_source(data_source, sync_log):
    """
    Sync metadata from a WMS (Web Map Service) source.
    """
    try:
        logger.info(f"Syncing WMS source: {data_source.url}")
        
        # Get WMS capabilities
        params = {
            'service': 'WMS',
            'version': '1.3.0',
            'request': 'GetCapabilities'
        }
        response = requests.get(data_source.url, params=params, timeout=30)
        response.raise_for_status()
        
        # TODO: Parse WMS capabilities XML and update layers
        
        return {
            'status': 'success',
            'processed': 0,
            'added': 0,
            'updated': 0,
            'failed': 0,
            'details': {'message': 'WMS capabilities retrieved'}
        }
        
    except Exception as e:
        logger.error(f"Error syncing WMS source: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'processed': 0,
            'added': 0,
            'updated': 0,
            'failed': 0
        }


@shared_task
def auto_sync_data_sources():
    """
    Automatically sync all active data sources based on their refresh_interval.
    This task should be run periodically via Celery Beat.
    """
    logger.info("Starting auto-sync for all data sources")
    
    # Get data sources that need syncing
    now = timezone.now()
    data_sources = DataSource.objects.filter(
        is_active=True,
        status=DataSource.Status.ACTIVE,
        refresh_interval__gt=0
    )
    
    synced_count = 0
    for data_source in data_sources:
        # Check if it's time to sync
        if data_source.last_sync:
            next_sync = data_source.last_sync + timedelta(minutes=data_source.refresh_interval)
            if now < next_sync:
                continue
        
        # Trigger sync
        sync_data_source.delay(data_source.id)
        synced_count += 1
    
    logger.info(f"Auto-sync triggered for {synced_count} data sources")
    return f"Synced {synced_count} data sources"


@shared_task
def cleanup_old_sync_logs(days=30):
    """
    Delete sync logs older than specified days.
    
    Args:
        days: Number of days to keep logs
    """
    threshold_date = timezone.now() - timedelta(days=days)
    deleted = SyncLog.objects.filter(started_at__lt=threshold_date).delete()
    
    logger.info(f"Deleted {deleted[0]} old sync logs")
    return f"Deleted {deleted[0]} sync logs"


@shared_task
def update_layer_statistics(layer_id):
    """
    Update statistics for a layer.
    
    Args:
        layer_id: ID of the Layer
    """
    try:
        layer = Layer.objects.get(id=layer_id)
        
        # Update feature count and other statistics
        feature_count = layer.features.filter(is_active=True).count()
        
        # Calculate extent if not set
        if not layer.extent and feature_count > 0:
            from django.contrib.gis.db.models.functions import Extent
            extent = layer.features.filter(is_active=True).aggregate(Extent('geometry'))
            # TODO: Set layer.extent with calculated extent
        
        logger.info(f"Updated statistics for layer {layer.name}: {feature_count} features")
        return {'status': 'success', 'feature_count': feature_count}
        
    except Layer.DoesNotExist:
        logger.error(f"Layer {layer_id} not found")
        return {'status': 'failed', 'error': 'Layer not found'}
    except Exception as e:
        logger.error(f"Error updating layer statistics: {str(e)}")
        return {'status': 'failed', 'error': str(e)}

# ============================================================================
# PROCESAMIENTO ASÍNCRONO DE UPLOADS GRANDES
# ============================================================================

@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def process_layer_upload(self, layer_id, file_path, original_filename, user_id):
    """
    Procesa la subida de una capa de forma asíncrona.
    Optimizado para archivos grandes (1GB+, 100k+ features).
    """
    from django.contrib.gis.geos import GEOSGeometry
    from apps.users.models import User
    import geopandas as gpd
    import tempfile
    import shutil
    import zipfile
    import os
    import gc
    from pathlib import Path
    
    sync_log = None
    temp_dir = None
    
    try:
        layer = Layer.objects.get(id=layer_id)
        user = User.objects.get(id=user_id)
        
        # Crear log de sincronización
        sync_log = SyncLog.objects.create(
            layer=layer,
            status='processing',
            details={
                'task_id': self.request.id,
                'filename': original_filename,
                'started_at': timezone.now().isoformat()
            }
        )
        
        logger.info(f"[Task {self.request.id}] Iniciando: {layer.name}")
        logger.info(f"[Task {self.request.id}] Archivo: {original_filename}")
        
        # Directorio temporal
        temp_dir = tempfile.mkdtemp(prefix='smgi_upload_')
        
        # Leer archivo
        logger.info(f"[Task {self.request.id}] Leyendo archivo...")
        gdf = _read_upload_file(file_path, original_filename, temp_dir)
        
        total_features = len(gdf)
        logger.info(f"[Task {self.request.id}] Total features: {total_features}")
        
        if total_features == 0:
            raise ValueError('El archivo no contiene features')
        
        # Reproyectar si es necesario
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            logger.info(f"[Task {self.request.id}] Reproyectando de {gdf.crs} a EPSG:4326...")
            gdf = gdf.to_crs(epsg=4326)
        elif gdf.crs is None:
            logger.warning(f"[Task {self.request.id}] Sin CRS, asumiendo EPSG:4326")
            gdf = gdf.set_crs(epsg=4326)
        
        # Detectar tipo de geometría
        geom_types = gdf.geometry.geom_type.unique()
        geom_type = 'GEOMETRY' if len(geom_types) > 1 else str(geom_types[0]).upper()
        
        layer.geometry_type = geom_type
        layer.save(update_fields=['geometry_type'])
        
        # Tamaño de lote según cantidad de features
        if total_features > 50000:
            batch_size = 250
        elif total_features > 10000:
            batch_size = 500
        else:
            batch_size = 1000
        
        features_created = 0
        features_failed = 0
        
        logger.info(f"[Task {self.request.id}] Procesando en lotes de {batch_size}...")
        
        columns = [col for col in gdf.columns if col != 'geometry']
        
        for start_idx in range(0, total_features, batch_size):
            end_idx = min(start_idx + batch_size, total_features)
            batch_gdf = gdf.iloc[start_idx:end_idx]
            
            features_batch = []
            
            for idx, row in batch_gdf.iterrows():
                if row.geometry is None or row.geometry.is_empty:
                    features_failed += 1
                    continue
                
                # Extraer propiedades
                props = {}
                for col in columns:
                    val = row[col]
                    if hasattr(val, 'item'):
                        val = val.item()
                    if val != val:  # NaN
                        val = None
                    if val is not None and not isinstance(val, (str, int, float, bool, list, dict)):
                        val = str(val)
                    props[col] = val
                
                try:
                    geom = GEOSGeometry(row.geometry.wkt, srid=4326)
                    features_batch.append(Feature(
                        layer=layer,
                        geometry=geom,
                        properties=props,
                        created_by=user
                    ))
                except Exception as e:
                    features_failed += 1
                    continue
            
            # Insertar lote
            if features_batch:
                Feature.objects.bulk_create(features_batch, batch_size=batch_size)
                features_created += len(features_batch)
            
            # Progreso
            progress = int((end_idx / total_features) * 100)
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': end_idx,
                    'total': total_features,
                    'percent': progress,
                    'created': features_created,
                    'failed': features_failed
                }
            )
            
            # Actualizar log
            sync_log.records_processed = end_idx
            sync_log.records_added = features_created
            sync_log.records_failed = features_failed
            sync_log.details['progress'] = progress
            sync_log.save(update_fields=['records_processed', 'records_added', 'records_failed', 'details'])
            
            if progress % 10 == 0:
                logger.info(f"[Task {self.request.id}] Progreso: {progress}% ({features_created} features)")
            
            # Liberar memoria
            del features_batch
            gc.collect()
        
        # Finalizar
        layer.feature_count = features_created
        layer.metadata = {
            'processed_at': timezone.now().isoformat(),
            'task_id': self.request.id,
            'total_features': total_features,
            'features_created': features_created,
            'features_failed': features_failed
        }
        layer.save(update_fields=['feature_count', 'metadata'])
        
        sync_log.status = 'success'
        sync_log.completed_at = timezone.now()
        sync_log.records_processed = total_features
        sync_log.records_added = features_created
        sync_log.records_failed = features_failed
        sync_log.details['message'] = f'Completado: {features_created} features'
        sync_log.details['completed_at'] = timezone.now().isoformat()
        sync_log.save()
        
        logger.info(f"[Task {self.request.id}] ✓ COMPLETADO: {features_created} features, {features_failed} fallidos")
        
        return {
            'success': True,
            'layer_id': layer.id,
            'layer_name': layer.name,
            'features_created': features_created,
            'features_failed': features_failed
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Task {self.request.id}] ✗ ERROR: {error_msg}", exc_info=True)
        
        if sync_log:
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.error_message = error_msg
            sync_log.save()
        
        try:
            layer = Layer.objects.get(id=layer_id)
            if layer.feature_count == 0:
                layer.delete()
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        raise
        
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        gc.collect()


def _read_upload_file(file_path, filename, temp_dir):
    """Lee archivos geoespaciales para upload."""
    import geopandas as gpd
    import zipfile
    from pathlib import Path
    
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.zip'):
        with zipfile.ZipFile(file_path) as zf:
            zf.extractall(temp_dir)
        
        for pattern in ['*.shp', '*.geojson', '*.json', '*.gpkg']:
            files = list(Path(temp_dir).rglob(pattern))
            if files:
                return gpd.read_file(str(files[0]))
        
        kml_files = list(Path(temp_dir).rglob('*.kml'))
        if kml_files:
            return gpd.read_file(str(kml_files[0]), driver='KML')
        
        raise ValueError('No se encontró archivo geoespacial en el ZIP')
    
    elif filename_lower.endswith(('.geojson', '.json')):
        return gpd.read_file(file_path)
    elif filename_lower.endswith('.kml'):
        return gpd.read_file(file_path, driver='KML')
    elif filename_lower.endswith('.gpkg'):
        return gpd.read_file(file_path)
    elif filename_lower.endswith('.shp'):
        return gpd.read_file(file_path)
    else:
        raise ValueError(f'Formato no soportado: {filename}')