"""
Management command para limpiar archivos expirados.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.file_locking import FileRegistry


class Command(BaseCommand):
    help = 'Limpia archivos expirados y locks huérfanos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se eliminaría sin eliminar realmente',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza eliminación sin confirmación',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.WARNING('Iniciando limpieza de archivos...'))
        
        if not force and not dry_run:
            confirm = input('¿Desea continuar con la limpieza? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operación cancelada'))
                return
        
        # Limpiar archivos expirados
        self.stdout.write('\n1. Limpiando archivos expirados...')
        
        if dry_run:
            from apps.core.models import GeneratedFile
            expired_count = GeneratedFile.objects.filter(
                expires_at__lt=timezone.now(),
                deleted_at__isnull=True
            ).count()
            self.stdout.write(
                self.style.WARNING(f'   [DRY RUN] Se eliminarían {expired_count} archivos')
            )
        else:
            deleted_count, failed_count = FileRegistry.cleanup_expired()
            self.stdout.write(
                self.style.SUCCESS(f'   ✓ Eliminados: {deleted_count}')
            )
            if failed_count > 0:
                self.stdout.write(
                    self.style.ERROR(f'   ✗ Fallidos: {failed_count}')
                )
        
        # Limpiar locks huérfanos
        self.stdout.write('\n2. Limpiando locks huérfanos...')
        
        if dry_run:
            import glob
            lock_count = len(glob.glob('data/exports/**/*.lock', recursive=True))
            self.stdout.write(
                self.style.WARNING(f'   [DRY RUN] Se eliminarían {lock_count} locks')
            )
        else:
            removed = FileRegistry.cleanup_orphaned_locks()
            self.stdout.write(
                self.style.SUCCESS(f'   ✓ Locks eliminados: {removed}')
            )
        
        # Estadísticas finales
        self.stdout.write('\n3. Estadísticas de almacenamiento:')
        stats = FileRegistry.get_storage_stats()
        
        for category, data in stats.items():
            if category != 'total':
                self.stdout.write(
                    f'   • {category}: {data["count"]} archivos, {data["size_mb"]} MB'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n   TOTAL: {stats["total"]["count"]} archivos, {stats["total"]["size_mb"]} MB'
            )
        )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Limpieza completada'))
