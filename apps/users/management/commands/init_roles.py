"""
Comando para inicializar roles por defecto
"""
from django.core.management.base import BaseCommand
from apps.users.models import Role


class Command(BaseCommand):
    help = 'Inicializa los roles por defecto del sistema'

    def handle(self, *args, **options):
        roles_data = [
            {
                'name': 'Super Administrador',
                'role_type': 'super_admin',
                'description': 'Acceso total al sistema sin restricciones',
                'can_upload_layers': True,
                'can_view_layers': True,
                'can_edit_layers': True,
                'can_delete_layers': True,
                'can_download_layers': True,
                'can_create_analysis': True,
                'can_view_analysis': True,
                'can_delete_analysis': True,
                'can_upload_agents': True,
                'can_create_monitors': True,
                'can_view_monitors': True,
                'can_configure_alerts': True,
                'can_manage_users': True,
                'can_approve_users': True,
                'can_create_areas': True,
                'can_share_resources': True,
                'can_export_reports': True,
                'can_view_audit_logs': True,
                'is_system_role': True,
            },
            {
                'name': 'Administrador de Área',
                'role_type': 'area_admin',
                'description': 'Gestiona usuarios y recursos de su área',
                'can_upload_layers': True,
                'can_view_layers': True,
                'can_edit_layers': True,
                'can_delete_layers': True,
                'can_download_layers': True,
                'can_create_analysis': True,
                'can_view_analysis': True,
                'can_delete_analysis': True,
                'can_upload_agents': True,
                'can_create_monitors': True,
                'can_view_monitors': True,
                'can_configure_alerts': True,
                'can_manage_users': False,
                'can_approve_users': True,
                'can_create_areas': False,
                'can_share_resources': True,
                'can_export_reports': True,
                'can_view_audit_logs': True,
                'is_system_role': True,
            },
            {
                'name': 'Analista IA',
                'role_type': 'analyst_ai',
                'description': 'Ejecuta análisis con IA y sube agentes personalizados',
                'can_upload_layers': False,
                'can_view_layers': True,
                'can_edit_layers': False,
                'can_delete_layers': False,
                'can_download_layers': False,
                'can_create_analysis': True,
                'can_view_analysis': True,
                'can_delete_analysis': False,
                'can_upload_agents': True,
                'can_create_monitors': False,
                'can_view_monitors': True,
                'can_configure_alerts': False,
                'can_manage_users': False,
                'can_approve_users': False,
                'can_create_areas': False,
                'can_share_resources': False,
                'can_export_reports': False,
                'can_view_audit_logs': False,
                'is_system_role': True,
            },
            {
                'name': 'Cargador de Capas',
                'role_type': 'loader',
                'description': 'Sube y gestiona capas geoespaciales',
                'can_upload_layers': True,
                'can_view_layers': True,
                'can_edit_layers': True,
                'can_delete_layers': False,
                'can_download_layers': False,
                'can_create_analysis': False,
                'can_view_analysis': False,
                'can_delete_analysis': False,
                'can_upload_agents': False,
                'can_create_monitors': False,
                'can_view_monitors': False,
                'can_configure_alerts': False,
                'can_manage_users': False,
                'can_approve_users': False,
                'can_create_areas': False,
                'can_share_resources': False,
                'can_export_reports': False,
                'can_view_audit_logs': False,
                'is_system_role': True,
            },
            {
                'name': 'Visualizador',
                'role_type': 'viewer',
                'description': 'Solo puede ver capas y resultados',
                'can_upload_layers': False,
                'can_view_layers': True,
                'can_edit_layers': False,
                'can_delete_layers': False,
                'can_download_layers': False,
                'can_create_analysis': False,
                'can_view_analysis': True,
                'can_delete_analysis': False,
                'can_upload_agents': False,
                'can_create_monitors': False,
                'can_view_monitors': True,
                'can_configure_alerts': False,
                'can_manage_users': False,
                'can_approve_users': False,
                'can_create_areas': False,
                'can_share_resources': False,
                'can_export_reports': True,
                'can_view_audit_logs': False,
                'is_system_role': True,
            },
            {
                'name': 'Descargador',
                'role_type': 'downloader',
                'description': 'Puede descargar capas y resultados',
                'can_upload_layers': False,
                'can_view_layers': True,
                'can_edit_layers': False,
                'can_delete_layers': False,
                'can_download_layers': True,
                'can_create_analysis': False,
                'can_view_analysis': True,
                'can_delete_analysis': False,
                'can_upload_agents': False,
                'can_create_monitors': False,
                'can_view_monitors': False,
                'can_configure_alerts': False,
                'can_manage_users': False,
                'can_approve_users': False,
                'can_create_areas': False,
                'can_share_resources': False,
                'can_export_reports': True,
                'can_view_audit_logs': False,
                'is_system_role': True,
            },
        ]
        
        created_count = 0
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                role_type=role_data['role_type'],
                defaults=role_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Rol creado: {role.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Rol ya existe: {role.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Proceso completado: {created_count} roles creados')
        )
