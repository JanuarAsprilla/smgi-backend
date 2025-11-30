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


@shared_task(name='core.cleanup_temp_files')
def cleanup_temp_files():
    """
    Elimina archivos temporales antiguos (>24 horas).
    Se ejecuta cada 6 horas.
    """
    logger.info("Cleaning up temp files...")
    
    try:
        from apps.core.models import GeneratedFile
        from django.utils import timezone
        from datetime import timedelta
        
        # Archivos temp con más de 24 horas
        old_temp = GeneratedFile.objects.filter(
            category='temp',
            created_at__lt=timezone.now() - timedelta(hours=24),
            deleted_at__isnull=True
        )
        
        deleted_count = 0
        for file_record in old_temp:
            try:
                file_record.delete_file()
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting temp file {file_record.file_path}: {e}")
        
        result = {
            'success': True,
            'deleted': deleted_count
        }
        
        logger.info(f"Temp cleanup completed: {deleted_count} deleted")
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning temp files: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='core.check_file_integrity')
def check_file_integrity():
    """
    Verifica integridad de archivos registrados.
    Se ejecuta diariamente.
    """
    logger.info("Checking file integrity...")
    
    try:
        from apps.core.models import GeneratedFile
        import os
        
        files = GeneratedFile.objects.filter(
            deleted_at__isnull=True,
            status='ready'
        )
        
        missing_count = 0
        size_mismatch = 0
        
        for file_record in files:
            # Verificar existencia
            if not os.path.exists(file_record.file_path):
                logger.warning(f"Missing file: {file_record.file_path}")
                file_record.mark_error()
                missing_count += 1
                continue
            
            # Verificar tamaño
            actual_size = os.path.getsize(file_record.file_path)
            if actual_size != file_record.size:
                logger.warning(
                    f"Size mismatch: {file_record.file_path} "
                    f"(expected {file_record.size}, got {actual_size})"
                )
                file_record.size = actual_size
                file_record.save(update_fields=['size'])
                size_mismatch += 1
        
        result = {
            'success': True,
            'checked': files.count(),
            'missing': missing_count,
            'size_mismatch': size_mismatch
        }
        
        logger.info(
            f"Integrity check completed: {files.count()} checked, "
            f"{missing_count} missing, {size_mismatch} size mismatches"
        )
        return result
        
    except Exception as e:
        logger.error(f"Error checking integrity: {e}")
        return {'success': False, 'error': str(e)}
