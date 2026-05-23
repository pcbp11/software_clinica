# Tareas del sistema

> **Reglas**: NO modificar models.py ni utils.py. Usar base.html con sidebar oscuro.

---

## ✅ Completado

- ✓ **Agenda rediseñada** — calendario tipo Google Calendar con bloques proporcionales (posicionamiento absoluto), indicador hora actual, scroll automático, líneas de cuadrícula CSS
- ✓ **Nueva cita desde agenda** — clic en slot disponible abre modal con profesional/hora pre-rellenados, búsqueda de paciente por nombre/RUT, selector de servicio con precio y duración
- ✓ **Modal de cita existente** — clic en tarjeta abre modal con detalle completo, cambio de estado AJAX, registro de pagos con historial, reagendar con redirección automática
- ✓ **Seguimientos** — vista con botones contactado/agendado/descartado, contador en sidebar
- ✓ Login/logout, sidebar con badges de seguimientos

---

## ✅ Completado recientemente

- ✓ **Horarios profesionales** (`/horarios/`) — tabla por día con hora inicio/fin, pausa, JS para toggle activo/pausa
- ✓ **Servicios** (`/servicios/`) — tabla con avatares de profesionales, modal para agregar con seguimiento condicional
- ✓ **Usuarios** (`/usuarios/`) — tabla con roles y badges, modal para crear, toggle activo
- ✓ Sidebar actualizado con sección "Configuración" (Horarios, Servicios, Usuarios para admins)
- ✓ **Sistema de Comisiones** (mayo 2026) — Insumo, ServicioInsumo, EstructuraComision, ComisionCalculada
- ✓ **Vista semanal de agenda** filtrada por profesional (23 mayo 2026)
- ✓ **Base de Pacientes + Ficha Clínica MVP** (24 mayo 2026) — ver CLAUDE.md para detalle completo

---

## 🔜 Próxima sesión — Insumos y Boxes obligatorios al cerrar cita

### Objetivo
Cuando una cita se marca como **"asistió"**, el sistema debe forzar al profesional a registrar:
1. **Qué insumos usó** (con cantidades) — necesario para calcular costo real y comisión
2. **Qué box de atención usó** — para tracking de uso y futura programación

Sin estos datos, la cita NO se puede "cerrar" como asistida.

### Por qué es importante
- La comisión del profesional ya considera `monto_insumos` como deducción
- Hoy ese cálculo usa valores ESTIMADOS (del template `ServicioInsumo`)
- Con esta feature, va a usar los REALMENTE usados
- También permite trazabilidad (qué lote, qué cantidad, en qué cita)

### 1. Insumo obligatorio al marcar asistió

**Modelo nuevo propuesto: `InsumoUsadoEnCita`**
- FK a `Cita`
- FK a `Insumo`
- `cantidad_usada` (decimal, igual que ServicioInsumo)
- `lote` opcional (si en el futuro se trackea por lote)
- Auditoría: registrado_por (User), creado_en

**Flujo UI propuesto**:
- Al cambiar estado de cita a "asistió" en el modal de detalle:
  - Si el servicio tiene insumos por defecto (`ServicioInsumo`), pre-cargar lista con cantidades sugeridas
  - Mostrar modal/sección con cada insumo y su cantidad editable
  - Profesional confirma o ajusta cantidades
  - Solo después de confirmar se acepta el cambio de estado a "asistió"
- Si el servicio no tiene insumos pre-definidos, igual permitir agregar manualmente

**Decisión pendiente**: ¿Se decrementa `Insumo.cantidad_disponible` automáticamente?
- Pro: refleja stock real, alerta cuando se acaba
- Contra: si después se anula la cita, hay que revertir (complejidad)
- Mi recomendación: SÍ decrementar, con un trigger para revertir en estado=cancelada

### 2. Boxes de atención

**Modelo nuevo propuesto: `Box`**
- FK a `Sucursal`
- `numero` o `nombre` (ej: "Box 1", "Sala lavanda")
- `descripcion` (opcional, "Box equipado con láser diodo")
- `activo` (bool)

**Y en `Cita`**: agregar campo `box` FK opcional (o crear modelo intermedio si queremos histórico de cambios).

**Flujo UI**:
- CRUD de boxes en sidebar grupo "Configuración" (mismo nivel que Categorías/Proveedores)
- Al marcar cita como asistió, también pedir/confirmar qué box se usó
- Posibilidad de pre-asignar box al crear la cita (no obligatorio inicialmente)

**Decisión pendiente que conversaremos**: ¿Dónde ubicar el tema de boxes?
- Opción A: solo CRUD + campo en cita (mínimo viable)
- Opción B: Lo anterior + validación de no doble-booking (más complejo)
- Opción C: Lo anterior + restricción de disponibilidad en agenda (más complejo aún)
- Mi recomendación: empezar con A (CRUD + campo en cita), después escalar si se necesita

### Diseño técnico que conversaremos al arrancar
- ¿Bloqueo del cambio de estado a nivel backend (validación) o solo a nivel UI?
- ¿Modal separado o sección expandible dentro del modal de detalle de cita?
- ¿Mostrar costo total estimado al confirmar insumos? (sumando costo_unitario × cantidad)

### ✅ Respuestas de Pía (24 mayo 2026)
1. **¿Quién registra el insumo?** Recepción al cambiar estado a "asistió". El insumo viene del catálogo (conectado por SKU).
2. **¿Quién puede saltarse la validación?** Solo admins con permisos de edición (ej. Pía para testing).
3. **¿Box al crear o al cerrar?** Asignar al crear cita, pero permitir modificar después.
4. **¿Validación de doble-booking?** Solo **alerta**, no prohibición — sirve para informar pero no bloquea.

---

## 🏢 Referencia de Boxes y servicios de la clínica
> Fuente: documento "DISTRIBUCIÓN DE BOX Y PRESTACIONES.docx" entregado por administradora (24 mayo 2026)

### Boxes existentes

| # | Tipo | Profesional(es) | Especialidades / Servicios principales |
|---|------|------------------|----------------------------------------|
| 1 | Sala de Procedimientos | Carolina Carmona, Dr Claudio Rodriguez | Derm/Cosm (PRP, Peeling, Fixer Plas, Mesoterapia, IPL Fraclight, Fototerapia, Microneedling, Crioterapia, Evaluaciones), Armonización Facial (Botox, Ácido hialurónico) |
| 2 | Sala de Procedimientos + Botiquín | Dra Paola Bonaldi, Dra María José Moyano | Derm/Cosm completo + Armonización Facial (Botox, Ác. hialurónico, Bioestimuladores, Lipolax VL, Fixer Glow, Mesoterapia Pink Glow) |
| 3 | Sala de Procedimientos | Dra Paola Bonaldi, Dr Vittorio Zaffiri | Derm/Cosm + Armonización Facial (Botox, Ác. hialurónico) |
| 4 | Multidisciplinar | Daniela Maldonado, Dr Vittorio Zaffiri (Enfermera) | Evaluaciones kinesiológicas, Depilación láser, Peeling químico, Limpiezas faciales, Fototerapia, Consultas médicas |
| 5 | Cosmetología | María José Uribe | Evaluaciones cosmetológicas, Peeling químico, Limpiezas faciales, Fototerapia |
| 6 | Nutrición + Holístico | Ignacio Diaz + Nutricionistas | Consultas nutricionales, Terapias holísticas, Masajes descontracturantes/relajación, Consultas médicas |
| 7 | Corporales / Kinesio | Daniela Maldonado | Tensamax, HIFU, Drenajes linfáticos, Masajes (relajación/post-op), Consultas kinesiológicas |
| 8 | Consultas | Dra Paola Bonaldi | Consultas dermatológicas y otras consultas médicas |
| 9 | Oftalmología | Dr Cristiano Burela | Consultas oftalmológicas |
| 10 | Procedimientos Ginecológicos (desde 29/05) | Dra Migdalia, Dr Hector Pinto | Consultas, Toma PAP, PRP vulvar, Extirpaciones ginecológicas menores, Control preventivo, Evaluación ITS, Anticonceptivos, Procedimientos vulvovaginales menores, Evaluaciones hormonales |
| 11 | Acceso Universal | Dra Paulina Cerda (Medicina General) | Derm/Cosm completo + Armonización Facial completa + Consultas médicas |

### Catálogo de servicios a verificar/agregar
Detectados en el documento — revisar que estén todos cargados en `Servicio` model:

**Dermatología/Cosmetología**:
PRP, Peeling químico, Fixer Plas, Mesoterapia facial/capilar, IPL Fraclight (Fraclight), Fototerapia, Microneedling, Tratamiento abrasivo cutáneo, Crioterapia, Evaluaciones cosmetológicas, Consultas dermatológicas, Extirpaciones, Inyección intracutánea, Limpiezas faciales

**Armonización Facial**:
Botox, Ácido hialurónico, Bioestimuladores, Lipolax VL, Fixer Glow, Mesoterapia Pink Glow, Evaluaciones y controles

**Kinesiología/Corporales**:
Evaluaciones kinesiológicas, Tensamax, HIFU, Drenajes linfáticos, Masajes de relajación, Masajes post-operatorios

**Otras**:
Depilación láser, Consultas nutricionales, Terapias holísticas, Masajes descontracturantes, Consultas oftalmológicas, Consultas ginecológicas, Toma de PAP, PRP vulvar, Extirpaciones ginecológicas menores, Control ginecológico preventivo, Evaluación de ITS, Colocación/retiro de anticonceptivos, Procedimientos vulvovaginales menores, Evaluaciones hormonales, Consultas médicas

### Profesionales detectados en el documento
- Carolina Carmona — Cosmetóloga
- Dr Claudio Rodriguez — Armonización Facial
- Dra Paola Bonaldi — Dermatóloga
- Dra María José Moyano — Armonización Facial
- Dr Vittorio Zaffiri — Dermatólogo + Enfermería
- Daniela Maldonado — Kinesióloga
- María José Uribe — Cosmetóloga
- Ignacio Diaz — Nutricionista
- Dr Cristiano Burela — Oftalmólogo
- Dra Migdalia — Ginecóloga
- Dr Hector Pinto — Ginecólogo
- Dra Paulina Cerda — Medicina General

### Modelo Box propuesto (revisado con info real)
```python
class Box(models.Model):
    sucursal = ForeignKey(Sucursal)
    numero = IntegerField()                    # 1, 2, 3...
    nombre = CharField(max_length=150)         # "Box 1 - Sala de Procedimientos"
    descripcion = TextField(blank=True)
    es_acceso_universal = BooleanField(default=False)  # Box 11 especial
    fecha_inicio_uso = DateField(null=True, blank=True)  # Box 10 desde 29/05
    activo = BooleanField(default=True)
    profesionales_habituales = M2M(Profesional, blank=True)
    servicios_disponibles = M2M(Servicio, blank=True)
```

Y en `Cita`: `box = FK(Box, null=True, blank=True)`.

---

## 🟠 También conversado pero pendiente (no urgente)

- **OAuth con Google + Microsoft** (django-allauth) — botones de login con allowlist obligatorio
- **Consentimiento legal del paciente** en primer acceso a ficha clínica (Ley 19.628 / 21.719)
- **Overlay "Profesional no disponible"** en franjas no laborales de vista semanal de agenda
- **Auto-formato de RUT en formulario de Pacientes** (consistencia con Profesionales/Proveedores)