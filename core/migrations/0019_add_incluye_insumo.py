# Migration: Add incluye_insumo field to EstructuraComision

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_add_unidad_negocio_back'),
    ]

    operations = [
        migrations.AddField(
            model_name='estructuracomision',
            name='incluye_insumo',
            field=models.BooleanField(default=False, help_text='Si está activado, el cálculo de comisión descuenta el costo de insumos'),
        ),
    ]
