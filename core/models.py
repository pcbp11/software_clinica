from datetime import date, datetime, timedelta
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


telefono_validator = RegexValidator(
    regex=r'^\+569\d{8}$',
    message="El teléfono debe estar en formato +569XXXXXXXX"
)


class Empresa(models.Model):
    nombre = models.CharField(max_length=150)
    razon_social = models.CharField(max_length=200, blank=True)
    rut = models.CharField(max_length=12, unique=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=12, validators=[telefono_validator])
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    color_principal = models.CharField(max_length=20, default='#2E8B8B')
    color_secundario = models.CharField(max_length=20, default='#F5F5F5')
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.nombre


class UnidadNegocio(models.Model):
    TIPOS_IMPUESTO = [
        ('afecto', 'Afecto a IVA'),
        ('exento', 'Exento'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='unidades_negocio')
    nombre = models.CharField(max_length=150)
    razon_social = models.CharField(max_length=200, blank=True)
    rut = models.CharField(max_length=12, blank=True)
    descripcion = models.TextField(blank=True)
    tipo_impuesto = models.CharField(max_length=10, choices=TIPOS_IMPUESTO, default='exento')
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Unidad de negocio"
        verbose_name_plural = "Unidades de negocio"

    def __str__(self):
        return f"{self.nombre} - {self.empresa.nombre}"


class Sucursal(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='sucursales')
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=250, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    comuna = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=12, validators=[telefono_validator])
    email = models.EmailField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"

    def __str__(self):
        return f"{self.nombre} - {self.empresa.nombre}"


class Paciente(models.Model):
    TIPOS_CLIENTE = [
        ('nuevo', 'Nuevo'),
        ('recurrente', 'Recurrente'),
        ('perdido', 'Perdido'),
    ]

    GENEROS = [
        ('femenino', 'Femenino'),
        ('masculino', 'Masculino'),
        ('no_binario', 'No binario'),
        ('prefiero_no_decir', 'Prefiero no decir'),
    ]

    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='pacientes')
    rut = models.CharField(max_length=12, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=12, validators=[telefono_validator], help_text="Formato: +569XXXXXXXX")
    email = models.EmailField(blank=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=20, choices=GENEROS, blank=True)
    fecha_ingreso = models.DateField(auto_now_add=True)
    origen = models.CharField(max_length=100, blank=True)
    tipo_cliente = models.CharField(max_length=20, choices=TIPOS_CLIENTE, default='nuevo')
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def __str__(self):
        return f"{self.nombres} {self.apellidos} - {self.rut}"

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        edad = hoy.year - self.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day):
            edad -= 1
        return edad


class Profesional(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='profesionales')
    sucursal_principal = models.ForeignKey(
        Sucursal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profesionales'
    )
    rut = models.CharField(max_length=12, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100, blank=True)
    nombre_publico = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=12, validators=[telefono_validator], help_text="Formato: +569XXXXXXXX")
    foto = models.ImageField(upload_to='profesionales/', blank=True, null=True)
    biografia = models.TextField(blank=True)
    certificado_salud = models.FileField(upload_to='certificados/', blank=True, null=True)
    acepta_reservas_online = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)
    fecha_ingreso = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Profesional"
        verbose_name_plural = "Profesionales"

    def __str__(self):
        return self.nombre_publico if self.nombre_publico else f"{self.nombres} {self.apellidos}"


class HorarioProfesional(models.Model):
    DIAS_SEMANA = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    profesional = models.ForeignKey(Profesional, on_delete=models.CASCADE, related_name='horarios')
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    activo = models.BooleanField(default=False)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    tiene_descanso = models.BooleanField(default=False)
    inicio_descanso = models.TimeField(null=True, blank=True)
    fin_descanso = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('profesional', 'dia_semana')
        verbose_name = "Horario profesional"
        verbose_name_plural = "Horarios profesionales"

    def __str__(self):
        return f"{self.profesional} - {self.get_dia_semana_display()}"


class CategoriaServicio(models.Model):
    unidad_negocio = models.ForeignKey(UnidadNegocio, on_delete=models.CASCADE, related_name='categorias')
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría de servicio"
        verbose_name_plural = "Categorías de servicio"

    def __str__(self):
        return f"{self.nombre} - {self.unidad_negocio.nombre}"


class Servicio(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='servicios')
    unidad_negocio = models.ForeignKey(UnidadNegocio, on_delete=models.CASCADE, related_name='servicios')
    categoria = models.ForeignKey(
        CategoriaServicio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='servicios'
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    duracion_minutos = models.PositiveIntegerField()
    precio = models.PositiveIntegerField(help_text="Valor en pesos chilenos. Ej: 230000")
    profesionales = models.ManyToManyField(Profesional, related_name='servicios', blank=True)
    activo = models.BooleanField(default=True)

    requiere_seguimiento = models.BooleanField(default=False)
    dias_seguimiento = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad de días para contactar nuevamente. Ej: 90 para Botox."
    )

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return f"{self.nombre} - {self.unidad_negocio.nombre}"

    @property
    def tipo_impuesto(self):
        return self.unidad_negocio.tipo_impuesto


class Cita(models.Model):
    ESTADOS = [
        ('reservado', 'Reservado'),
        ('pendiente', 'Pendiente (no pagado)'),
        ('confirmado', 'Confirmado'),
        ('en_espera', 'En espera'),
        ('asistio', 'Asistió'),
        ('no_asistio', 'No asistió'),
        ('cancelada', 'Cancelada'),
        ('reprogramada', 'Reprogramada'),
    ]

    ESTADOS_PAGO = [
        ('sin_pago', 'Sin pago'),
        ('abonado', 'Abonado'),
        ('pagado', 'Pagado'),
    ]

    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='citas')
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='citas')
    profesional = models.ForeignKey(Profesional, on_delete=models.CASCADE, related_name='citas')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='citas')

    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='reservado')

    monto_total = models.PositiveIntegerField(default=0)
    monto_pagado = models.PositiveIntegerField(default=0)
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='sin_pago')

    observaciones = models.TextField(blank=True)

    cita_origen = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='citas_reprogramadas'
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['fecha', 'hora_inicio']

    def calcular_hora_fin(self):
        if self.servicio and self.hora_inicio and self.fecha:
            inicio = datetime.combine(self.fecha, self.hora_inicio)
            fin = inicio + timedelta(minutes=self.servicio.duracion_minutos)
            return fin.time()
        return self.hora_fin

    def actualizar_estado_pago(self):
        if self.monto_pagado <= 0:
            self.estado_pago = 'sin_pago'
        elif self.monto_total and self.monto_pagado < self.monto_total:
            self.estado_pago = 'abonado'
        else:
            self.estado_pago = 'pagado'

    def recalcular_pagos(self):
        total_pagado = sum(pago.monto for pago in self.pagos.all())
        self.monto_pagado = total_pagado
        self.actualizar_estado_pago()
        self.save()

    def clean(self):
        if self.servicio and self.profesional:
            profesionales_servicio = self.servicio.profesionales.all()
            if profesionales_servicio.exists() and self.profesional not in profesionales_servicio:
                raise ValidationError("El profesional seleccionado no realiza este servicio.")

        if self.fecha and self.hora_inicio and self.servicio and self.profesional:
            dia_semana = self.fecha.weekday()

            horario = HorarioProfesional.objects.filter(
                profesional=self.profesional,
                dia_semana=dia_semana,
                activo=True
            ).first()

            if not horario:
                raise ValidationError("El profesional no atiende este día.")

            if not horario.hora_inicio or not horario.hora_fin:
                raise ValidationError("El horario del profesional no está bien definido.")

            hora_fin_calculada = self.calcular_hora_fin()

            if not (horario.hora_inicio <= self.hora_inicio and hora_fin_calculada <= horario.hora_fin):
                raise ValidationError("La cita está fuera del horario del profesional.")

            if horario.tiene_descanso and horario.inicio_descanso and horario.fin_descanso:
                if horario.inicio_descanso < hora_fin_calculada and self.hora_inicio < horario.fin_descanso:
                    raise ValidationError("La cita coincide con el horario de descanso del profesional.")

            citas_cruzadas = Cita.objects.filter(
                profesional=self.profesional,
                fecha=self.fecha
            ).exclude(
                estado__in=['cancelada', 'reprogramada']
            ).exclude(
                pk=self.pk
            ).filter(
                hora_inicio__lt=hora_fin_calculada,
                hora_fin__gt=self.hora_inicio
            )

            if citas_cruzadas.exists():
                raise ValidationError("Este profesional ya tiene una cita en ese horario.")

    def crear_seguimiento_si_corresponde(self):
        if (
            self.estado == 'asistio'
            and self.servicio
            and self.servicio.requiere_seguimiento
            and self.servicio.dias_seguimiento
        ):
            existe = SeguimientoPaciente.objects.filter(cita_origen=self).exists()

            if not existe:
                fecha_seguimiento = self.fecha + timedelta(days=self.servicio.dias_seguimiento)

                SeguimientoPaciente.objects.create(
                    paciente=self.paciente,
                    servicio=self.servicio,
                    cita_origen=self,
                    fecha_objetivo=fecha_seguimiento,
                    estado='pendiente',
                    observaciones='Seguimiento generado automáticamente.'
                )

    def save(self, *args, **kwargs):
        if self.servicio:
            if not self.monto_total:
                self.monto_total = self.servicio.precio

            if self.hora_inicio and self.fecha:
                self.hora_fin = self.calcular_hora_fin()

        self.actualizar_estado_pago()
        self.clean()
        super().save(*args, **kwargs)

        self.crear_seguimiento_si_corresponde()

    @property
    def saldo_pendiente(self):
        return max(self.monto_total - self.monto_pagado, 0)

    def __str__(self):
        return f"{self.paciente} - {self.servicio} - {self.fecha} {self.hora_inicio}"


class Pago(models.Model):
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('debito', 'Tarjeta Débito'),
        ('credito', 'Tarjeta Crédito'),
        ('transferencia', 'Transferencia'),
        ('webpay', 'WebPay'),
        ('otro', 'Otro'),
    ]

    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='pagos')
    monto = models.PositiveIntegerField()
    metodo = models.CharField(max_length=20, choices=METODOS_PAGO)
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_metodo_display()} - ${self.monto} - {self.cita}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.cita.recalcular_pagos()

    def delete(self, *args, **kwargs):
        cita = self.cita
        super().delete(*args, **kwargs)
        cita.recalcular_pagos()


class SeguimientoPaciente(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('contactado', 'Contactado'),
        ('agendado', 'Agendado'),
        ('descartado', 'Descartado'),
    ]

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='seguimientos')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='seguimientos')
    cita_origen = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='seguimientos')

    fecha_objetivo = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    observaciones = models.TextField(blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Seguimiento de paciente"
        verbose_name_plural = "Seguimientos de pacientes"
        ordering = ['fecha_objetivo']

    def __str__(self):
        return f"{self.paciente} - {self.servicio} - {self.fecha_objetivo}"


class Descuento(models.Model):
    TIPOS = [
        ('porcentaje', 'Porcentaje (%)'),
        ('valor_fijo', 'Valor fijo ($)'),
    ]

    ESTADOS = [
        ('pendiente', 'Pendiente de autorización'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='descuentos')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    valor = models.PositiveIntegerField(help_text="Si es %, ingresar 10 para 10%. Si es $, ingresar la cantidad.")
    monto_descuento = models.PositiveIntegerField(help_text="Monto final a descontar en pesos")
    razon = models.TextField(blank=True, help_text="Ej: Autorizado por Natalia Carro")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    solicitado_por = models.CharField(max_length=100, blank=True)  # Nombre de quien solicitó
    autorizado_por = models.CharField(max_length=100, blank=True)  # Nombre de quien autorizó
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Descuento"
        verbose_name_plural = "Descuentos"
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f"Descuento {self.get_tipo_display()} - {self.cita} - {self.get_estado_display()}"

    @property
    def monto_fmt(self):
        """Formato de visualización del monto"""
        return f"${self.monto_descuento:,.0f}".replace(',', '.')


# ── COMMISSION SYSTEM ────────────────────────────────────────────────────────

class Insumo(models.Model):
    """Productos/insumos utilizados en servicios con costo de inventario"""

    UNIDADES = [
        ('unidad', 'Unidad'),
        ('ml', 'ml'),
        ('gr', 'gr'),
        ('caja', 'Caja'),
    ]

    unidad_negocio = models.ForeignKey(UnidadNegocio, on_delete=models.CASCADE, related_name='insumos')
    nombre = models.CharField(max_length=200)
    codigo_sku = models.CharField(max_length=50, blank=True, unique=True)
    descripcion = models.TextField(blank=True)

    costo_unitario = models.PositiveIntegerField(help_text="Costo en pesos chilenos")
    precio_venta = models.PositiveIntegerField(
        help_text="Precio de venta en pesos chilenos",
        null=True,
        blank=True
    )

    unidad = models.CharField(max_length=20, choices=UNIDADES, default='unidad')
    cantidad_disponible = models.PositiveIntegerField(default=0)

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.codigo_sku})" if self.codigo_sku else self.nombre

    @property
    def margen(self):
        """Margen de ganancia: (precio_venta - costo) / precio_venta * 100"""
        if not self.precio_venta or self.precio_venta == 0:
            return 0
        return ((self.precio_venta - self.costo_unitario) / self.precio_venta) * 100


class ServicioInsumo(models.Model):
    """Relación M2M entre Servicio e Insumo con cantidad utilizada"""

    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='insumos_usados')
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='servicios')
    cantidad_usada = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Cantidad de insumo usado por cada servicio"
    )

    class Meta:
        verbose_name = "Servicio-Insumo"
        verbose_name_plural = "Servicios-Insumos"
        unique_together = ('servicio', 'insumo')

    def __str__(self):
        return f"{self.servicio.nombre} → {self.insumo.nombre} ({self.cantidad_usada}{self.insumo.unidad})"

    @property
    def costo_total(self):
        """Costo total del insumo para este servicio"""
        return int(float(self.cantidad_usada) * self.insumo.costo_unitario)


class EstructuraComision(models.Model):
    """Define la estructura de comisión para cada profesional por unidad + categoría de servicio"""

    TIPOS_TRIBUTO = [
        ('afecta', 'Afecta a IVA'),
        ('exenta', 'Exenta'),
    ]

    profesional = models.ForeignKey(Profesional, on_delete=models.CASCADE, related_name='estructuras_comision')
    unidad_negocio = models.ForeignKey(UnidadNegocio, on_delete=models.CASCADE, related_name='estructuras_comision')
    categoria_servicio = models.ForeignKey(CategoriaServicio, on_delete=models.CASCADE, related_name='estructuras_comision')

    tipo_tributo = models.CharField(max_length=10, choices=TIPOS_TRIBUTO, default='exenta')
    valor_comision = models.PositiveIntegerField(
        help_text="Porcentaje de comisión (ingresar 30 para 30%)"
    )

    activa = models.BooleanField(default=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    vigencia_indefinida = models.BooleanField(default=False, help_text="Si está activado, la estructura no tiene fecha de fin")
    incluye_insumo = models.BooleanField(default=False, help_text="Si está activado, el cálculo de comisión descuenta el costo de insumos")
    notas = models.TextField(blank=True)

    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Estructura de comisión"
        verbose_name_plural = "Estructuras de comisión"

    def __str__(self):
        return f"{self.profesional} - {self.unidad_negocio.nombre} / {self.categoria_servicio.nombre} ({self.get_tipo_tributo_display()})"

    @property
    def vigente(self):
        """¿Esta estructura está vigente hoy?"""
        hoy = date.today()
        if not self.activa:
            return False
        if self.fecha_inicio > hoy:
            return False
        if not self.vigencia_indefinida and self.fecha_fin and self.fecha_fin < hoy:
            return False
        return True


class ComisionCalculada(models.Model):
    """Registro de comisiones calculadas por profesional y cita"""

    profesional = models.ForeignKey(Profesional, on_delete=models.CASCADE, related_name='comisiones_calculadas')
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='comisiones')
    estructura_comision = models.ForeignKey(EstructuraComision, on_delete=models.SET_NULL, null=True, blank=True)

    # Montos
    monto_ingresos_brutos = models.PositiveIntegerField(help_text="Ingresos totales del servicio")
    monto_insumos = models.PositiveIntegerField(default=0, help_text="Costo total de insumos utilizados")
    monto_descuentos = models.PositiveIntegerField(default=0, help_text="Descuentos aplicados a la cita")
    monto_neto = models.PositiveIntegerField(help_text="Ingresos brutos - insumos - descuentos")
    monto_comision = models.PositiveIntegerField(help_text="Comisión calculada para el profesional")

    # Referencia
    porcentaje_comision = models.PositiveIntegerField(help_text="Porcentaje de comisión aplicado")
    mes_referencia = models.CharField(max_length=7, help_text="Formato YYYY-MM para agrupar por mes")

    # Auditoría
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comisión calculada"
        verbose_name_plural = "Comisiones calculadas"
        ordering = ['-fecha_calculo']
        indexes = [
            models.Index(fields=['profesional', 'mes_referencia']),
            models.Index(fields=['mes_referencia']),
        ]

    def __str__(self):
        return f"{self.profesional.nombre_publico} - ${self.monto_comision:,} - {self.mes_referencia}"

    @property
    def tipo_comision_display(self):
        if self.estructura_comision:
            return self.estructura_comision.get_tipo_comision_display()
        return "Manual"