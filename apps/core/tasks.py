"""
Tareas Celery para gestión de archivos.
"""
from celery import shared_task
from apps.core.file_locking import FileRegistry
import logging

logger = logging.getLogger(__name__)


@shared_task(name='core.cleanup_expired_files')
def cleanup_expired_files():
    """
    Elimina archivos expirados.
    Se ejecuta cada hora.
    """
    logger.info("Starting cleanup of expired files...")
    
    try:
        deleted_count, failed_count = FileRegistry.cleanup_expired()
        
        result = {
            'success': True,
            'deleted': deleted_count,
            'failed': failed_count
        }
        
        logger.info(f"Cleanup completed: {deleted_count} deleted, {failed_count} failed")
        return result
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='core.cleanup_orphaned_locks')
def cleanup_orphaned_locks():
    """
    Elimina archivos .lock huérfanos.
    Se ejecuta cada hora.
    """
    logger.info("Cleaning up orphaned lock files...")
    
    try:
        removed = FileRegistry.cleanup_orphaned_locks()
        
        result = {
            'success': True,
            'removed': removed
        }
        
        logger.info(f"Lock cleanup completed: {removed} removed")
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning locks: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='core.generate_storage_report')
def generate_storage_report():
    """
    Genera reporte de uso de almacenamiento.
    Se ejecuta diariamente.
    """
    logger.info("Generating storage report...")
    
    try:
        stats = FileRegistry.get_storage_stats()
        
        logger.info("Storage stats:")
        for category, data in stats.items():
            logger.info(f"  {category}: {data['count']} files, {data['size_mb']} MB")
        
        return {'success': True, 'stats': stats}
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {'success': False, 'error': str(e)}
