# Migración para expandir los estados disponibles en Insumo
# Añade: vencido, vendido, cancelado

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_simplify_insumo_remove_nombre_redundant'),
    ]

    operations = [
        # Actualizar el campo estado con opciones expandidas
        migrations.AlterField(
            model_name='insumo',
            name='estado',
            field=models.CharField(
                choices=[
                    ('vigente', 'Vigente'),
                    ('vencido', 'Vencido'),
                    ('vendido', 'Vendido'),
                    ('cancelado', 'Cancelado'),
                ],
                default='vigente',
                help_text='Estado del insumo: vigente, vencido, vendido o cancelado',
                max_length=20
            ),
        ),
    ]
