"""
Sistema de file locking para prevenir race conditions.
"""
import os
import fcntl
import time
import logging
import hashlib
from contextlib import contextmanager
from typing import Optional
from pathlib import Path
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class FileLock:
    """
    File locking usando fcntl (Linux/Unix).
    Previene que múltiples procesos escriban el mismo archivo.
    """
    
    def __init__(self, file_path: str, timeout: int = 30):
        """
        Args:
            file_path: Ruta del archivo a lockear
            timeout: Segundos máximos para esperar el lock
        """
        self.file_path = Path(file_path)
        self.lock_file_path = Path(f"{file_path}.lock")
        self.timeout = timeout
        self.lock_file = None
        self._locked = False
    
    def acquire(self, blocking: bool = True) -> bool:
        """
        Adquiere el lock del archivo.
        
        Args:
            blocking: Si True, espera hasta obtener lock
        
        Returns:
            True si obtuvo el lock, False si no
        """
        # Crear directorio si no existe
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Abrir archivo .lock
        self.lock_file = open(self.lock_file_path, 'w')
        
        start_time = time.time()
        
        while True:
            try:
                # Intentar adquirir lock exclusivo
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Escribir info del lock
                self.lock_file.write(f"Locked at: {time.time()}\n")
                self.lock_file.write(f"PID: {os.getpid()}\n")
                self.lock_file.flush()
                
                self._locked = True
                logger.debug(f"Lock acquired: {self.lock_file_path}")
                return True
                
            except (IOError, OSError):
                # Lock no disponible
                if not blocking:
                    logger.debug(f"Lock not available: {self.lock_file_path}")
                    return False
                
                # Verificar timeout
                if time.time() - start_time > self.timeout:
                    logger.warning(f"Lock timeout: {self.lock_file_path}")
                    return False
                
                # Esperar un poco y reintentar
                time.sleep(0.1)
    
    def release(self):
        """Libera el lock."""
        if self._locked and self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                
                # Eliminar archivo .lock
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
                
                self._locked = False
                logger.debug(f"Lock released: {self.lock_file_path}")
                
            except Exception as e:
                logger.error(f"Error releasing lock: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise TimeoutError(f"Could not acquire lock for {self.file_path}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
    
    def __del__(self):
        """Destructor - asegurar que el lock se libere."""
        if self._locked:
            self.release()


@contextmanager
def file_lock(file_path: str, timeout: int = 30):
    """
    Context manager para file locking.
    
    Uso:
        with file_lock('/path/to/file.zip') as lock:
            # Operaciones con el archivo
            pass
    """
    lock = FileLock(file_path, timeout)
    try:
        if not lock.acquire():
            raise TimeoutError(f"Could not acquire lock for {file_path}")
        yield lock
    finally:
        lock.release()


class FileRegistry:
    """
    Registro de archivos generados para tracking y cleanup.
    """
    
    @staticmethod
    def register_file(file_path: str, 
                     category: str,
                     user_id: Optional[int] = None,
                     ttl_hours: Optional[int] = None,
                     metadata: dict = None) -> 'GeneratedFile':
        """
        Registra un archivo en la base de datos.
        
        Args:
            file_path: Ruta del archivo
            category: Categoría (export, report, analysis, etc.)
            user_id: ID del usuario que lo generó
            ttl_hours: Tiempo de vida en horas (None = usa default por categoría)
            metadata: Metadata adicional
        
        Returns:
            Instancia de GeneratedFile
        """
        from apps.core.models import GeneratedFile
        
        # TTL por categoría si no se especifica
        if ttl_hours is None:
            ttl_hours = {
                'export': 72,      # 3 días
                'report': 168,     # 7 días
                'analysis': 48,    # 2 días
                'monitoring': 720, # 30 días
                'temp': 24,        # 1 día
                'backup': None,    # Indefinido
            }.get(category, 72)
        
        # Calcular expiración
        if ttl_hours is not None:
            expires_at = timezone.now() + timedelta(hours=ttl_hours)
        else:
            expires_at = timezone.now() + timedelta(days=365 * 10)  # 10 años
        
        # Calcular MD5 si el archivo existe
        md5_hash = ''
        size = 0
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            md5_hash = FileRegistry._calculate_md5(file_path)
        
        # Crear registro
        file_record = GeneratedFile.objects.create(
            file_path=file_path,
            category=category,
            user_id=user_id,
            size=size,
            hash_md5=md5_hash,
            expires_at=expires_at,
            status='ready',
            metadata=metadata or {}
        )
        
        logger.info(f"Registered file: {file_path} (expires: {expires_at})")
        return file_record
    
    @staticmethod
    def _calculate_md5(file_path: str) -> str:
        """Calcula hash MD5 del archivo."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    @staticmethod
    def cleanup_expired():
        """Elimina archivos expirados."""
        from apps.core.models import GeneratedFile
        
        expired = GeneratedFile.objects.filter(
            expires_at__lt=timezone.now(),
            deleted_at__isnull=True
        )
        
        deleted_count = 0
        failed_count = 0
        
        for file_record in expired:
            try:
                if os.path.exists(file_record.file_path):
                    os.remove(file_record.file_path)
                    logger.info(f"Deleted expired file: {file_record.file_path}")
                
                # Eliminar .lock si existe
                lock_path = f"{file_record.file_path}.lock"
                if os.path.exists(lock_path):
                    os.remove(lock_path)
                
                file_record.deleted_at = timezone.now()
                file_record.save()
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Error deleting file {file_record.file_path}: {e}")
                failed_count += 1
        
        logger.info(f"Cleanup completed: {deleted_count} deleted, {failed_count} failed")
        return deleted_count, failed_count
    
    @staticmethod
    def cleanup_orphaned_locks():
        """Elimina archivos .lock huérfanos (>1 hora de antigüedad)."""
        import glob
        
        lock_files = glob.glob('data/exports/**/*.lock', recursive=True)
        removed = 0
        
        for lock_file in lock_files:
            try:
                # Verificar si es antiguo (>1 hora)
                if os.path.getmtime(lock_file) < (time.time() - 3600):
                    os.remove(lock_file)
                    removed += 1
                    logger.info(f"Removed orphaned lock: {lock_file}")
            except Exception as e:
                logger.warning(f"Could not remove lock {lock_file}: {e}")
        
        logger.info(f"Orphaned locks cleanup: {removed} removed")
        return removed
    
    @staticmethod
    def get_storage_stats():
        """Obtiene estadísticas de almacenamiento."""
        from apps.core.models import GeneratedFile
        from django.db.models import Sum, Count
        
        stats = {}
        
        # Por categoría
        by_category = GeneratedFile.objects.filter(
            deleted_at__isnull=True
        ).values('category').annotate(
            count=Count('id'),
            total_size=Sum('size')
        )
        
        for item in by_category:
            stats[item['category']] = {
                'count': item['count'],
                'size_mb': round((item['total_size'] or 0) / 1024 / 1024, 2)
            }
        
        # Total
        total = GeneratedFile.objects.filter(
            deleted_at__isnull=True
        ).aggregate(
            count=Count('id'),
            total_size=Sum('size')
        )
        
        stats['total'] = {
            'count': total['count'],
            'size_mb': round((total['total_size'] or 0) / 1024 / 1024, 2)
        }
        
        return stats
