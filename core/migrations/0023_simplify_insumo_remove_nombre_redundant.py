# Migración para simplificar modelo Insumo: eliminar campo nombre redundante

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_productoproveedor_and_insumo_linking'),
    ]

    operations = [
        # Remover campos redundantes
        migrations.RemoveField(
            model_name='insumo',
            name='nombre',
        ),

        # Remover campo proveedor (se obtiene desde producto_proveedor)
        migrations.RemoveField(
            model_name='insumo',
            name='proveedor',
        ),

        # Actualizar producto_proveedor para que sea requerido (on_delete=CASCADE)
        migrations.AlterField(
            model_name='insumo',
            name='producto_proveedor',
            field=models.ForeignKey(
                help_text='Selecciona el producto del proveedor',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='insumos',
                to='core.productoproveedor'
            ),
        ),

        # Hacer codigo_sku único
        migrations.AlterField(
            model_name='insumo',
            name='codigo_sku',
            field=models.CharField(
                blank=True,
                help_text='Se genera automáticamente en formato BOTENE_001',
                max_length=50,
                unique=True
            ),
        ),

        # Actualizar descripcion
        migrations.AlterField(
            model_name='insumo',
            name='descripcion',
            field=models.TextField(
                blank=True,
                help_text='Notas específicas de este lote de insumo'
            ),
        ),
    ]
