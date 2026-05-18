# Generated migration for ProductoProveedor model and Insumo linking

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_proveedor_expanded_insumo_model'),
    ]

    operations = [
        # Create ProductoProveedor model
        migrations.CreateModel(
            name='ProductoProveedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(help_text='Nombre del producto que ofrece este proveedor', max_length=200)),
                ('descripcion', models.TextField(blank=True)),
                ('unidad', models.CharField(
                    choices=[
                        ('unidad', 'Unidad'),
                        ('ml', 'ml'),
                        ('gr', 'gr'),
                        ('caja', 'Caja'),
                        ('botella', 'Botella'),
                        ('jeringa', 'Jeringa'),
                        ('ampolla', 'Ampolla'),
                    ],
                    default='unidad',
                    help_text='Unidad de medida por defecto para este producto',
                    max_length=20
                )),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('proveedor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='productos', to='core.proveedor')),
            ],
            options={
                'verbose_name': 'Producto Proveedor',
                'verbose_name_plural': 'Productos Proveedor',
                'ordering': ['proveedor__nombre', 'nombre'],
                'unique_together': {('proveedor', 'nombre')},
            },
        ),

        # Add campo producto_proveedor to Insumo
        migrations.AddField(
            model_name='insumo',
            name='producto_proveedor',
            field=models.ForeignKey(
                blank=True,
                help_text='Producto del proveedor (se autocompleta)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='insumos',
                to='core.productoproveedor'
            ),
        ),

        # Alter nombre field in Insumo
        migrations.AlterField(
            model_name='insumo',
            name='nombre',
            field=models.CharField(
                help_text='Se autocompleta desde el producto seleccionado del proveedor',
                max_length=200
            ),
        ),

        # Add index to ProductoProveedor
        migrations.AddIndex(
            model_name='productoproveedor',
            index=models.Index(fields=['proveedor', 'activo'], name='core_productoproveedor_proveedor_activo_idx'),
        ),
    ]
