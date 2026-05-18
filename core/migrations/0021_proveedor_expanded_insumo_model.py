# Generated migration for expanded Insumo model with Proveedor

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_remove_unique_together_estructuracomision'),
    ]

    operations = [
        # Create Proveedor model
        migrations.CreateModel(
            name='Proveedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200)),
                ('razon_social', models.CharField(blank=True, max_length=200)),
                ('rut', models.CharField(blank=True, max_length=12)),
                ('telefono', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('contacto', models.CharField(blank=True, max_length=100)),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proveedores', to='core.empresa')),
            ],
            options={
                'verbose_name': 'Proveedor',
                'verbose_name_plural': 'Proveedores',
                'ordering': ['nombre'],
            },
        ),

        # Add fields to Insumo model
        migrations.AddField(
            model_name='insumo',
            name='costo_con_iva',
            field=models.PositiveIntegerField(default=0, help_text='Costo con IVA incluido en pesos chilenos'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='insumo',
            name='costo_neto',
            field=models.PositiveIntegerField(default=0, help_text='Costo neto en pesos chilenos'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='insumo',
            name='estado',
            field=models.CharField(choices=[('vigente', 'Vigente'), ('terminado', 'Terminado')], default='vigente', max_length=20),
        ),
        migrations.AddField(
            model_name='insumo',
            name='estado_transferencia',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('realizada', 'Realizada')], default='pendiente', max_length=20),
        ),
        migrations.AddField(
            model_name='insumo',
            name='fecha_compra',
            field=models.DateField(default='2026-05-17', help_text='Fecha de compra del insumo'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='insumo',
            name='fecha_transferencia',
            field=models.DateField(blank=True, help_text='Fecha de transferencia bancaria', null=True),
        ),
        migrations.AddField(
            model_name='insumo',
            name='fecha_vencimiento',
            field=models.DateField(blank=True, help_text='Fecha de vencimiento del producto', null=True),
        ),
        migrations.AddField(
            model_name='insumo',
            name='fecha_venta',
            field=models.DateField(blank=True, help_text='Fecha en que se vendió el insumo (automática)', null=True),
        ),
        migrations.AddField(
            model_name='insumo',
            name='notas',
            field=models.TextField(blank=True, help_text='Notas adicionales sobre el insumo'),
        ),
        migrations.AddField(
            model_name='insumo',
            name='precio_venta_con_iva',
            field=models.PositiveIntegerField(blank=True, help_text='Precio venta con IVA a profesionales', null=True),
        ),
        migrations.AddField(
            model_name='insumo',
            name='precio_venta_neto',
            field=models.PositiveIntegerField(blank=True, help_text='Precio venta neto a profesionales', null=True),
        ),
        migrations.AddField(
            model_name='insumo',
            name='tiempo_maximo_proyectado',
            field=models.PositiveIntegerField(blank=True, help_text='Tiempo máximo antes de considerarlo crítico', null=True),
        ),
        migrations.AddField(
            model_name='insumo',
            name='unidad_tiempo',
            field=models.CharField(choices=[('dias', 'Días'), ('meses', 'Meses')], default='meses', max_length=10),
        ),
        migrations.AddField(
            model_name='insumo',
            name='actualizado_en',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='insumo',
            name='paciente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='insumos_vendidos', to='core.paciente'),
        ),
        migrations.AddField(
            model_name='insumo',
            name='proveedor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='insumos', to='core.proveedor'),
        ),

        # Alter existing fields
        migrations.AlterField(
            model_name='insumo',
            name='codigo_sku',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterModelOptions(
            name='insumo',
            options={'ordering': ['-fecha_creacion', 'nombre'], 'verbose_name': 'Insumo', 'verbose_name_plural': 'Insumos'},
        ),
        migrations.AddIndex(
            model_name='insumo',
            index=models.Index(fields=['unidad_negocio', '-fecha_creacion'], name='core_insumo_unidad_negocio_fecha_creacion_idx'),
        ),
        migrations.AddIndex(
            model_name='insumo',
            index=models.Index(fields=['estado', 'fecha_vencimiento'], name='core_insumo_estado_fecha_vencimiento_idx'),
        ),

        # Remove old field
        migrations.RemoveField(
            model_name='insumo',
            name='costo_unitario',
        ),
        migrations.RemoveField(
            model_name='insumo',
            name='precio_venta',
        ),
    ]
