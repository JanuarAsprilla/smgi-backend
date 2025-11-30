"""
Admin interface for core models.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import GeneratedFile


@admin.register(GeneratedFile)
class GeneratedFileAdmin(admin.ModelAdmin):
    list_display = [
        'filename_display', 'category', 'status_badge', 'size_display',
        'user', 'download_count', 'created_at', 'expires_at', 'is_expired_display'
    ]
    list_filter = ['category', 'status', 'created_at', 'expires_at']
    search_fields = ['file_path', 'user__username', 'hash_md5']
    readonly_fields = [
        'file_path', 'size', 'hash_md5', 'created_at', 'last_accessed',
        'download_count', 'deleted_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('File Information', {
            'fields': ('file_path', 'category', 'status', 'size', 'hash_md5')
        }),
        ('User & Access', {
            'fields': ('user', 'download_count', 'last_accessed')
        }),
        ('Lifecycle', {
            'fields': ('created_at', 'expires_at', 'deleted_at')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def filename_display(self, obj):
        """Muestra solo el nombre del archivo."""
        return obj.filename
    filename_display.short_description = 'Filename'
    
    def size_display(self, obj):
        """Muestra tamaño en MB."""
        return f"{obj.size_mb} MB"
    size_display.short_description = 'Size'
    size_display.admin_order_field = 'size'
    
    def is_expired_display(self, obj):
        """Indicador visual de expiración."""
        if obj.is_expired:
            return format_html('<span style="color: red;">●</span> Expired')
        return format_html('<span style="color: green;">●</span> Active')
    is_expired_display.short_description = 'Status'
    
    def status_badge(self, obj):
        """Display status as badge."""
        colors = {
            'generating': 'orange',
            'ready': 'green',
            'downloading': 'blue',
            'expired': 'red',
            'error': 'darkred'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    actions = ['delete_files', 'extend_expiration']
    
    def delete_files(self, request, queryset):
        """Elimina archivos seleccionados."""
        count = 0
        for obj in queryset:
            obj.delete_file()
            count += 1
        self.message_user(request, f'{count} files deleted successfully.')
    delete_files.short_description = "Delete selected files"
    
    def extend_expiration(self, request, queryset):
        """Extiende expiración 7 días."""
        from datetime import timedelta
        from django.utils import timezone
        
        queryset.update(expires_at=timezone.now() + timedelta(days=7))
        self.message_user(request, f'Extended expiration for {queryset.count()} files.')
    extend_expiration.short_description = "Extend expiration (+7 days)"
