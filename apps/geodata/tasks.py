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
