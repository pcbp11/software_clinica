# Add unidad_negocio back to EstructuraComision
# Now structure is: profesional + unidad_negocio + categoria_servicio

import django.db.models.deletion
from django.db import migrations, models


def add_unidad_negocio(apps, schema_editor):
    """Populate unidad_negocio from categoria_servicio"""
    EstructuraComision = apps.get_model('core', 'EstructuraComision')

    for estructura in EstructuraComision.objects.all():
        if estructura.categoria_servicio and not estructura.unidad_negocio_id:
            estructura.unidad_negocio = estructura.categoria_servicio.unidad_negocio
            estructura.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_restructure_comisiones'),
    ]

    operations = [
        # Step 1: Add unidad_negocio back (nullable)
        migrations.AddField(
            model_name='estructuracomision',
            name='unidad_negocio',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, to='core.unidadnegocio', related_name='estructuras_comision'),
        ),

        # Step 2: Populate unidad_negocio from categoria_servicio
        migrations.RunPython(add_unidad_negocio),

        # Step 3: Make unidad_negocio non-nullable
        migrations.AlterField(
            model_name='estructuracomision',
            name='unidad_negocio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.unidadnegocio', related_name='estructuras_comision'),
        ),

        # Step 4: Update unique_together to include both unidad_negocio and categoria_servicio
        migrations.AlterUniqueTogether(
            name='estructuracomision',
            unique_together={('profesional', 'unidad_negocio', 'categoria_servicio', 'fecha_inicio')},
        ),
    ]
