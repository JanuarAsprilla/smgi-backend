# Generated migration for SMGI geodata app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('geodata', '0001_initial'),
    ]

    operations = [
        # 1. Make data_source optional
        migrations.AlterField(
            model_name='layer',
            name='data_source',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='layers',
                to='geodata.datasource',
                verbose_name='fuente de datos'
            ),
        ),
        
        # 2. Add feature_count field
        migrations.AddField(
            model_name='layer',
            name='feature_count',
            field=models.IntegerField(default=0, verbose_name='número de features'),
        ),
        
        # 3. Add original_filename field
        migrations.AddField(
            model_name='layer',
            name='original_filename',
            field=models.CharField(blank=True, max_length=500, verbose_name='nombre de archivo original'),
        ),
        
        # 4. Add file_size field
        migrations.AddField(
            model_name='layer',
            name='file_size',
            field=models.BigIntegerField(blank=True, null=True, verbose_name='tamaño del archivo (bytes)'),
        ),
        
        # 5. Update layer_type default
        migrations.AlterField(
            model_name='layer',
            name='layer_type',
            field=models.CharField(
                choices=[
                    ('vector', 'Vectorial'),
                    ('raster', 'Raster'),
                    ('point_cloud', 'Nube de Puntos'),
                    ('tile', 'Tiles')
                ],
                default='vector',
                max_length=20,
                verbose_name='tipo de capa'
            ),
        ),
        
        # 6. Update geometry_type choices
        migrations.AlterField(
            model_name='layer',
            name='geometry_type',
            field=models.CharField(
                choices=[
                    ('POINT', 'Punto'),
                    ('LINESTRING', 'Línea'),
                    ('POLYGON', 'Polígono'),
                    ('MULTIPOINT', 'Multipunto'),
                    ('MULTILINESTRING', 'Multilínea'),
                    ('MULTIPOLYGON', 'Multipolígono'),
                    ('GEOMETRYCOLLECTION', 'Colección'),
                    ('GEOMETRY', 'Geometría Mixta'),
                    ('RASTER', 'Raster')
                ],
                default='GEOMETRY',
                max_length=30,
                verbose_name='tipo de geometría'
            ),
        ),
        
        # 7. Remove unique_together constraint
        migrations.AlterUniqueTogether(
            name='layer',
            unique_together=set(),
        ),
        
        # 8. Update ordering
        migrations.AlterModelOptions(
            name='layer',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'capa',
                'verbose_name_plural': 'capas'
            },
        ),
        
        # 9. Update SyncLog data_source to allow null
        migrations.AlterField(
            model_name='synclog',
            name='data_source',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sync_logs',
                to='geodata.datasource',
                verbose_name='fuente de datos'
            ),
        ),
        
        # 10. Add layer field to SyncLog
        migrations.AddField(
            model_name='synclog',
            name='layer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sync_logs',
                to='geodata.layer',
                verbose_name='capa'
            ),
        ),
        
        # 11. Update SyncLog status choices
        migrations.AlterField(
            model_name='synclog',
            name='status',
            field=models.CharField(
                choices=[
                    ('success', 'Exitoso'),
                    ('failed', 'Fallido'),
                    ('partial', 'Parcial'),
                    ('processing', 'Procesando')
                ],
                default='processing',
                max_length=20,
                verbose_name='estado'
            ),
        ),
        
        # 12. Update DataSource source_type choices
        migrations.AlterField(
            model_name='datasource',
            name='source_type',
            field=models.CharField(
                choices=[
                    ('wms', 'Web Map Service'),
                    ('wfs', 'Web Feature Service'),
                    ('wmts', 'Web Map Tile Service'),
                    ('api', 'REST API'),
                    ('database', 'Base de Datos'),
                    ('file', 'Archivo'),
                    ('sentinel', 'Sentinel Hub'),
                    ('landsat', 'Landsat'),
                    ('arcgis', 'ArcGIS Online'),
                    ('custom', 'Personalizado')
                ],
                default='file',
                max_length=20,
                verbose_name='tipo de fuente'
            ),
        ),
    ]