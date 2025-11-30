# Generated migration to add validators to Agent model

from django.db import migrations, models
import apps.agents.validators


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agent',
            name='code',
            field=models.TextField(
                help_text='Código Python del agente',
                validators=[apps.agents.validators.validate_agent_code],
                verbose_name='código'
            ),
        ),
        migrations.AlterField(
            model_name='agent',
            name='requirements',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Lista de paquetes Python requeridos',
                validators=[apps.agents.validators.validate_agent_requirements],
                verbose_name='dependencias'
            ),
        ),
        migrations.AlterField(
            model_name='agent',
            name='parameters_schema',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='JSON Schema para validar parámetros de entrada',
                validators=[apps.agents.validators.validate_json_schema],
                verbose_name='esquema de parámetros'
            ),
        ),
        migrations.AlterField(
            model_name='agentrating',
            name='rating',
            field=models.IntegerField(
                choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)],
                help_text='Calificación de 1 a 5 estrellas',
                validators=[
                    models.validators.MinValueValidator(1),
                    models.validators.MaxValueValidator(5)
                ],
                verbose_name='calificación'
            ),
        ),
        migrations.AlterField(
            model_name='agentschedule',
            name='cron_expression',
            field=models.CharField(
                blank=True,
                help_text='Para tipo cron (ej: 0 0 * * *)',
                max_length=100,
                validators=[apps.agents.validators.validate_cron_expression],
                verbose_name='expresión cron'
            ),
        ),
    ]
