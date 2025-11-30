"""
Modelos core del sistema.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import os


class GeneratedFile(models.Model):
    """
    Registro de archivos generados por el sistema.
    Permite tracking, cleanup automático y prevención de duplicados.
    """
    
    CATEGORY_CHOICES = [
        ('export', 'Export'),
        ('report', 'Report'),
        ('analysis', 'Analysis'),
        ('monitoring', 'Monitoring'),
        ('temp', 'Temporary'),
        ('backup', 'Backup'),
    ]
    
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('downloading', 'Downloading'),
        ('expired', 'Expired'),
        ('error', 'Error'),
    ]
    
    file_path = models.CharField(
        max_length=500, 
        unique=True, 
        db_index=True,
        help_text="Ruta completa del archivo"
    )
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES, 
        db_index=True
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='generating'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='generated_files'
    )
    
    size = models.BigIntegerField(
        default=0, 
        help_text="Tamaño en bytes"
    )
    hash_md5 = models.CharField(
        max_length=32, 
        blank=True, 
        help_text="Hash MD5 del archivo"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(
        db_index=True, 
        help_text="Fecha de expiración"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    download_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'core_generated_file'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'status']),
            models.Index(fields=['expires_at', 'deleted_at']),
            models.Index(fields=['user', 'category']),
        ]
        verbose_name = 'Generated File'
        verbose_name_plural = 'Generated Files'
    
    def __str__(self):
        return f"{self.category}: {os.path.basename(self.file_path)}"
    
    @property
    def is_expired(self):
        """Verifica si el archivo expiró."""
        return timezone.now() > self.expires_at
    
    @property
    def is_locked(self):
        """Verifica si el archivo tiene un lock activo."""
        lock_path = f"{self.file_path}.lock"
        return os.path.exists(lock_path)
    
    @property
    def filename(self):
        """Retorna solo el nombre del archivo."""
        return os.path.basename(self.file_path)
    
    @property
    def size_mb(self):
        """Tamaño en MB."""
        return round(self.size / 1024 / 1024, 2)
    
    @property
    def size_kb(self):
        """Tamaño en KB."""
        return round(self.size / 1024, 2)
    
    def exists_on_disk(self):
        """Verifica si el archivo existe físicamente."""
        return os.path.exists(self.file_path)
    
    def get_age_hours(self):
        """Retorna edad del archivo en horas."""
        delta = timezone.now() - self.created_at
        return round(delta.total_seconds() / 3600, 2)
    
    def time_until_expiry(self):
        """Retorna tiempo hasta expiración en horas."""
        delta = self.expires_at - timezone.now()
        return round(delta.total_seconds() / 3600, 2)
    
    def mark_downloaded(self):
        """Marca el archivo como descargado (thread-safe)."""
        from django.db.models import F
        
        # Usar F() para incremento atómico
        self.__class__.objects.filter(pk=self.pk).update(
            download_count=F('download_count') + 1,
            last_accessed=timezone.now(),
            status='downloading'
        )
        self.refresh_from_db()
    
    def mark_ready(self):
        """Marca el archivo como listo."""
        self.status = 'ready'
        self.save(update_fields=['status'])
    
    def mark_error(self):
        """Marca el archivo con error."""
        self.status = 'error'
        self.save(update_fields=['status'])
    
    def can_be_deleted(self):
        """Verifica si el archivo puede ser eliminado."""
        # No eliminar si está bloqueado
        if self.is_locked:
            return False
        # No eliminar si ya fue eliminado
        if self.deleted_at:
            return False
        return True
    
    def can_be_downloaded(self):
        """Verifica si el archivo puede ser descargado."""
        # No descargar si expiró
        if self.is_expired:
            return False
        # No descargar si ya fue eliminado
        if self.deleted_at:
            return False
        # No descargar si tiene error
        if self.status == 'error':
            return False
        # No descargar si aún está generándose
        if self.status == 'generating':
            return False
        # Verificar que existe en disco
        if not self.exists_on_disk():
            return False
        return True
    
    def get_download_url(self):
        """Retorna URL relativa para descargar el archivo."""
        from django.conf import settings
        import os
        
        # Obtener ruta relativa desde MEDIA_ROOT
        media_root = str(settings.MEDIA_ROOT)
        if self.file_path.startswith(media_root):
            relative_path = os.path.relpath(self.file_path, media_root)
            return f"/media/{relative_path}"
        return None
    
    def extend_expiration(self, hours: int = 24):
        """Extiende la fecha de expiración."""
        self.expires_at = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['expires_at'])
    
    def delete_file(self):
        """Elimina el archivo físico y marca como eliminado."""
        if not self.can_be_deleted():
            raise ValueError("File cannot be deleted (locked or already deleted)")
        
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        
        # Eliminar lock si existe
        lock_path = f"{self.file_path}.lock"
        if os.path.exists(lock_path):
            os.remove(lock_path)
        
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
