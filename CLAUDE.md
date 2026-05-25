# 🏥 Software Clínica Médica Estética - Documentación

## 📋 Descripción general
Sistema de gestión integral para una Clínica Médica Estética ubicada en La Serena. Reemplaza/complementa Agenda Pro (muy limitado) y sistemas administrativos en Google Sheets.

**Estado**: Desarrollo activo
**Stack**: Django 4.x + SQLite (dev) + HTML/CSS/JS + Flatpickr + Pillow (imágenes)
**Desarrollador**: Pía Barraza (usando Cursor + Claude Code)

---

## 🏗️ Estructura del proyecto

```
software_clinica/
├── config/              # Configuración Django
│   ├── settings.py     # Configuración principal (SQLite, DEBUG=True)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/               # App principal
│   ├── models.py       # ⚠️ MODIFICAR SOLO SI ES INEVITABLE (con migración)
│   ├── views.py
│   ├── admin.py
│   ├── utils.py        # ⚠️ NO MODIFICAR (solo lectura)
│   ├── context_processors.py
│   ├── migrations/     # Última: 0027 (ficha clínica + servicio/aparatologia)
│   ├── static/js/
│   └── templatetags/
│       └── clinica_tags.py   # Filtros: |pesos, |rut
├── templates/          # HTML - estilo unificado, sidebar oscuro
├── static/             # CSS, JS compartido
├── media/              # 📷 Fichas clínicas (fotos de evolución protegidas)
│   └── fichas_clinicas/<paciente_id>/<YYYY-MM>/
├── logos/              # Recursos visuales
├── manage.py
├── db.sqlite3
├── TAREAS.md          # Features pendientes (ver abajo)
└── CLAUDE.md          # Este archivo
```

---

## 🗄️ Modelos de datos (✓ Funcionales)

### Estructura corporativa
- **Empresa**: Clínica madre (nombre, RUT, colores, logo)
- **Sucursal**: Ubicaciones de la clínica (empresa, dirección, teléfono)
- **UnidadNegocio**: Divisiones contables (Botox, Rellenos, etc.)
- **CategoriaServicio**: Categorización dentro de unidad

### Personas
- **Paciente**: Clientes (RUT, contacto, tipo: nuevo/recurrente/perdido, fecha_nacimiento, género, origen)
  - Property `edad`: calculada desde fecha_nacimiento
- **Profesional**: Médicos/esteticistas (RUT, nombre_publico, foto, certificado)
- **HorarioProfesional**: Disponibilidad por día semana (lunes-domingo, descanso)

### Negocio
- **Servicio**: Procedimientos (nombre, duracion_minutos, precio, profesionales M2M, unidad_negocio)
- **Cita**: Agendamiento (paciente, profesional, servicio, fecha, hora, estado)
  - Estados: reservado, pendiente, confirmado, en_espera, asistió, no_asistió, cancelada, reprogramada
  - Control de pago: monto_total, monto_pagado, estado_pago
  - Validaciones: respeta horarios del profesional, evita cruces, respeta descansos
- **Pago**: Registro de pagos (efectivo, débito, crédito, transferencia, WebPay)
- **SeguimientoPaciente**: Contactos post-cita (para servicios que requieren follow-up)
- **Descuento**: Sistema de autorización de descuentos con email + workflow

### Sistema de Comisiones
- **Insumo**: Productos/materiales con costo de inventario
- **ServicioInsumo**: M2M Servicio-Insumo (cantidad por servicio)
- **EstructuraComision**: Define comisión por profesional y unidad
  - Tipos: porcentaje, fijo_por_servicio, sociedad_carro, clinica_salud_70_30
- **ComisionCalculada**: Registro histórico de cálculos mensuales

### Boxes de Atención ⭐ NUEVO (25 mayo 2026)
- **Box**: Espacios físicos donde se realizan atenciones
  - `numero` (único por sucursal), `nombre`, `descripcion`, `activo`
  - `es_acceso_universal` (Box 11) y `fecha_inicio_uso` (Box 10 desde 29/05)
  - M2M `profesionales_habituales` y `servicios_disponibles`
  - 11 boxes precargados desde el documento real de la clínica
  - Property `disponible_hoy` (False si `fecha_inicio_uso > date.today()`)
- **Cita.box** (FK opcional): asignable al crear, modificable después
  - Validación: obligatorio al marcar estado="asistió"
  - Doble-booking detectado (alerta, no prohibición)

### Sistema de Ficha Clínica ⭐ NUEVO
- **FichaClinicaPaciente**: Antecedentes médicos (1 por paciente, OneToOne)
  - Alergias, enfermedades crónicas, medicamentos, cirugías previas, antecedentes estéticos
  - Embarazo/lactancia (choices: no_aplica/embarazo/lactancia/busca)
  - Contraindicaciones (texto libre — se destaca como alerta roja)
  - Property `tiene_contraindicaciones` para banner de alerta
- **RegistroAtencion**: Bitácora de cada atención clínica
  - FK opcional a `Cita` (OneToOne) y a `Servicio` (selector buscable)
  - Profesional (FK PROTECT)
  - Campos clínicos: motivo_consulta, procedimiento_realizado, productos_utilizados, **aparatologia**, parametros, zonas_tratadas
  - Resultados: observaciones, indicaciones_post, plan_proxima_sesion
  - Auditoría: creado_por, actualizado_por (User FKs)
- **FotoEvolucion**: Galería de evolución del paciente
  - Tipos: antes, durante, después, control, otro
  - FK opcional a `RegistroAtencion` (organiza por sesión)
  - Almacenadas en `media/fichas_clinicas/<paciente_id>/<YYYY-MM>/`
  - Servidas vía vista Django con auth check (NO link directo)
- **AuditLogFicha**: Bitácora de accesos y modificaciones
  - Acciones: view, antecedentes_create/update, registro_create/update/delete, foto_upload/view/delete
  - Captura usuario, paciente, acción, detalle, timestamp, IP
  - Indexada por (paciente, timestamp) y (usuario, timestamp)

---

## ✅ Features completadas

### Sesión Actual (25 mayo 2026) — Boxes de atención + Validaciones de cierre + Colación bloqueada

#### 🏢 Sistema de Boxes de atención ⭐ (la feature principal de la sesión)

**Modelos** (`core/models.py` + migraciones 0028 y 0029):
- `Box` con: número (único por sucursal), nombre, descripción, `es_acceso_universal` (Box 11), `fecha_inicio_uso` (Box 10 desde 29/05), `activo`, M2M `profesionales_habituales`, M2M `servicios_disponibles`
- Campo `box` FK opcional en `Cita` (asignable al crear, modificable después)
- Migración `0029_seed_boxes_iniciales` **precarga los 11 boxes reales** del documento "DISTRIBUCIÓN DE BOX Y PRESTACIONES.docx":
  - Box 1: Sala de Procedimientos — Carolina Carmona + Dr Claudio Rodriguez
  - Box 2: Sala de Procedimientos + Botiquín — Paola Bonaldi + María José Moyano
  - Box 3: Sala de Procedimientos — Paola Bonaldi + Vittorio Zaffiri
  - Box 4: Multidisciplinar — Daniela Maldonado + Vittorio Zaffiri
  - Box 5: Cosmetología — María José Uribe
  - Box 6: Nutrición + Holístico — Ignacio Diaz + Nutricionistas
  - Box 7: Corporales/Kinesiología — Daniela Maldonado
  - Box 8: Consultas — Paola Bonaldi
  - Box 9: Oftalmología — Cristiano Burela
  - Box 10: Procedimientos Ginecológicos (desde 29/05) — Migdalia + Hector Pinto
  - Box 11: Acceso Universal — Paulina Cerda

**Vistas** (`core/views.py`):
- `boxes_view` — lista con búsqueda, filtros, stats (Total/Activos/Universal)
- `crear_box`, `editar_box`, `toggle_box`, `eliminar_box` — CRUD completo
- `actualizar_box_cita` — endpoint AJAX para cambiar el box de una cita desde el modal de detalle
- Helper `_detectar_doble_booking_box()` — chequea overlap considerando duración del servicio (no solo hora_inicio exacta)

**URLs**: 6 rutas nuevas (`/boxes/` + crear/editar/toggle/eliminar + AJAX update por cita)

**Template `boxes.html`**:
- Lista al estilo unificado del proyecto (stats-mini + filtros + tabla)
- Cada fila muestra: número en círculo verde, nombre, descripción, badges UNIVERSAL/Desde-fecha, pills de profesionales habituales (verdes), pills de servicios (primeros 4 + "más"), estado activo/inactivo
- Modal de crear/editar con grid 2-col: número + sucursal, nombre, descripción, fecha inicio + checkbox universal
- **Multi-select con buscador en vivo** para profesionales y servicios (sin libraries — vanilla JS)
- Sidebar: link "Boxes" en grupo Configuración (arriba de Categorías)

#### 🔗 Integración Boxes ↔ Agenda

**Modal "Nueva cita"**:
- Campo "Box de atención (opcional)" en grid 2-col junto a Profesional
- `boxes_activos` pasado desde `agenda_view`
- Backend (`crear_cita`): guarda el box; si hay doble-booking detectado, muestra alerta amarilla con `messages.warning` pero NO bloquea el guardado

**Modal "Detalle de cita"**:
- Nueva sección "Box de atención" entre Estado y Observaciones
- Dropdown con todos los boxes activos + opción "— Sin asignar —"
- **Auto-guardado AJAX** al cambiar selección → muestra "✓ Guardado" verde
- Si hay doble-booking, muestra pill ámbar inline (no bloquea)
- `detalle_cita` (JSON) ahora expone `box_id` y `box_nombre`

#### 🔒 Validación obligatoria: Box al marcar "Asistió"

- Backend `actualizar_estado_cita`: si `nuevo_estado == 'asistio'` y `cita.box is None`, rebota con HTTP 400 + `{ error, requiere_box: true }`
- Frontend (`cambiarEstado`): detecta `requiere_box` en respuesta y dispara `mostrarErrorRequiereBox()`:
  - Resalta el select de box con **borde rojo + sombra**
  - Muestra mensaje inline sobre el select: "⚠️ Debes asignar un box antes de marcar Asistió"
  - Scroll suave a la sección Box
  - Focus en el dropdown
  - Listener que limpia los estilos rojos apenas el usuario selecciona algo
- Otros estados (Confirmado, En espera, Cancelada, etc.) NO requieren box
- Patrón listo para reutilizar cuando agreguemos validación de insumos

#### 🕐 Colación bloqueada visualmente en la agenda

**Problema previo**: la franja de descanso del profesional aparecía como slots clicables, y solo rechazaba al guardar con un mensaje reactivo. Mala UX.

**Ahora**:
- `agenda_view` cruza con `HorarioProfesional` para cada profesional del día. Si `tiene_descanso=True`, los bloques que caen en el rango `(inicio_descanso, fin_descanso)` se marcan con `estado='descanso'` + `descanso_inicio/fin`
- Loop de render separa los bloques de descanso a una nueva lista `descansos_render` (no entran a `slots_render`, por lo tanto no hay botón clicable)
- Template: nueva clase CSS `.cal-descanso` con:
  - Fondo gris claro con **rayado diagonal** (`repeating-linear-gradient 135deg`)
  - `cursor: not-allowed`
  - Etiqueta **"ALMUERZO"** + rango horario "13:00 – 14:00"
  - Title attribute con info
- **Compatible con modo día y modo semana**
- **No modifiqué `utils.py`** (respetando restricción del proyecto); la lógica se inyecta como post-procesamiento en `agenda_view`

#### 🐛 Fix de bug detectado durante revisión

- `templates/core/descuentos_pendientes.html` usaba `{% widthratio descuentos|dictsort:"monto_descuento"|sum 1 1 %}` — el filtro `|sum` NO existe en Django built-ins. Habría fallado en `/descuentos/pendientes/` con descuentos en lista
- Fix: calcular total con `Sum('monto_descuento')` en la vista, formatear con filtro `|pesos` en el template
- También limpieza: había **2 definiciones** de `descuentos_pendientes_view` (líneas 637 y 1327); Python sobrescribía la primera. Eliminé la duplicada obsoleta

### Sesión anterior (23-24 mayo 2026) — Pacientes + Ficha Clínica + Polish UX

#### 🔧 Fixes y mejoras en modal "Nueva cita"
- ✓ **Bug timezone del mini-calendario**: `new Date('YYYY-MM-DD')` parseaba como UTC y al formatear en zona horaria local retrocedía un día. Fix: construir `Date` con componentes locales.
- ✓ **Fecha editable** en modal de nueva cita (antes era read-only)
  - Implementado con Flatpickr + altInput (display amigable, value ISO al backend)
  - En slot-click: pre-rellena con el día del slot
  - En libre (botón "+ Nueva cita"): arranca vacío
- ✓ **Hora editable** con default a hora chilena actual (`Intl.DateTimeFormat` con `timeZone: 'America/Santiago'`)
- ✓ **Profesional editable** (select con todos los activos vía `todos_profesionales` en context)
- ✓ **Botón "+ Nuevo cliente"** inline en el modal — abre un sub-form con: Nombre, Apellido, RUT (auto-formato), Fecha nacimiento, Teléfono (+569), Email
  - Hidden input `modo_paciente=existente|nuevo` para distinguir modo en backend
  - Backend (`crear_cita`): si modo='nuevo' crea Paciente primero (full_clean), si RUT ya existe lo reutiliza con `messages.info`
  - Fix incidental en `crear_cita`: `Sucursal.objects.filter(activo=...)` → `activa=...` (era bug latente, el campo real es `activa`)

#### 👥 Sección "Base de pacientes" completa ⭐
- ✓ **Lista (`/pacientes/`)** con:
  - 5 stats: Total, Activos, Nuevos este mes, Recurrentes, Perdidos
  - Banner 🎂 cumpleaños del mes (pills clicleables → ficha)
  - Búsqueda unificada: nombre, apellido, RUT, teléfono, email
  - Filtros: tipo cliente, estado (activo/inactivo)
  - Tabla con avatar, nombre, RUT formateado, teléfono, edad, última visita, badge tipo
  - Modal "+ Nuevo paciente" con auto-formato RUT y prefijo +569
- ✓ **Ficha individual (`/pacientes/<id>/`)** con:
  - Columna izquierda: identidad (avatar grande, badges) + datos completos + edición inline
  - Columna derecha: 4 KPIs (visitas, total gastado, servicio favorito, profesional habitual)
  - Próxima cita destacada con fecha completa y profesional
  - Historial de las 30 citas más recientes con estado coloreado
  - Botón verde "Ver ficha clínica" a `/pacientes/<id>/ficha/`
- ✓ **Auto-clasificación de tipo_cliente**: helper `_calcular_tipo_cliente()`
  - nuevo: 0-1 cita asistida
  - recurrente: 2+ citas y última fue hace ≤6 meses
  - perdido: ≥1 cita pero última fue hace >6 meses
  - Alert ⚠️ amarillo si el manual no coincide con el calculado, con botón "Reclasificar"
- ✓ **Endpoint**: `pacientes_view`, `paciente_detalle_view`, `crear_paciente`, `editar_paciente`, `toggle_paciente`, `reclasificar_paciente`
- ✓ Sidebar: nuevo link "Base de pacientes" en grupo Pacientes
- ✓ Búsqueda incluye `paciente.email` además de los otros campos

#### 🩺 Ficha Clínica MVP ⭐⭐ (la feature más grande de la sesión)

**Modelos** (`core/models.py` + migración 0026):
- `FichaClinicaPaciente`, `RegistroAtencion`, `FotoEvolucion`, `AuditLogFicha`
- Migración 0027 agregó `servicio` FK + `aparatologia` TextField a `RegistroAtencion`

**Vistas** (`core/views.py`):
- `ficha_clinica_view` — vista principal (antecedentes + timeline + galería + audit)
- `guardar_antecedentes` — POST actualiza el bloque de antecedentes médicos
- `crear_registro_atencion` / `editar_registro_atencion` / `eliminar_registro_atencion`
- `subir_foto_evolucion` / `editar_foto_evolucion` / `eliminar_foto_evolucion`
- `servir_foto_evolucion` — **endpoint protegido** con auth check (no MEDIA_URL directo)
- Helpers: `_get_client_ip`, `_log_ficha`, `_puede_ver_ficha`, `_puede_editar_registro`

**Permisos**:
- Ver ficha: cualquier staff o profesional activo (consensuado con usuaria — necesario para coordinar tratamientos cruzados ej: bótox + dermatología)
- Editar/borrar registro: solo el creador o admin
- Antecedentes: editables por cualquier profesional activo (conocimiento compartido)

**Template `ficha_clinica.html`**:
- Banner rojo automático de **contraindicaciones** cuando hay alergias, embarazo/lactancia o restricciones
- Bloque de **antecedentes** con toggle vista/edición inline
- Bloque amarillo "Citas atendidas sin registro" que sugiere crearlos (con botón pre-cargado)
- **Timeline de registros** con borde verde si tú lo creaste
  - Servicio mostrado como badge verde junto a la fecha
  - Detalle: motivo, procedimiento, productos, aparatología, parámetros, zonas, observaciones, indicaciones, plan próx
  - Mini-galería de fotos AL FINAL de cada registro con upload contextual
- **Galería de evolución (vista resumen)** agrupada por sesión:
  - Header por cada registro con fecha + servicio + profesional + cantidad de fotos
  - Sección extra "Fotos sin sesión asociada" al final si las hay
- **Audit log** colapsable al pie

**Servicio buscable en registro de atención**:
- Patrón `search-select-wrap` (custom, sin libraries)
- Filtra mientras escribes por nombre o unidad de negocio
- Catálogo se pasa vía `{{ servicios_json|json_script:"servicios-data" }}` (Django pattern seguro contra escape issues)
- Si seleccionas un servicio, pre-rellena "Procedimiento realizado" con el nombre como punto de partida

**Edición de fotos**:
- Modal de editar permite cambiar tipo, fecha, zona, descripción, sesión asociada
- **Opcionalmente reemplazar el archivo** (campo file opcional — si subes una nueva, reemplaza; si no, solo actualiza metadata)
- Permisos: solo el que subió o staff
- Si no hay registros aún, muestra hint amarillo "⚠️ Crea un registro primero" con botón rápido

#### 🔗 Integración Agenda ↔ Ficha Clínica
- ✓ `detalle_cita` JSON ahora expone: `paciente_id`, `servicio_id`, `tiene_registro_atencion`, `registro_atencion_id`
- ✓ Modal de detalle de cita en agenda tiene 3 CTAs contextuales:
  - **Siempre visible**: link "Ficha clínica" → ficha del paciente
  - **Si asistió + sin registro**: botón verde destacado "Registrar atención clínica" → ficha con modal de nuevo registro pre-cargado vía `?nuevo_para_cita=<id>`
  - **Si asistió + ya tiene registro**: banner verde "✓ Atención ya registrada — Ver detalle"
- ✓ Pre-carga: en `ficha_clinica_view`, si viene `?nuevo_para_cita=<id>` se prepara `nueva_cita_data` y el template abre el modal automáticamente con servicio, fecha, profesional pre-llenados

#### 🎨 Unificación visual del proyecto
- ✓ **Tipografía de stats unificada** al patrón del dashboard:
  - Antes: `var(--font-display)` (Fraunces serif) en stats de profesionales/proveedores/categorías/descuentos/pacientes
  - Ahora: `var(--font-body)` (DM Sans) consistente — coincide con el dashboard
  - Especificación: `font-size: 1.8rem; font-weight: 300; letter-spacing: -0.02em`
- ✓ **Patrón de stats unificado** entre secciones: `.stats-mini` + `.stat-mini` + `.stat-mini-label` + `.stat-mini-value`
- ✓ **Modal pattern unificado**: `.modal-overlay.active` + `.modal-content` (consistente con proveedores)
- ✓ Botón "+ Nuevo paciente" ahora en `card-header` con `.filters-bar` dentro del card
- ✓ Variable `--font-display` (Fraunces) sigue disponible pero no se usa en stats

#### 📐 Polish de formato (ficha del paciente)
- ✓ Filtro nuevo `|rut` en `clinica_tags.py`: `25970622-K` → `25.970.622-K`
- ✓ Filtro `|pesos` ahora usado en: total gastado, montos del historial
- ✓ RUT debajo del nombre en ficha: más grande (0.95rem), peso 600, fondo pill gris claro
- ✓ Próxima cita: formato "Martes 16 de junio" (`l j \d\e F`|capfirst) + nombre completo del profesional
- ✓ Lista de pacientes: RUT también con formato

#### 🎨 Suavizar colores (botón "Pagar total")
- ✓ `.btn-success` en `base.html` actualizado con colores explícitos más suaves
- ✓ Override específico por ID en `agenda.html` con `!important` para `#md-btn-pago-total` y `#md-btn-pago-saldo`:
  - bg `#eef7f1` (mint suave) + texto `#2e7d55` (verde oscuro) + font-weight 600

### Sesión anterior (23 mayo 2026) — UX Agenda + Profesionales
- ✓ Auto-formato de RUT en `editar_profesional.html`
- ✓ Nombres de profesionales responsive en el header de agenda (wrap a 2 líneas)
- ✓ Botón "Ver solo este profesional" (icono ojo) en columnas
- ✓ Chip de filtro activo
- ✓ **Vista SEMANAL** cuando hay filtro individual (1 prof × 7 días)
  - Backend branchea entre modo día y modo semana
  - Headers de columna distintos (profesional vs día/fecha)
  - Navegación de 7 en 7 días en modo semana
  - Helper JS `buildAgendaUrl()` preserva filtros

### Sesión anterior — Sistema de Comisiones
- ✓ Modelos: Insumo, ServicioInsumo, EstructuraComision, ComisionCalculada
- ✓ Dos estructuras: SOCIEDAD MIA CARRO (% flexible) y CLINICA MIA SALUD (70/30)
- ✓ Dashboard de comisiones por profesional/mes con desglose
- ✓ Proyector de comisiones (simulador)
- ✓ Sidebar: sección "Ventas y Comisiones"

### Sesión anterior — Descuentos
- ✓ Sistema de autorizaciones de descuentos con email + workflow
- ✓ Vista admin `descuentos_pendientes`
- ✓ Pestaña "Autorizaciones" en dashboard
- ✓ Sidebar badge contador

### Base previa
- ✓ Modelos con validaciones
- ✓ Agenda rediseñada tipo Google Calendar (mayo 2026)
- ✓ Modal de nueva cita + detalle de cita
- ✓ Indicador de pago (P/A) + colores de estado diferenciados
- ✓ Sección de Profesionales con edición integrada
- ✓ Seguimientos con badge en sidebar
- ✓ Admin de Django funcional + Login/logout
- ✓ Email notifications via Django send_mail

---

## 📝 Features pendientes

### 🔴 Prioridad 1 - Próxima sesión

1. **Insumos obligatorios al marcar "Asistió"** ⭐ — última pieza del flujo de cierre de cita
   - Modelo nuevo `InsumoUsadoEnCita` (FK Cita + FK Insumo + cantidad + auditoría)
   - Modal interceptor del cambio de estado a "asistió" (mismo patrón que box):
     - Pre-llenar con `ServicioInsumo` del servicio
     - Recepción ajusta cantidades reales y confirma
     - Backend valida que haya al menos 1 insumo confirmado
     - UX consistente con la validación de box (rojo, scroll, focus)
   - Decremento automático de stock con reversión en cancelada
   - Admin override permitido para testing
   - **El patrón UX ya está listo** desde la validación de box — solo replicar
   - Detalle completo en `TAREAS.md`

### 🔴 Prioridad 1.5 - Core (backend listo, falta HTML)
- `templates/core/horarios.html` — view `horarios_view` + URLs ya registradas
- `templates/core/servicios.html` — view `servicios_view` + URLs ya registradas
- `templates/core/usuarios.html` — view `usuarios_view` + URLs ya registradas

### 🟠 Prioridad 2 - Conversado y aprobado

- **Google + Microsoft OAuth (django-allauth)**:
  - Allowlist obligatorio (el admin pre-registra emails que pueden hacer login)
  - Soporta Google (Workspace y Gmail gratuito) + Microsoft (Hotmail/Outlook)
  - Botones en `login.html` además del fallback email/password
  - Requiere crear proyecto en Google Cloud Console + obtener credentials
  - HTTPS requerido en producción (en dev funciona con localhost)

- **Consentimiento de paciente para datos clínicos** (Ley 19.628 / 21.719):
  - Checkbox + fecha + IP en primer acceso a ficha clínica
  - Botón "Exportar mi ficha" (derecho de acceso)
  - Versión MVP actual NO incluye este paso

- **Asignación M2M de profesionales/servicios a los boxes precargados**:
  - Los 11 boxes ya están en BD con descripciones detalladas
  - Falta que la admin entre a `/boxes/<id>/editar/` y vincule los profesionales y servicios reales (los M2M vienen vacíos)
  - Cuando estén poblados, el dropdown de box al crear cita podría auto-sugerir según prof+servicio (mejora futura)

### 🟡 Prioridad 3 - Admin & Reportes
- Dashboard mejorado con gráficos (recaudación, servicios populares)
- Reportes exportables (Excel, PDF)
- Integración Google Sheets (backup administrativo)

### 🟢 Prioridad 4 - Polish identificado pero no urgente
- Overlay explícito "Profesional no disponible HH:MM – HH:MM" en franjas no laborales de vista semanal
- Auto-formato de RUT también en formulario de Pacientes (consistencia con Profesionales y Proveedores)
- Eliminar función `formatearFecha` huérfana en `agenda.html` (no se usa post-refactor de Flatpickr)
- Suavizar otros colores intensos: rojo del saldo pendiente (cumple función de alerta, discutible)

---

## 🎨 Estilo y convenciones

**NO CAMBIAR**: estructura general del sidebar oscuro (base.html)
**Colores principales**: definidos como CSS variables en base.html
- `--accent: #4ea17f` (verde principal)
- `--accent-light: #e6f4ee` (verde muy suave)
- `--accent-hover: #3d8468` (verde oscuro)
- `--font-body: 'DM Sans', sans-serif` (default para todo)
- `--font-display: 'Fraunces', serif` (disponible pero no usado en stats)

**Templates**: en carpeta `/templates/core/`
**JS**: Vanilla JS, sin frameworks. Flatpickr es la única dep externa (para datepickers)
**Patrón de stats**: `.stats-mini` > `.stat-mini` > `.stat-mini-label` + `.stat-mini-value`
**Patrón de modales**: `.modal-overlay.active` + `.modal-content` + `.modal-buttons` (botones .btn-secondary y .btn-primary)
**Patrón de tabla list**: `.{seccion}-row-header` + `.{seccion}-row` (ver pacientes.html, proveedores.html)
**Filtros disponibles** en `clinica_tags.py`:
- `{{ valor|pesos }}` → `$45.000`
- `{{ "25970622-K"|rut }}` → `25.970.622-K`

---

## 🔐 Restricciones de desarrollo

⚠️ **EVITAR MODIFICAR**:
- `core/utils.py` (solo lectura — funciones de cálculo de agenda)
- `core/models.py` (cambios SOLO si inevitables; siempre con migración + documentar)

✅ **Permitido**:
- Crear vistas (views.py)
- Crear templates
- Crear JS en static/
- Migrations (cuando se agregan modelos o campos)
- Modificar templatetags (clinica_tags.py)

---

## 🔒 Notas de seguridad (Ficha clínica)

**Implementado a nivel de código**:
- ✅ HTTPS no requerido para fotos (van por endpoint Django auth-protected)
- ✅ `@login_required` en todos los endpoints
- ✅ Permisos por rol (staff vs profesional vs creador)
- ✅ Audit log automático (quién, qué, cuándo, IP)
- ✅ Validación de archivos: tipo (JPG/PNG/WEBP/HEIC) + tamaño (≤10 MB)
- ✅ Borrado físico de archivos al eliminar fotos
- ✅ Fotos servidas vía `FileResponse` con auth check (no MEDIA_URL directo)

**Pendiente a nivel de deployment** (NO se puede hacer solo en código):
- ⏳ HTTPS obligatorio en producción
- ⏳ Encriptación en reposo (SQLite no encripta; pasar a PostgreSQL + cifrado)
- ⏳ Backups encriptados
- ⏳ Firma de consentimiento del paciente (definir formato legal con abogado)

---

## 🚀 Deployment

**Actual**: SQLite en desarrollo
**Recomendado para producción**: Django + VPS con PostgreSQL + SSL (Heroku, Railway, DigitalOcean)
**NO ahora**: Firebase (mejor después, si escalas a múltiples clínicas)

---

## 📌 Notas para sesiones futuras

- El proyecto usa `LANGUAGE_CODE = 'es-cl'` y `TIME_ZONE = 'America/Santiago'`
- Para hora chilena en JS: `Intl.DateTimeFormat('en-GB', { timeZone: 'America/Santiago', hour: '2-digit', minute: '2-digit', hour12: false })`
- Cuando pases data Python → JS: usa SIEMPRE `{{ var|json_script:"id" }}` + `JSON.parse(document.getElementById('id').textContent)`. NO uses `|escapejs|stringformat` (rompe con `%` en strings).
- Cuando accedas a `OneToOneField` inverso: usa `try/except DoesNotExist` o `hasattr` con cuidado.
- **Última migración**: 0029_seed_boxes_iniciales (precarga 11 boxes desde documento real)
- **Para correr el server**: SIEMPRE activar el venv primero (`.venv\Scripts\Activate.ps1`) o usar `.venv\Scripts\python.exe manage.py runserver`. Sin venv da error de Pillow (los `ImageField` necesitan la lib instalada solo en `.venv`).
- Para `ImageField` se requiere `Pillow` instalado (`pip install Pillow`)
- Para servir media en dev: actualmente las fotos clínicas se sirven vía vista Django auth-protected, no necesitan MEDIA_URL configurado en urls.py.
- BD tiene datos de prueba (db.sqlite3 existente)
- **Context processors**: `global_seguimientos_pendientes`, `global_seguimientos_vencidos`, `global_autorizaciones_pendientes`

---

## 🔄 Archivos Clave Modificados (sesión actual — 25 mayo 2026)

### Modelos & migraciones
- **core/models.py**: nuevo modelo `Box` con M2M a Profesional y Servicio + FK opcional `box` en `Cita`
- **core/migrations/0028_box_cita_box_***: migración estructural
- **core/migrations/0029_seed_boxes_iniciales.py**: data migration con los 11 boxes reales

### Vistas
- **core/views.py**:
  - `agenda_view`: nueva queryset `boxes_activos`, cruza con `HorarioProfesional` para marcar bloques de descanso con `estado='descanso'`, separa render en `slots_render` (clicables) y `descansos_render` (no clicables)
  - `crear_cita`: acepta `box` desde POST, detecta doble-booking, emite warning sin bloquear
  - `detalle_cita` (JSON): expone `box_id` y `box_nombre`
  - `actualizar_estado_cita`: valida que cita tenga box al cambiar a "asistio" — retorna `{ error, requiere_box: true }` con HTTP 400
  - **6 vistas nuevas para Box**: `boxes_view`, `crear_box`, `editar_box`, `toggle_box`, `eliminar_box`, `actualizar_box_cita`
  - Helper `_detectar_doble_booking_box()` (considera duración del servicio para overlap)
  - **Bug fix**: eliminada definición duplicada de `descuentos_pendientes_view` (sobrescribía a la real)
  - Mejora: `descuentos_pendientes_view` calcula `monto_total` con `Sum()`

### URLs
- **config/urls.py**: 6 rutas para boxes (`/boxes/`, crear, editar, toggle, eliminar) + `/citas/<id>/box/` (AJAX update)

### Templates
- **templates/core/boxes.html** (NEW): lista de boxes con multi-select buscador en vivo para profesionales y servicios
- **templates/core/base.html**: link "Boxes" en sidebar grupo Configuración
- **templates/core/agenda.html**:
  - Modal "Nueva cita": campo Box (opcional) en grid 2-col junto a Profesional
  - Modal detalle: nueva sección "Box de atención" con dropdown auto-guardado (AJAX)
  - JS `actualizarBoxCita()` y `mostrarErrorRequiereBox()` con UX rojo + scroll + focus
  - Nuevo CSS `.cal-descanso` con rayado diagonal y cursor not-allowed para colación
  - Render: `descansos_render` separado de `slots_render` (no clicables)
- **templates/core/descuentos_pendientes.html**: load `clinica_tags`, monto total con filtro `|pesos` reemplaza el `|sum` que no existía

---

## 🔄 Archivos Modificados (sesión anterior — 23-24 mayo 2026)

### Modelos & migraciones
- **core/models.py**: agregados 4 modelos (FichaClinicaPaciente, RegistroAtencion, FotoEvolucion, AuditLogFicha) + 2 campos en RegistroAtencion (servicio FK, aparatologia)
- **core/migrations/0026_***: ficha clínica (4 modelos)
- **core/migrations/0027_***: servicio + aparatologia en RegistroAtencion

### Vistas
- **core/views.py**:
  - `agenda_view`: nueva queryset `todos_profesionales`, integra `profesional_id` y datos para modal de nueva cita
  - `crear_cita`: rama `modo_paciente=nuevo` que crea Paciente con `full_clean()`, reusa por RUT si existe, mejor manejo de ValidationError (`message_dict`)
  - `detalle_cita` (JSON): expone `paciente_id`, `servicio_id`, `tiene_registro_atencion`, `registro_atencion_id`
  - **Pacientes** (6 vistas nuevas): `pacientes_view`, `paciente_detalle_view`, `crear_paciente`, `editar_paciente`, `toggle_paciente`, `reclasificar_paciente`
  - Helper: `_calcular_tipo_cliente()`
  - **Ficha clínica** (8 vistas nuevas): `ficha_clinica_view`, `guardar_antecedentes`, `crear_registro_atencion`, `editar_registro_atencion`, `eliminar_registro_atencion`, `subir_foto_evolucion`, `editar_foto_evolucion`, `eliminar_foto_evolucion`, `servir_foto_evolucion`
  - Helpers: `_get_client_ip`, `_log_ficha`, `_puede_ver_ficha`, `_puede_editar_registro`

### URLs
- **config/urls.py**: agregadas rutas para pacientes (6) + ficha clínica (8)

### Templates
- **templates/core/pacientes.html** (NEW): lista con stats, búsqueda, filtros, cumpleaños, modal de nuevo paciente
- **templates/core/paciente_detalle.html** (NEW): ficha individual con KPIs, historial, próxima cita, edición inline
- **templates/core/ficha_clinica.html** (NEW): ficha clínica completa con antecedentes, timeline, galería, audit
- **templates/core/base.html**:
  - Sidebar: link "Base de pacientes"
  - `.btn-success` colores suavizados
- **templates/core/agenda.html**:
  - Modal nueva cita: fecha editable (Flatpickr), hora editable (default Chile time), profesional editable, "+ Nuevo cliente" inline con form completo
  - Modal detalle cita: 3 CTAs contextuales (Ficha clínica / Registrar atención / Ya registrada)
  - Override de `.btn-success` con `!important` para botones de pago
  - Fix timezone en mini-cal (`new Date(y, m-1, d)` en vez de `new Date(string)`)
- **templates/core/profesionales.html, proveedores.html, categorias.html, descuentos_pendientes.html**: tipografía de stats unificada (DM Sans en vez de Fraunces)

### Filtros
- **core/templatetags/clinica_tags.py**: agregado filtro `|rut` para formato chileno (25.970.622-K)

---

## 🔗 Recursos clave
- **TAREAS.md**: Feature roadmap detallado
- **models.py**: ~14 modelos, 27 migraciones
- **templates/core/**: ~25 templates con estilo unificado
- **clinica_tags.py**: filtros `|pesos` y `|rut`
