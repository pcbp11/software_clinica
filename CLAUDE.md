# 🏥 Software Clínica Médica Estética - Documentación

## 📋 Descripción general
Sistema de gestión integral para una Clínica Médica Estética ubicada en La Serena. Reemplaza/complementa Agenda Pro (muy limitado) y sistemas administrativos en Google Sheets.

**Estado**: Desarrollo activo  
**Stack**: Django 4.x + SQLite (dev) + HTML/CSS/JS  
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
│   ├── models.py       # ⚠️ NO MODIFICAR (solo lectura)
│   ├── views.py
│   ├── admin.py
│   ├── utils.py        # ⚠️ NO MODIFICAR (solo lectura)
│   ├── context_processors.py
│   ├── migrations/
│   ├── static/js/
│   └── templatetags/
├── templates/          # HTML - mantener estilo actual (sidebar oscuro)
├── static/             # CSS, JS compartido
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
- **Paciente**: Clientes (RUT, contacto, tipo: nuevo/recurrente/perdido)
- **Profesional**: Médicos/esteticistas (RUT, nombre_publico, foto, certificado)
- **HorarioProfesional**: Disponibilidad por día semana (lunes-domingo, descanso)

### Negocio
- **Servicio**: Procedimientos (nombre, duracion_minutos, precio, profesionales M2M)
- **Cita**: Agendamiento (paciente, profesional, servicio, fecha, hora, estado)
  - Estados: reservado, pendiente, confirmado, en_espera, asistió, no_asistió, cancelada, reprogramada
  - Control de pago: monto_total, monto_pagado, estado_pago
  - Validaciones: respeta horarios del profesional, evita cruces, respeta descansos
- **Pago**: Registro de pagos (efectivo, débito, crédito, transferencia, WebPay)
  - Campos: voucher, boleta (extraídos de observación)
- **SeguimientoPaciente**: Contactos post-cita (para servicios que requieren follow-up)
  - Estados: pendiente, contactado, agendado, descartado
- **Descuento**: Sistema de autorización de descuentos
  - Tipos: porcentaje (%) o valor_fijo ($)
  - Estados: pendiente, aprobado, rechazado
  - Campos: valor, monto_descuento, razon, solicitado_por, autorizado_por, fecha_solicitud, fecha_autorizacion
  - Workflow: Solicitud → Email notificación → Admin aprueba/rechaza → Email confirmación

### Sistema de Comisiones (NUEVO)
- **Insumo**: Productos/materiales con costo de inventario
  - Campos: nombre, codigo_sku, costo_unitario, precio_venta, unidad, cantidad_disponible
  - Margen calculado: (precio_venta - costo) / precio_venta * 100
  - Vinculado a UnidadNegocio

- **ServicioInsumo**: Relación M2M entre Servicio e Insumo
  - Cantidad de insumo utilizado por servicio
  - Costo total calculado automáticamente

- **EstructuraComision**: Define comisión para profesional por unidad de negocio
  - Tipos: porcentaje (%), fijo_por_servicio, sociedad_carro (%), clinica_salud_70_30
  - Campos: tipo_comision, valor_comision, activa, fecha_inicio, fecha_fin
  - Propiedad `vigente`: verifica si está activa en la fecha actual

- **ComisionCalculada**: Registro histórico de comisiones calculadas
  - Agrupa por: profesional, mes_referencia
  - Montos: monto_ingresos_brutos, monto_insumos, monto_descuentos, monto_neto, monto_comision
  - Auditoría: fecha_calculo, actualizado_en

---

## ✅ Features completadas

### Sesión Actual (Mayo 2026) - Sistema de Comisiones
- ✓ Modelos para inventario: **Insumo** (productos con costo), **ServicioInsumo** (relación M2M)
- ✓ Estructura de comisiones: **EstructuraComision** (configurable por profesional y unidad)
- ✓ Cálculo de comisiones: **ComisionCalculada** (registro histórico de cálculos)
- ✓ Cálculo inteligente: fórmula `(ingresos - insumos - descuentos) × porcentaje`
- ✓ Soporte para dos estructuras:
  - **SOCIEDAD MIA CARRO**: Porcentaje flexible (ej: 30%, 40%, etc.)
  - **CLINICA MIA SALUD**: 70/30 split (70% profesional, 30% clínica)
- ✓ Dashboard profesional: vista de comisiones por mes con desglose por servicio
- ✓ Proyector de comisiones: simulador de ganancias según volumen de atenciones
- ✓ Admin Django: gestión completa de estructuras, insumos y comisiones calculadas
- ✓ Sidebar: nueva sección "Ventas y Comisiones" con links a Comisiones y Proyección

### Anterior
- ✓ Modelos con validaciones
- ✓ Control de horarios profesionales y validación de citas
- ✓ Sistema de pagos con saldo pendiente y comprobantes (voucher/boleta)
- ✓ Seguimientos automáticos (cuando cita pasa a "asistió" y servicio requiere seguimiento)
- ✓ Admin de Django funcional
- ✓ Login/logout con autenticación Django
- ✓ Sidebar con badge de seguimientos pendientes/vencidos
- ✓ **Agenda rediseñada** (mayo 2026) — posicionamiento absoluto tipo Google Calendar, bloques proporcionales a duración, indicador de hora actual, scroll automático
- ✓ **Nueva cita desde agenda** — modal con búsqueda de paciente, selector de servicio, validaciones
- ✓ **Detalle de cita en modal** — estados, pago, historial, reagendar
- ✓ **Indicador de pago (P/A)** — P=Pagado (verde), A=Abonado (naranja) en agenda y resumen de cita
- ✓ **Colores de estado diferenciados**:
  - Reservado: Azul claro
  - Confirmado: Calipso/Cyan (azul-turquesa)
  - En espera: Naranja
  - Asistió: Verde oscuro (diferenciado del confirmado)
  - No asistió: Gris
  - Cancelada: Gris opaco
  - Reprogramada: Púrpura
- ✓ **Sección de Profesionales** — gestión integrada de datos, horarios y cuentas
- ✓ **Seguimientos** — vista completa con botones contactado/agendado/descartado, contador en sidebar
- ✓ Backend vistas y URLs listos para: Horarios profesionales, Servicios UI, Usuarios y roles
- ✓ **Sistema de autorizaciones de descuentos** (mayo 2026)
  - Solicitud de descuento en modal de pago (%, o $ fijo)
  - Extracción de voucher/boleta del campo observación
  - Descuentos visibles en modal de cita con estado (⚠️ pendiente, ✓ aprobado)
  - Email notificación a solicitante + admin
  - Vista admin `descuentos_pendientes` para aprobar/rechazar
  - Nueva pestaña "Autorizaciones" en dashboard para ver estado de solicitudes
  - Sidebar badge contador de autorizaciones pendientes
  - Separación clara: Seguimientos (Botox 3m) vs Autorizaciones (descuentos)

---

## 📝 Features pendientes

### 🔴 Prioridad 1 - Core

1. **Templates pendientes** (backend ya listo, solo falta el HTML)
   - `templates/core/horarios.html` — view `horarios_view` + URLs ya registradas
   - `templates/core/servicios.html` — view `servicios_view` + URLs ya registradas
   - `templates/core/usuarios.html` — view `usuarios_view` + URLs ya registradas

### 🟡 Prioridad 2 - Admin & Reportes
- Dashboard mejorado con gráficos (recaudación, servicios populares)
- Reportes exportables (Excel, PDF)
- Integración Google Sheets (backup administrativo)

---

## 🎨 Estilo y convenciones

**NO CAMBIAR**: Mantener estilo actual (base.html con sidebar oscuro)
**Colores**: Definidos en modelo Empresa (color_principal, color_secundario)
**Templates**: En carpeta `/templates`
**JS**: Preferir vanilla JS, minimal (archivo cita_admin.js existente)

---

## 🔐 Restricciones de desarrollo

⚠️ **NUNCA MODIFICAR**:
- `core/models.py` (solo lectura)
- `core/utils.py` (solo lectura)

✅ **Permitido**:
- Crear vistas (views.py)
- Crear templates
- Crear JS en static/
- Migrations (si cambios en modelos son inevitables)

---

## 🚀 Deployment

**Actual**: SQLite en desarrollo  
**Recomendado para producción**: Django + VPS (Heroku, Railway, DigitalOcean)  
**NO ahora**: Firebase (mejor después, si escalas a múltiples clínicas)

---

## 📌 Notas para sesiones futuras

- El proyecto usa `LANGUAGE_CODE = 'es-cl'` y `TIME_ZONE = 'America/Santiago'`
- Google Sheets integración: pendiente (para admin/reportes)
- **Migraciones al día**: 0014 es la última (Descuento model)
- BD tiene datos de prueba (db.sqlite3 existente)
- Pía trabaja en Cursor + Claude Code para desarrollo rápido
- **Context processors**: Agregado `global_autorizaciones_pendientes` para sidebar badge
- **Nueva funcionalidad**: Email notifications via Django send_mail (settings.DEFAULT_FROM_EMAIL)

---

## 🔄 Archivos Clave Modificados (sesión actual)

- **core/views.py**: 
  - `registrar_pago_cita()` — Manejo de descuentos y notificaciones por email
  - `detalle_cita()` — Extracción voucher/boleta y retorno de descuentos
  - `descuentos_pendientes_view()` — Admin view para autorizar descuentos
  - `autorizar_descuento()` — AJAX endpoint para aprobar/rechazar
  - `autorizaciones_view()` (NEW) — Dashboard view para usuario

- **templates/core/agenda.html**:
  - `renderDescuentos()` — Función JS con iconos de estado
  - `renderDetalle()` — Agregado llamada a renderDescuentos()

- **templates/core/autorizaciones.html** (NEW):
  - Vista usuario-facing con tabla de autorizaciones
  - Filtros por pestañas (Todas, Pendientes, Procesadas)
  - Stats cards (Total, Pendientes, Aprobadas)

- **templates/core/base.html**:
  - Agregada sección "Autorizaciones" en sidebar
  - Badge con contador de autorizaciones pendientes

- **core/context_processors.py**:
  - Agregado `global_autorizaciones_pendientes` al contexto global

- **config/urls.py**:
  - Nueva ruta: `path('autorizaciones/', views.autorizaciones_view, name='autorizaciones')`

- **CLAUDE.md** (este archivo):
  - Documentación de sistema de descuentos completado

---

## 🔗 Recursos clave
- **TAREAS.md**: Feature roadmap detallado
- **models.py**: 7 modelos (agregado Descuento), 14 migraciones
- **templates/**: Estructura existente con sidebar + nueva vista autorizaciones.html
