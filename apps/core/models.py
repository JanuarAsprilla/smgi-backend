"""
Modelos core del sistema.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
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
    
    def mark_downloaded(self):
        """Marca el archivo como descargado."""
        self.download_count += 1
        self.last_accessed = timezone.now()
        self.status = 'downloading'
        self.save(update_fields=['download_count', 'last_accessed', 'status'])
    
    def mark_ready(self):
        """Marca el archivo como listo."""
        self.status = 'ready'
        self.save(update_fields=['status'])
    
    def mark_error(self):
        """Marca el archivo con error."""
        self.status = 'error'
        self.save(update_fields=['status'])
    
    def delete_file(self):
        """Elimina el archivo físico y marca como eliminado."""
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        
        # Eliminar lock si existe
        lock_path = f"{self.file_path}.lock"
        if os.path.exists(lock_path):
            os.remove(lock_path)
        
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
