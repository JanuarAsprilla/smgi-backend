"""
Management command to create sample agents.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.agents.models import AgentCategory, Agent, AgentTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample agents for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username of the user who will own the agents',
        )

    def handle(self, *args, **options):
        username = options.get('user', 'admin')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User {username} does not exist. Creating admin user...')
            )
            user = User.objects.create_superuser(
                username='admin',
                email='admin@smgi.com',
                password='admin123',
                role='admin'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Admin user created: admin / admin123')
            )

        # Create categories
        self.stdout.write('Creating agent categories...')
        
        categories = [
            {
                'name': 'Análisis',
                'description': 'Agentes para análisis estadístico y de datos',
                'icon': 'chart-bar',
                'color': '#3B82F6'
            },
            {
                'name': 'Detección',
                'description': 'Agentes para detección de cambios y anomalías',
                'icon': 'eye',
                'color': '#EF4444'
            },
            {
                'name': 'Clasificación',
                'description': 'Agentes para clasificación de datos',
                'icon': 'grid',
                'color': '#10B981'
            },
            {
                'name': 'Monitoreo',
                'description': 'Agentes para monitoreo continuo',
                'icon': 'monitor',
                'color': '#F59E0B'
            }
        ]
        
        created_categories = {}
        for cat_data in categories:
            category, created = AgentCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'icon': cat_data['icon'],
                    'color': cat_data['color'],
                    'created_by': user
                }
            )
            created_categories[cat_data['name']] = category
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Category created: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  - Category exists: {category.name}')
                )

        # Create sample agents
        self.stdout.write('\nCreating sample agents...')
        
        agents = [
            {
                'name': 'Contador de Features',
                'description': 'Cuenta el número de features en una capa',
                'category': 'Análisis',
                'agent_type': 'statistics',
                'code': '''
import logging
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
count = layer.features.filter(is_active=True).count()

output_data['feature_count'] = count
output_data['layer_name'] = layer.name

logger.info(f"Total de features en {layer.name}: {count}")
''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {}
                },
                'status': 'published',
                'is_public': True
            },
            {
                'name': 'Comparador de Capas',
                'description': 'Compara dos capas y detecta diferencias',
                'category': 'Detección',
                'agent_type': 'change_detection',
                'code': '''
import logging
logger = logging.getLogger(__name__)

if len(input_layers) < 2:
    raise ValueError("Se requieren al menos 2 capas para comparar")

layer1 = input_layers[0]
layer2 = input_layers[1]

count1 = layer1.features.filter(is_active=True).count()
count2 = layer2.features.filter(is_active=True).count()

difference = abs(count2 - count1)
percentage_change = (difference / count1 * 100) if count1 > 0 else 0

output_data['layer1_count'] = count1
output_data['layer2_count'] = count2
output_data['difference'] = difference
output_data['percentage_change'] = round(percentage_change, 2)

logger.info(f"Capa 1: {count1} features, Capa 2: {count2} features")
logger.info(f"Diferencia: {difference} ({percentage_change:.2f}%)")
''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {}
                },
                'status': 'published',
                'is_public': True
            },
            {
                'name': 'Calculador de Área',
                'description': 'Calcula el área total de features en una capa',
                'category': 'Análisis',
                'agent_type': 'statistics',
                'code': '''
import logging
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
features = layer.features.filter(is_active=True)

total_area = 0
count = 0

for feature in features:
    if feature.geometry and feature.geometry.area:
        total_area += feature.geometry.area
        count += 1

avg_area = total_area / count if count > 0 else 0

output_data['total_area'] = round(total_area, 2)
output_data['feature_count'] = count
output_data['average_area'] = round(avg_area, 2)

logger.info(f"Área total: {total_area:.2f}")
logger.info(f"Promedio por feature: {avg_area:.2f}")
''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {}
                },
                'status': 'published',
                'is_public': True
            },
            {
                'name': 'Filtro por Atributos',
                'description': 'Filtra features basado en atributos específicos',
                'category': 'Clasificación',
                'agent_type': 'classification',
                'code': '''
import logging
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
attribute_name = parameters.get('attribute_name')
attribute_value = parameters.get('attribute_value')

if not attribute_name:
    raise ValueError("Se requiere especificar 'attribute_name' en parámetros")

features = layer.features.filter(is_active=True)
matching_features = []

for feature in features:
    if hasattr(feature, 'properties') and feature.properties:
        if feature.properties.get(attribute_name) == attribute_value:
            matching_features.append(feature.id)

output_data['total_features'] = features.count()
output_data['matching_features'] = len(matching_features)
output_data['filter_criteria'] = {
    'attribute': attribute_name,
    'value': attribute_value
}
output_layers = matching_features

logger.info(f"Filtradas {len(matching_features)} de {features.count()} features")
''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'attribute_name': {
                            'type': 'string',
                            'description': 'Nombre del atributo a filtrar'
                        },
                        'attribute_value': {
                            'type': 'string',
                            'description': 'Valor del atributo a buscar'
                        }
                    },
                    'required': ['attribute_name']
                },
                'status': 'published',
                'is_public': True
            }
        ]
        
        for agent_data in agents:
            category = created_categories.get(agent_data['category'])
            
            agent, created = Agent.objects.get_or_create(
                name=agent_data['name'],
                defaults={
                    'description': agent_data['description'],
                    'category': category,
                    'agent_type': agent_data['agent_type'],
                    'code': agent_data['code'],
                    'parameters_schema': agent_data['parameters_schema'],
                    'status': agent_data['status'],
                    'is_public': agent_data['is_public'],
                    'created_by': user
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Agent created: {agent.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  - Agent exists: {agent.name}')
                )

        # Create templates
        self.stdout.write('\nCreating agent templates...')
        
        templates = [
            {
                'name': 'Template: Análisis Estadístico',
                'description': 'Plantilla para crear agentes de análisis estadístico',
                'category': 'Análisis',
                'agent_type': 'statistics',
                'code_template': '''
import logging
logger = logging.getLogger(__name__)

# Tu código aquí
layer = input_layers[0]

# Realizar análisis
# ...

output_data['result'] = 'Tu resultado aquí'
logger.info("Análisis completado")
''',
                'is_featured': True
            },
            {
                'name': 'Template: Detección de Cambios',
                'description': 'Plantilla para crear agentes de detección de cambios',
                'category': 'Detección',
                'agent_type': 'change_detection',
                'code_template': '''
import logging
logger = logging.getLogger(__name__)

layer1 = input_layers[0]
layer2 = input_layers[1]

# Comparar capas
# ...

output_data['changes'] = []
logger.info("Detección de cambios completada")
''',
                'is_featured': True
            }
        ]
        
        for template_data in templates:
            category = created_categories.get(template_data['category'])
            
            template, created = AgentTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults={
                    'description': template_data['description'],
                    'category': category,
                    'agent_type': template_data['agent_type'],
                    'code_template': template_data['code_template'],
                    'parameters_schema': {},
                    'is_featured': template_data.get('is_featured', False),
                    'created_by': user
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Template created: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  - Template exists: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('\n✓ Sample agents setup completed successfully!')
        )
