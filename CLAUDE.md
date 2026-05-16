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
- **SeguimientoPaciente**: Contactos post-cita (para servicios que requieren follow-up)
  - Estados: pendiente, contactado, agendado, descartado

---

## ✅ Features completadas
- ✓ Modelos con validaciones
- ✓ Control de horarios profesionales y validación de citas
- ✓ Sistema de pagos con saldo pendiente
- ✓ Seguimientos automáticos (cuando cita pasa a "asistió" y servicio requiere seguimiento)
- ✓ Admin de Django funcional
- ✓ Login/logout con autenticación Django
- ✓ Sidebar con badge de seguimientos pendientes/vencidos
- ✓ **Agenda rediseñada** (mayo 2026) — posicionamiento absoluto tipo Google Calendar, bloques proporcionales a duración, indicador de hora actual, scroll automático
- ✓ **Nueva cita desde agenda** — modal con búsqueda de paciente, selector de servicio, validaciones
- ✓ **Seguimientos** — vista completa con botones contactado/agendado/descartado, contador en sidebar
- ✓ Backend vistas y URLs listos para: Horarios profesionales, Servicios UI, Usuarios y roles

---

## 📝 Features pendientes

### 🔴 Prioridad 1 - Core (siguiente a implementar)
1. **Modal de cita** (clic en tarjeta de cita existente en agenda)
   - Las views AJAX ya existen: `detalle_cita`, `actualizar_estado_cita`, `registrar_pago_cita`, `reagendar_cita`
   - Falta: modal HTML en `agenda.html` + JS que llama a esas views
   - Ver detalles completos, cambiar estado, registrar pago, reagendar

2. **Templates pendientes** (backend ya listo, solo falta el HTML)
   - `templates/core/horarios.html` — view `horarios_view` + URLs ya registradas
   - `templates/core/servicios.html` — view `servicios_view` + URLs ya registradas
   - `templates/core/usuarios.html` — view `usuarios_view` + URLs ya registradas

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
- Las migraciones están al día (0013 es la última)
- BD tiene datos de prueba (db.sqlite3 existente)
- Pía trabaja en Cursor + Claude Code para desarrollo rápido

---

## 🔗 Recursos clave
- **TAREAS.md**: Feature roadmap detallado
- **models.py**: 6 modelos principales, 13 migraciones
- **templates/**: Estructura existente con sidebar
