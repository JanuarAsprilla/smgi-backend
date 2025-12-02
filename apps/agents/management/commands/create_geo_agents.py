# create_geo_agents.py
# 
# Script para crear agentes geoespaciales predeterminados en SMGI
# 
# USO:
# 1. Copia este archivo a: smgi-backend/apps/agents/management/commands/create_geo_agents.py
# 2. Ejecuta: python manage.py create_geo_agents
#

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.agents.models import Agent, AgentCategory

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea agentes geoespaciales predeterminados para SMGI'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🤖 Creando Agentes Geoespaciales Predeterminados...\n'))

        # Obtener o crear usuario admin
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()
        
        if not admin_user:
            self.stdout.write(self.style.ERROR('❌ No se encontró ningún usuario. Crea un usuario primero.'))
            return

        # Crear categorías
        categories = {
            'Análisis': self.create_category('Análisis', 'Agentes de análisis estadístico', 'chart-bar', '#3B82F6'),
            'Validación': self.create_category('Validación', 'Agentes de validación de datos', 'shield-check', '#10B981'),
            'Transformación': self.create_category('Transformación', 'Agentes de transformación de datos', 'arrows-exchange', '#F59E0B'),
            'Detección': self.create_category('Detección', 'Agentes de detección de cambios', 'search', '#EF4444'),
            'Exportación': self.create_category('Exportación', 'Agentes de generación de reportes', 'file-text', '#8B5CF6'),
        }

        # Definir agentes
        agents_data = [
            {
                'name': 'Análisis Estadístico Completo',
                'description': 'Calcula estadísticas completas de una capa: área total, perímetro, conteo de features, estadísticas de atributos numéricos (min, max, promedio, suma).',
                'category': 'Análisis',
                'agent_type': 'statistics',
                'code': '''import logging
import json
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
features = layer.features.filter(is_active=True)

# Estadísticas básicas
total_features = features.count()
total_area = 0
total_perimeter = 0

for feature in features:
    if feature.geometry:
        if hasattr(feature.geometry, 'area'):
            total_area += feature.geometry.area
        if hasattr(feature.geometry, 'length'):
            total_perimeter += feature.geometry.length

# Análisis de atributos numéricos
attribute_stats = {}
if total_features > 0:
    sample = features.first()
    if sample and sample.properties:
        for key, value in sample.properties.items():
            if isinstance(value, (int, float)):
                values = [f.properties.get(key, 0) for f in features if f.properties]
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    attribute_stats[key] = {
                        'min': min(numeric_values),
                        'max': max(numeric_values),
                        'avg': round(sum(numeric_values) / len(numeric_values), 2),
                        'sum': sum(numeric_values)
                    }

output_data['layer_name'] = layer.name
output_data['geometry_type'] = layer.geometry_type
output_data['srid'] = layer.srid
output_data['total_features'] = total_features
output_data['total_area_m2'] = round(total_area, 2)
output_data['total_area_ha'] = round(total_area / 10000, 2)
output_data['total_area_km2'] = round(total_area / 1000000, 4)
output_data['total_perimeter_m'] = round(total_perimeter, 2)
output_data['total_perimeter_km'] = round(total_perimeter / 1000, 2)
output_data['attribute_statistics'] = attribute_stats

logger.info(f"Análisis completado: {total_features} features, {total_area:.2f} m²")
''',
                'parameters_schema': {},
            },
            {
                'name': 'Validador de Calidad de Datos',
                'description': 'Detecta problemas de calidad en los datos: geometrías inválidas, nulas, atributos faltantes, y genera un score de calidad.',
                'category': 'Validación',
                'agent_type': 'custom',
                'code': '''import logging
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
features = layer.features.filter(is_active=True)

issues = []
valid_count = 0
invalid_geometries = 0
null_geometries = 0
empty_properties = 0

for feature in features:
    feature_issues = []
    
    # Validar geometría
    if feature.geometry is None:
        null_geometries += 1
        feature_issues.append("Geometría nula")
    elif not feature.geometry.valid:
        invalid_geometries += 1
        feature_issues.append(f"Geometría inválida: {feature.geometry.valid_reason}")
    
    # Validar propiedades
    if not feature.properties or len(feature.properties) == 0:
        empty_properties += 1
        feature_issues.append("Sin propiedades/atributos")
    
    if feature_issues:
        issues.append({
            'feature_id': feature.id,
            'issues': feature_issues
        })
    else:
        valid_count += 1

total = features.count()
quality_score = round((valid_count / total) * 100, 2) if total > 0 else 0

output_data['layer_name'] = layer.name
output_data['total_features'] = total
output_data['valid_features'] = valid_count
output_data['invalid_geometries'] = invalid_geometries
output_data['null_geometries'] = null_geometries
output_data['empty_properties'] = empty_properties
output_data['quality_score'] = quality_score
output_data['quality_level'] = 'Excelente' if quality_score >= 90 else 'Bueno' if quality_score >= 70 else 'Regular' if quality_score >= 50 else 'Malo'
output_data['issues'] = issues[:50]
output_data['total_issues'] = len(issues)

logger.info(f"Validación completada: {valid_count}/{total} válidos ({quality_score}%)")
''',
                'parameters_schema': {},
            },
            {
                'name': 'Análisis de Cobertura por Tipo',
                'description': 'Analiza la distribución de tipos/categorías en una capa, calculando área y porcentaje por cada tipo.',
                'category': 'Análisis',
                'agent_type': 'statistics',
                'code': '''import logging
from collections import defaultdict
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
features = layer.features.filter(is_active=True)

# Campo de clasificación (busca automáticamente)
class_field = parameters.get('class_field', '')

# Buscar campo automáticamente si no se especifica
if not class_field:
    sample = features.first()
    if sample and sample.properties:
        for key in ['tipo', 'type', 'clase', 'class', 'category', 'categoria', 'cobertura', 'uso']:
            if key in sample.properties:
                class_field = key
                break
        if not class_field:
            class_field = list(sample.properties.keys())[0] if sample.properties else 'tipo'

# Calcular cobertura por tipo
coverage_by_type = defaultdict(lambda: {'count': 0, 'area': 0})
total_area = 0

for feature in features:
    area = feature.geometry.area if feature.geometry else 0
    total_area += area
    
    tipo = 'Sin clasificar'
    if feature.properties:
        tipo = str(feature.properties.get(class_field, 'Sin clasificar'))
    
    coverage_by_type[tipo]['count'] += 1
    coverage_by_type[tipo]['area'] += area

# Ordenar por área
coverage_summary = []
for tipo, data in sorted(coverage_by_type.items(), key=lambda x: x[1]['area'], reverse=True):
    percentage = (data['area'] / total_area * 100) if total_area > 0 else 0
    coverage_summary.append({
        'type': tipo,
        'count': data['count'],
        'area_m2': round(data['area'], 2),
        'area_ha': round(data['area'] / 10000, 2),
        'percentage': round(percentage, 2)
    })

output_data['layer_name'] = layer.name
output_data['classification_field'] = class_field
output_data['total_features'] = features.count()
output_data['total_area_ha'] = round(total_area / 10000, 2)
output_data['unique_types'] = len(coverage_by_type)
output_data['coverage_by_type'] = coverage_summary
output_data['dominant_type'] = coverage_summary[0] if coverage_summary else None

logger.info(f"Cobertura analizada: {len(coverage_by_type)} tipos en {features.count()} features")
''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'class_field': {
                            'type': 'string',
                            'description': 'Campo de clasificación (opcional, se detecta automáticamente)'
                        }
                    }
                },
            },
            {
                'name': 'Generador de Buffer',
                'description': 'Crea zonas de influencia (buffer) alrededor de cada feature y calcula las áreas resultantes.',
                'category': 'Transformación',
                'agent_type': 'custom',
                'code': '''import logging
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
features = layer.features.filter(is_active=True)

# Distancia del buffer en metros
buffer_distance = float(parameters.get('buffer_distance', 100))

buffer_results = []
total_original_area = 0
total_buffer_area = 0

for feature in features:
    if feature.geometry:
        try:
            original_area = feature.geometry.area
            buffer_geom = feature.geometry.buffer(buffer_distance)
            buffer_area = buffer_geom.area
            
            total_original_area += original_area
            total_buffer_area += buffer_area
            
            buffer_results.append({
                'feature_id': feature.id,
                'original_area_m2': round(original_area, 2),
                'buffer_area_m2': round(buffer_area, 2),
                'area_increase_m2': round(buffer_area - original_area, 2),
                'area_increase_pct': round(((buffer_area - original_area) / original_area * 100) if original_area > 0 else 0, 2)
            })
        except Exception as e:
            logger.warning(f"Error en feature {feature.id}: {e}")

output_data['layer_name'] = layer.name
output_data['buffer_distance_m'] = buffer_distance
output_data['total_features'] = features.count()
output_data['processed_features'] = len(buffer_results)
output_data['total_original_area_ha'] = round(total_original_area / 10000, 2)
output_data['total_buffer_area_ha'] = round(total_buffer_area / 10000, 2)
output_data['total_area_increase_ha'] = round((total_buffer_area - total_original_area) / 10000, 2)
output_data['buffer_details'] = buffer_results[:30]

logger.info(f"Buffer de {buffer_distance}m aplicado a {len(buffer_results)} features")
''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'buffer_distance': {
                            'type': 'number',
                            'description': 'Distancia del buffer en metros',
                            'default': 100
                        }
                    }
                },
            },
            {
                'name': 'Comparador de Capas Temporales',
                'description': 'Compara dos capas de diferentes fechas para detectar cambios en área, cantidad de features y distribución.',
                'category': 'Detección',
                'agent_type': 'change_detection',
                'code': '''import logging
logger = logging.getLogger(__name__)

if len(input_layers) < 2:
    raise ValueError("Se requieren exactamente 2 capas para comparar (antes y después)")

layer_before = input_layers[0]
layer_after = input_layers[1]

features_before = layer_before.features.filter(is_active=True)
features_after = layer_after.features.filter(is_active=True)

def calculate_metrics(features):
    total_area = 0
    count = features.count()
    for f in features:
        if f.geometry:
            total_area += f.geometry.area
    return {'count': count, 'total_area': total_area}

metrics_before = calculate_metrics(features_before)
metrics_after = calculate_metrics(features_after)

# Calcular cambios
count_diff = metrics_after['count'] - metrics_before['count']
area_diff = metrics_after['total_area'] - metrics_before['total_area']

count_change_pct = ((count_diff / metrics_before['count']) * 100) if metrics_before['count'] > 0 else 0
area_change_pct = ((area_diff / metrics_before['total_area']) * 100) if metrics_before['total_area'] > 0 else 0

# Determinar tendencia
if area_change_pct > 5:
    trend = 'AUMENTO'
    trend_icon = '📈'
elif area_change_pct < -5:
    trend = 'DISMINUCIÓN'
    trend_icon = '📉'
else:
    trend = 'ESTABLE'
    trend_icon = '➡️'

output_data['layer_before'] = {
    'name': layer_before.name,
    'feature_count': metrics_before['count'],
    'total_area_ha': round(metrics_before['total_area'] / 10000, 2)
}
output_data['layer_after'] = {
    'name': layer_after.name,
    'feature_count': metrics_after['count'],
    'total_area_ha': round(metrics_after['total_area'] / 10000, 2)
}
output_data['changes'] = {
    'feature_count_diff': count_diff,
    'feature_count_change_pct': round(count_change_pct, 2),
    'area_diff_ha': round(area_diff / 10000, 2),
    'area_change_pct': round(area_change_pct, 2),
    'trend': trend,
    'trend_icon': trend_icon
}
output_data['summary'] = f"{trend_icon} {trend}: {abs(round(area_change_pct, 1))}% {'aumento' if area_diff > 0 else 'disminución'} en área"

logger.info(f"Comparación: {trend} de {abs(area_change_pct):.1f}% en área")
''',
                'parameters_schema': {},
            },
            {
                'name': 'Generador de Reporte Completo',
                'description': 'Genera un reporte detallado de la capa con toda la información disponible: metadata, estadísticas, calidad y atributos.',
                'category': 'Exportación',
                'agent_type': 'custom',
                'code': '''import logging
from datetime import datetime
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
features = layer.features.filter(is_active=True)

# Generar reporte completo
report = {
    'report_metadata': {
        'generated_at': datetime.now().isoformat(),
        'generator': 'SMGI Agent - Generador de Reportes',
        'version': '1.0'
    },
    'layer_info': {
        'id': layer.id,
        'name': layer.name,
        'geometry_type': layer.geometry_type,
        'srid': layer.srid,
        'created_at': layer.created_at.isoformat() if layer.created_at else None,
        'updated_at': layer.updated_at.isoformat() if layer.updated_at else None,
    },
    'statistics': {
        'total_features': 0,
        'total_area_m2': 0,
        'total_area_ha': 0,
        'total_perimeter_m': 0,
        'avg_area_m2': 0,
        'min_area_m2': None,
        'max_area_m2': None,
    },
    'attributes': {
        'field_count': 0,
        'fields': [],
        'sample_record': {}
    },
    'quality': {
        'valid_geometries': 0,
        'invalid_geometries': 0,
        'null_geometries': 0,
        'quality_score': 0
    }
}

# Calcular estadísticas
areas = []
total_perimeter = 0
valid_geoms = 0
null_geoms = 0
invalid_geoms = 0

for feature in features:
    if feature.geometry is None:
        null_geoms += 1
    elif not feature.geometry.valid:
        invalid_geoms += 1
    else:
        valid_geoms += 1
        areas.append(feature.geometry.area)
        total_perimeter += feature.geometry.length if hasattr(feature.geometry, 'length') else 0
    
    # Campos
    if feature.properties and not report['attributes']['fields']:
        report['attributes']['fields'] = list(feature.properties.keys())
        report['attributes']['sample_record'] = feature.properties
        report['attributes']['field_count'] = len(feature.properties)

total_features = features.count()
total_area = sum(areas) if areas else 0

report['statistics']['total_features'] = total_features
report['statistics']['total_area_m2'] = round(total_area, 2)
report['statistics']['total_area_ha'] = round(total_area / 10000, 2)
report['statistics']['total_perimeter_m'] = round(total_perimeter, 2)
report['statistics']['avg_area_m2'] = round(total_area / len(areas), 2) if areas else 0
report['statistics']['min_area_m2'] = round(min(areas), 2) if areas else None
report['statistics']['max_area_m2'] = round(max(areas), 2) if areas else None

report['quality']['valid_geometries'] = valid_geoms
report['quality']['invalid_geometries'] = invalid_geoms
report['quality']['null_geometries'] = null_geoms
report['quality']['quality_score'] = round((valid_geoms / total_features) * 100, 1) if total_features > 0 else 0

output_data.update(report)

logger.info(f"Reporte generado para '{layer.name}': {total_features} features")
''',
                'parameters_schema': {},
            },
            {
                'name': 'Calculador de Centroides',
                'description': 'Calcula el centroide de cada feature y el centroide general de toda la capa.',
                'category': 'Transformación',
                'agent_type': 'custom',
                'code': '''import logging
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
features = layer.features.filter(is_active=True)

centroids = []
all_x = []
all_y = []

for feature in features:
    if feature.geometry:
        try:
            centroid = feature.geometry.centroid
            centroids.append({
                'feature_id': feature.id,
                'x': round(centroid.x, 6),
                'y': round(centroid.y, 6),
                'lon': round(centroid.x, 6),
                'lat': round(centroid.y, 6)
            })
            all_x.append(centroid.x)
            all_y.append(centroid.y)
        except Exception as e:
            logger.warning(f"Error en feature {feature.id}: {e}")

# Centroide general
general_centroid = None
if all_x and all_y:
    general_centroid = {
        'x': round(sum(all_x) / len(all_x), 6),
        'y': round(sum(all_y) / len(all_y), 6),
        'lon': round(sum(all_x) / len(all_x), 6),
        'lat': round(sum(all_y) / len(all_y), 6)
    }

# Bounding box
bbox = None
if all_x and all_y:
    bbox = {
        'min_x': round(min(all_x), 6),
        'min_y': round(min(all_y), 6),
        'max_x': round(max(all_x), 6),
        'max_y': round(max(all_y), 6)
    }

output_data['layer_name'] = layer.name
output_data['total_features'] = features.count()
output_data['centroids_calculated'] = len(centroids)
output_data['general_centroid'] = general_centroid
output_data['bounding_box'] = bbox
output_data['feature_centroids'] = centroids[:50]

logger.info(f"Centroides calculados: {len(centroids)} features")
''',
                'parameters_schema': {},
            },
            {
                'name': 'Filtro por Atributos',
                'description': 'Filtra features según condiciones en sus atributos. Soporta: igual, diferente, contiene, mayor que, menor que.',
                'category': 'Análisis',
                'agent_type': 'classification',
                'code': '''import logging
logger = logging.getLogger(__name__)

if not input_layers:
    raise ValueError("Se requiere al menos una capa de entrada")

layer = input_layers[0]
features = layer.features.filter(is_active=True)

# Parámetros
field_name = parameters.get('field_name', '')
operator = parameters.get('operator', 'equals')
filter_value = parameters.get('value', '')

if not field_name:
    # Mostrar campos disponibles
    sample = features.first()
    available_fields = list(sample.properties.keys()) if sample and sample.properties else []
    raise ValueError(f"Especifica 'field_name'. Campos disponibles: {available_fields}")

matching = []
non_matching = []

for feature in features:
    if not feature.properties:
        non_matching.append(feature.id)
        continue
    
    field_value = feature.properties.get(field_name)
    if field_value is None:
        non_matching.append(feature.id)
        continue
    
    matches = False
    
    if operator == 'equals':
        matches = str(field_value).lower() == str(filter_value).lower()
    elif operator == 'not_equals':
        matches = str(field_value).lower() != str(filter_value).lower()
    elif operator == 'contains':
        matches = str(filter_value).lower() in str(field_value).lower()
    elif operator == 'greater':
        try:
            matches = float(field_value) > float(filter_value)
        except (ValueError, TypeError):
            pass
    elif operator == 'less':
        try:
            matches = float(field_value) < float(filter_value)
        except (ValueError, TypeError):
            pass
    elif operator == 'starts_with':
        matches = str(field_value).lower().startswith(str(filter_value).lower())
    elif operator == 'ends_with':
        matches = str(field_value).lower().endswith(str(filter_value).lower())
    
    if matches:
        matching.append({
            'feature_id': feature.id,
            field_name: field_value
        })
    else:
        non_matching.append(feature.id)

total = features.count()
match_pct = round((len(matching) / total) * 100, 2) if total > 0 else 0

output_data['layer_name'] = layer.name
output_data['filter'] = {
    'field': field_name,
    'operator': operator,
    'value': filter_value
}
output_data['total_features'] = total
output_data['matching_count'] = len(matching)
output_data['non_matching_count'] = len(non_matching)
output_data['match_percentage'] = match_pct
output_data['matching_features'] = matching[:100]

logger.info(f"Filtro: {len(matching)}/{total} features coinciden ({match_pct}%)")
''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'field_name': {
                            'type': 'string',
                            'description': 'Nombre del campo a filtrar'
                        },
                        'operator': {
                            'type': 'string',
                            'enum': ['equals', 'not_equals', 'contains', 'greater', 'less', 'starts_with', 'ends_with'],
                            'description': 'Operador de comparación'
                        },
                        'value': {
                            'type': 'string',
                            'description': 'Valor a buscar'
                        }
                    },
                    'required': ['field_name', 'value']
                },
            },
        ]

        # Crear agentes
        created_count = 0
        for agent_data in agents_data:
            category = categories.get(agent_data['category'])
            
            agent, created = Agent.objects.update_or_create(
                name=agent_data['name'],
                defaults={
                    'description': agent_data['description'],
                    'category': category,
                    'agent_type': agent_data['agent_type'],
                    'code': agent_data['code'],
                    'parameters_schema': agent_data.get('parameters_schema', {}),
                    'status': 'published',
                    'is_public': True,
                    'created_by': admin_user,
                    'updated_by': admin_user
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✅ Creado: {agent.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  🔄 Actualizado: {agent.name}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✨ Proceso completado: {created_count} agentes creados'))
        self.stdout.write(self.style.SUCCESS(f'   Total de agentes: {len(agents_data)}'))
        self.stdout.write('')

    def create_category(self, name, description, icon, color):
        category, created = AgentCategory.objects.get_or_create(
            name=name,
            defaults={
                'description': description,
                'icon': icon,
                'color': color,
            }
        )
        if created:
            self.stdout.write(f'  📁 Categoría creada: {name}')
        return category