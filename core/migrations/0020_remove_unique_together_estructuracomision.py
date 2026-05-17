# Migration: Remove unique_together constraint from EstructuraComision

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_add_incluye_insumo'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='estructuracomision',
            unique_together=set(),
        ),
    ]
