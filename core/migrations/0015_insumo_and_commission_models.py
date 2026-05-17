# Generated migration for Insumo and Commission tracking models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_descuento'),
    ]

    operations = [
        # Insumo model - tracks costs of products/materials
        migrations.CreateModel(
            name='Insumo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200)),
                ('codigo_sku', models.CharField(blank=True, max_length=50)),
                ('descripcion', models.TextField(blank=True)),
                ('costo_unitario', models.PositiveIntegerField(help_text='Costo en pesos chilenos')),
                ('precio_venta', models.PositiveIntegerField(help_text='Precio de venta en pesos chilenos', blank=True, null=True)),
                ('unidad', models.CharField(choices=[('unidad', 'Unidad'), ('ml', 'ml'), ('gr', 'gr'), ('caja', 'Caja')], default='unidad', max_length=20)),
                ('cantidad_disponible', models.PositiveIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
                ('unidad_negocio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='insumos', to='core.unidadnegocio')),
            ],
            options={
                'verbose_name': 'Insumo',
                'verbose_name_plural': 'Insumos',
            },
        ),

        # Relationship between Service and Insumo (many-to-many)
        migrations.CreateModel(
            name='ServicioInsumo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad_usada', models.PositiveIntegerField(help_text='Cantidad de insumo usado por servicio')),
                ('insumo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='servicios', to='core.insumo')),
                ('servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='insumos_usados', to='core.servicio')),
            ],
            options={
                'verbose_name': 'Servicio-Insumo',
                'verbose_name_plural': 'Servicios-Insumos',
                'unique_together': {('servicio', 'insumo')},
            },
        ),

        # Commission structure per professional
        migrations.CreateModel(
            name='EstructuraComision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_comision', models.CharField(
                    choices=[
                        ('porcentaje', 'Porcentaje (%)'),
                        ('fijo_por_servicio', 'Fijo por servicio'),
                        ('sociedad_carro', 'Sociedad Mía Carro (%)'),
                        ('clinica_salud_70_30', 'Clínica Mía Salud (70/30)'),
                    ],
                    default='porcentaje',
                    max_length=30
                )),
                ('valor_comision', models.PositiveIntegerField(help_text='Para %, ingresar 30 para 30%. Para fijo, ingresar el monto.')),
                ('activa', models.BooleanField(default=True)),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('notas', models.TextField(blank=True)),
                ('profesional', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='estructuras_comision', to='core.profesional')),
                ('unidad_negocio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='estructuras_comision', to='core.unidadnegocio')),
            ],
            options={
                'verbose_name': 'Estructura de comisión',
                'verbose_name_plural': 'Estructuras de comisión',
            },
        ),

        # Commission calculation record
        migrations.CreateModel(
            name='ComisionCalculada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_calculo', models.DateTimeField(auto_now_add=True)),
                ('monto_ingresos_brutos', models.PositiveIntegerField(help_text='Ingresos totales del servicio')),
                ('monto_insumos', models.PositiveIntegerField(help_text='Costo total de insumos utilizados')),
                ('monto_descuentos', models.PositiveIntegerField(default=0, help_text='Descuentos aplicados')),
                ('monto_neto', models.PositiveIntegerField(help_text='Ingresos brutos - insumos - descuentos')),
                ('monto_comision', models.PositiveIntegerField(help_text='Comisión calculada')),
                ('porcentaje_comision', models.PositiveIntegerField(help_text='Porcentaje aplicado')),
                ('mes_referencia', models.CharField(max_length=7, help_text='Formato YYYY-MM')),
                ('cita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comisiones', to='core.cita')),
                ('estructura_comision', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.estructuracomision')),
                ('profesional', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comisiones_calculadas', to='core.profesional')),
            ],
            options={
                'verbose_name': 'Comisión calculada',
                'verbose_name_plural': 'Comisiones calculadas',
                'ordering': ['-fecha_calculo'],
                'indexes': [
                    models.Index(fields=['profesional', 'mes_referencia'], name='core_comisi_profesi_mes_idx'),
                    models.Index(fields=['mes_referencia'], name='core_comisi_mes_idx'),
                ],
            },
        ),
    ]
