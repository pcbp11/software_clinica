# Generated migration for changing EstructuraComision structure
# Changes: unidad_negocio -> categoria_servicio, tipo_comision -> tipo_tributo, add vigencia_indefinida

import django.db.models.deletion
from django.db import migrations, models


def migrate_data(apps, schema_editor):
    """Migrates data from unidad_negocio to categoria_servicio"""
    EstructuraComision = apps.get_model('core', 'EstructuraComision')
    CategoriaServicio = apps.get_model('core', 'CategoriaServicio')

    for estructura in EstructuraComision.objects.all():
        # Find the first active categoria from the same unidad_negocio
        try:
            categoria = CategoriaServicio.objects.filter(
                unidad_negocio=estructura.unidad_negocio,
                activa=True
            ).first()
            if categoria:
                estructura.categoria_servicio = categoria
                estructura.save()
        except:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_alter_insumo_options_and_more'),
    ]

    operations = [
        # Step 1: Add categoria_servicio field (nullable)
        migrations.AddField(
            model_name='estructuracomision',
            name='categoria_servicio',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, to='core.categoriaservicio', related_name='estructuras_comision'),
        ),

        # Step 2: Add vigencia_indefinida field
        migrations.AddField(
            model_name='estructuracomision',
            name='vigencia_indefinida',
            field=models.BooleanField(default=False, help_text='Si está activado, la estructura no tiene fecha de fin'),
        ),

        # Step 3: Migrate data from unidad_negocio to categoria_servicio
        migrations.RunPython(migrate_data),

        # Step 4: Update unique_together constraint BEFORE removing unidad_negocio
        migrations.AlterUniqueTogether(
            name='estructuracomision',
            unique_together=set(),  # Clear existing constraint first
        ),

        # Step 5: Remove unidad_negocio field
        migrations.RemoveField(
            model_name='estructuracomision',
            name='unidad_negocio',
        ),

        # Step 6: Make categoria_servicio NOT nullable
        migrations.AlterField(
            model_name='estructuracomision',
            name='categoria_servicio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.categoriaservicio', related_name='estructuras_comision'),
        ),

        # Step 7: Rename tipo_comision to tipo_tributo with new choices
        migrations.RenameField(
            model_name='estructuracomision',
            old_name='tipo_comision',
            new_name='tipo_tributo',
        ),

        # Step 8: Alter tipo_tributo field with new choices
        migrations.AlterField(
            model_name='estructuracomision',
            name='tipo_tributo',
            field=models.CharField(
                max_length=10,
                choices=[('afecta', 'Afecta a IVA'), ('exenta', 'Exenta')],
                default='exenta'
            ),
        ),

        # Step 9: Update help text for valor_comision
        migrations.AlterField(
            model_name='estructuracomision',
            name='valor_comision',
            field=models.PositiveIntegerField(help_text='Porcentaje de comisión (ingresar 30 para 30%)'),
        ),

        # Step 10: Set new unique_together constraint
        migrations.AlterUniqueTogether(
            name='estructuracomision',
            unique_together={('profesional', 'categoria_servicio', 'fecha_inicio')},
        ),
    ]
