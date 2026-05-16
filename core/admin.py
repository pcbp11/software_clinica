from django import forms
from django.contrib import admin

from .models import (
    Empresa,
    UnidadNegocio,
    Sucursal,
    Paciente,
    Profesional,
    HorarioProfesional,
    CategoriaServicio,
    Servicio,
    Cita,
    Pago,
    SeguimientoPaciente,
)
from .utils import obtener_horas_disponibles


class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        profesional_id = None
        servicio_id = None
        fecha_valor = None

        if self.data:
            profesional_id = self.data.get('profesional')
            servicio_id = self.data.get('servicio')
            fecha_valor = self.data.get('fecha')
        elif self.instance and self.instance.pk:
            profesional_id = self.instance.profesional_id
            servicio_id = self.instance.servicio_id
            fecha_valor = self.instance.fecha

        if profesional_id and servicio_id and fecha_valor:
            try:
                import datetime

                profesional = Profesional.objects.get(id=profesional_id)
                servicio = Servicio.objects.get(id=servicio_id)

                if isinstance(fecha_valor, str):
                    fecha_obj = datetime.datetime.strptime(fecha_valor, "%Y-%m-%d").date()
                else:
                    fecha_obj = fecha_valor

                horas = obtener_horas_disponibles(
                    profesional,
                    fecha_obj,
                    servicio.duracion_minutos
                )

                self.fields['hora_inicio'] = forms.ChoiceField(
                    choices=[(h.strftime("%H:%M:%S"), h.strftime("%H:%M")) for h in horas],
                    label="Hora inicio",
                    required=True,
                )

            except Exception:
                pass


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'email', 'telefono', 'activa')
    search_fields = ('nombre', 'rut')


@admin.register(UnidadNegocio)
class UnidadNegocioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'razon_social', 'rut', 'tipo_impuesto', 'activa')
    search_fields = ('nombre', 'empresa__nombre', 'razon_social', 'rut')
    list_filter = ('empresa', 'tipo_impuesto', 'activa')


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'ciudad', 'comuna', 'activa')
    search_fields = ('nombre', 'empresa__nombre')


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'rut', 'telefono', 'tipo_cliente', 'activo')
    search_fields = ('nombres', 'apellidos', 'rut', 'telefono')
    readonly_fields = ('edad_mostrada',)

    fieldsets = (
        ('Datos personales', {
            'fields': ('rut', 'nombres', 'apellidos', 'fecha_nacimiento', 'edad_mostrada', 'genero')
        }),
        ('Contacto', {
            'fields': ('telefono', 'email')
        }),
        ('Información clínica', {
            'fields': ('sucursal', 'tipo_cliente', 'origen', 'activo')
        }),
        ('Otros', {
            'fields': ('observaciones',)
        }),
    )

    def edad_mostrada(self, obj):
        if obj and obj.edad is not None:
            return f"{obj.edad} años"
        return "-"

    edad_mostrada.short_description = "Edad"


class HorarioProfesionalInline(admin.TabularInline):
    model = HorarioProfesional
    extra = 0
    fields = (
        'dia_semana',
        'activo',
        'hora_inicio',
        'hora_fin',
        'tiene_descanso',
        'inicio_descanso',
        'fin_descanso',
    )


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = (
        'nombres',
        'apellidos',
        'rut',
        'empresa',
        'sucursal_principal',
        'acepta_reservas_online',
        'activo',
    )
    search_fields = ('nombres', 'apellidos', 'rut', 'nombre_publico')
    inlines = [HorarioProfesionalInline]


@admin.register(HorarioProfesional)
class HorarioProfesionalAdmin(admin.ModelAdmin):
    list_display = (
        'profesional',
        'dia_semana',
        'activo',
        'hora_inicio',
        'hora_fin',
        'tiene_descanso',
        'inicio_descanso',
        'fin_descanso',
    )
    list_filter = ('profesional', 'dia_semana', 'activo')
    search_fields = ('profesional__nombres', 'profesional__apellidos')


@admin.register(CategoriaServicio)
class CategoriaServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'unidad_negocio', 'activa')
    search_fields = ('nombre', 'unidad_negocio__nombre')
    list_filter = ('unidad_negocio', 'activa')


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'empresa',
        'unidad_negocio',
        'categoria',
        'duracion_minutos',
        'precio',
        'requiere_seguimiento',
        'dias_seguimiento',
        'activo',
    )
    search_fields = ('nombre', 'empresa__nombre', 'unidad_negocio__nombre')
    list_filter = ('empresa', 'unidad_negocio', 'categoria', 'requiere_seguimiento', 'activo')
    filter_horizontal = ('profesionales',)

    fieldsets = (
        ('Información básica', {
            'fields': (
                'empresa',
                'unidad_negocio',
                'categoria',
                'nombre',
                'descripcion',
            )
        }),
        ('Configuración del servicio', {
            'fields': (
                'duracion_minutos',
                'precio',
                'activo',
            )
        }),
        ('Profesionales habilitados', {
            'fields': (
                'profesionales',
            )
        }),
        ('Seguimiento comercial', {
            'fields': (
                'requiere_seguimiento',
                'dias_seguimiento',
            )
        }),
    )


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 1
    fields = ('monto', 'metodo', 'observacion', 'fecha')
    readonly_fields = ('fecha',)


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    form = CitaForm

    list_display = (
        'fecha',
        'hora_inicio',
        'hora_fin',
        'paciente',
        'profesional',
        'servicio',
        'estado',
        'estado_pago',
        'monto_total',
        'monto_pagado',
        'saldo_pendiente_mostrado',
    )

    search_fields = (
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__rut',
        'profesional__nombres',
        'profesional__apellidos',
        'servicio__nombre',
    )

    list_filter = (
        'fecha',
        'sucursal',
        'profesional',
        'servicio',
        'estado',
        'estado_pago',
    )

    readonly_fields = (
        'hora_fin',
        'estado_pago',
        'monto_pagado',
        'saldo_pendiente_mostrado',
        'creado_en',
        'actualizado_en',
    )

    fieldsets = (
        ('Datos de la cita', {
            'fields': (
                'sucursal',
                'paciente',
                'profesional',
                'servicio',
                'fecha',
                'hora_inicio',
                'hora_fin',
                'estado',
            )
        }),
        ('Pago', {
            'fields': (
                'monto_total',
                'monto_pagado',
                'estado_pago',
                'saldo_pendiente_mostrado',
            )
        }),
        ('Reprogramación', {
            'fields': (
                'cita_origen',
            )
        }),
        ('Observaciones', {
            'fields': (
                'observaciones',
            )
        }),
        ('Auditoría', {
            'fields': (
                'creado_en',
                'actualizado_en',
            )
        }),
    )

    inlines = [PagoInline]

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)

        profesional = request.GET.get('profesional')
        servicio = request.GET.get('servicio')
        fecha = request.GET.get('fecha')
        hora_inicio = request.GET.get('hora_inicio')

        if profesional:
            initial['profesional'] = profesional

        if servicio:
            initial['servicio'] = servicio

        if fecha:
            initial['fecha'] = fecha

        if hora_inicio:
            initial['hora_inicio'] = hora_inicio

        return initial

    def saldo_pendiente_mostrado(self, obj):
        if obj:
            return f"${obj.saldo_pendiente:,}".replace(",", ".")
        return "$0"

    saldo_pendiente_mostrado.short_description = "Saldo pendiente"

    class Media:
        js = ('core/js/cita_admin.js',)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('cita', 'monto', 'metodo', 'fecha')
    list_filter = ('metodo', 'fecha')
    search_fields = (
        'cita__paciente__nombres',
        'cita__paciente__apellidos',
        'cita__paciente__rut',
        'cita__servicio__nombre',
    )


@admin.register(SeguimientoPaciente)
class SeguimientoPacienteAdmin(admin.ModelAdmin):
    list_display = (
        'fecha_objetivo',
        'paciente',
        'servicio',
        'estado',
        'cita_origen',
    )
    list_filter = ('estado', 'servicio', 'fecha_objetivo')
    search_fields = (
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__rut',
        'servicio__nombre',
    )
    readonly_fields = ('creado_en', 'actualizado_en')