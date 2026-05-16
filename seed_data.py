# -*- coding: utf-8 -*-
"""
Script para agregar datos de prueba a la clínica.
Ejecutar con: cat seed_data.py | python manage.py shell
"""

from datetime import date, time, timedelta
from core.models import Profesional, HorarioProfesional, Sucursal, Paciente, Servicio, Cita, Empresa

# ──────────────────────────────────────────────────────────────────────────────
# 1. OBTENER O CREAR SUCURSAL Y EMPRESA
# ──────────────────────────────────────────────────────────────────────────────

empresa = Empresa.objects.first()
if not empresa:
    empresa = Empresa.objects.create(
        nombre="Clínica Mía Salud",
        rut="12.345.678-9",
        telefono="+56912345678",
        color_principal="#2E8B8B",
        color_secundario="#F5F5F5"
    )
    print(f"✓ Empresa creada: {empresa.nombre}")
else:
    print(f"✓ Usando empresa existente: {empresa.nombre}")

sucursal = Sucursal.objects.filter(empresa=empresa).first()
if not sucursal:
    sucursal = Sucursal.objects.create(
        empresa=empresa,
        nombre="Sucursal La Serena",
        direccion="Av. Francisco de Aguirre 123",
        ciudad="La Serena",
        telefono="+56912345678"
    )
    print(f"✓ Sucursal creada: {sucursal.nombre}")
else:
    print(f"✓ Usando sucursal existente: {sucursal.nombre}")

# ──────────────────────────────────────────────────────────────────────────────
# 2. CREAR PROFESIONALES ADICIONALES
# ──────────────────────────────────────────────────────────────────────────────

profesionales_data = [
    {
        "nombres": "María",
        "apellidos": "González López",
        "rut": "11.222.333-4",
        "nombre_publico": "Dra. María González",
        "telefono": "+56912111111",
    },
    {
        "nombres": "Carlos",
        "apellidos": "Rodríguez Pérez",
        "rut": "22.333.444-5",
        "nombre_publico": "Dr. Carlos Rodríguez",
        "telefono": "+56912222222",
    },
    {
        "nombres": "Andrea",
        "apellidos": "Martínez Silva",
        "rut": "33.444.555-6",
        "nombre_publico": "Dra. Andrea Martínez",
        "telefono": "+56912333333",
    }
]

profesionales_creados = []
for prof_data in profesionales_data:
    prof, created = Profesional.objects.get_or_create(
        rut=prof_data["rut"],
        defaults={
            "empresa": empresa,
            "sucursal_principal": sucursal,
            "nombres": prof_data["nombres"],
            "apellidos": prof_data["apellidos"],
            "nombre_publico": prof_data["nombre_publico"],
            "telefono": prof_data["telefono"],
            "activo": True,
        }
    )
    if created:
        print(f"✓ Profesional creado: {prof.nombre_publico}")
    else:
        print(f"✓ Profesional existente: {prof.nombre_publico}")
    profesionales_creados.append(prof)

# ──────────────────────────────────────────────────────────────────────────────
# 3. CONFIGURAR HORARIOS PARA PROFESIONALES
# ──────────────────────────────────────────────────────────────────────────────

# Horarios: Lunes a Viernes 09:00-18:00, con descanso 13:00-14:00
horarios_config = [
    # Lunes (0) a Viernes (4): 09:00-18:00 con descanso 13:00-14:00
    (0, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Lunes
    (1, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Martes
    (2, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Miércoles
    (3, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Jueves
    (4, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Viernes
    (5, False, None, None, False, None, None),                             # Sábado - No atiende
    (6, False, None, None, False, None, None),                             # Domingo - No atiende
]

for prof in profesionales_creados:
    for dia, activo, h_inicio, h_fin, tiene_descanso, des_inicio, des_fin in horarios_config:
        horario, created = HorarioProfesional.objects.get_or_create(
            profesional=prof,
            dia_semana=dia,
            defaults={
                "activo": activo,
                "hora_inicio": h_inicio,
                "hora_fin": h_fin,
                "tiene_descanso": tiene_descanso,
                "inicio_descanso": des_inicio,
                "fin_descanso": des_fin,
            }
        )
        if created:
            estado = "ACTIVO" if activo else "INACTIVO"
            print(f"  ✓ {prof.nombres}: {['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'][dia]} - {estado}")

# ──────────────────────────────────────────────────────────────────────────────
# 4. CREAR SERVICIOS (si no existen)
# ──────────────────────────────────────────────────────────────────────────────

from core.models import UnidadNegocio, CategoriaServicio

unidad, _ = UnidadNegocio.objects.get_or_create(
    empresa=empresa,
    nombre="Tratamientos Estéticos",
    defaults={"tipo_impuesto": "exento"}
)

categoria, _ = CategoriaServicio.objects.get_or_create(
    unidad_negocio=unidad,
    nombre="Inyectables"
)

servicios_data = [
    {"nombre": "Botox", "duracion": 30, "precio": 150000, "seguimiento": True, "dias_seg": 90},
    {"nombre": "Relleno de labios", "duracion": 45, "precio": 200000, "seguimiento": True, "dias_seg": 60},
    {"nombre": "Consulta inicial", "duracion": 30, "precio": 50000, "seguimiento": False, "dias_seg": None},
]

servicios_creados = []
for srv_data in servicios_data:
    srv, created = Servicio.objects.get_or_create(
        empresa=empresa,
        nombre=srv_data["nombre"],
        defaults={
            "unidad_negocio": unidad,
            "categoria": categoria,
            "duracion_minutos": srv_data["duracion"],
            "precio": srv_data["precio"],
            "requiere_seguimiento": srv_data["seguimiento"],
            "dias_seguimiento": srv_data["dias_seg"],
            "activo": True,
        }
    )
    if created:
        print(f"✓ Servicio creado: {srv.nombre}")
    servicios_creados.append(srv)
    # Asociar profesionales al servicio
    srv.profesionales.set(profesionales_creados)

# ──────────────────────────────────────────────────────────────────────────────
# 5. CREAR PACIENTES DE PRUEBA
# ──────────────────────────────────────────────────────────────────────────────

pacientes_data = [
    {"nombres": "Carolina", "apellidos": "Luco Silva", "rut": "88.999.000-1", "telefono": "+56987654321"},
    {"nombres": "Javiera", "apellidos": "Varas Vargas", "rut": "77.888.999-2", "telefono": "+56987654322"},
    {"nombres": "Nora Isabel", "apellidos": "León Robledo", "rut": "66.777.888-3", "telefono": "+56987654323"},
    {"nombres": "Roxana", "apellidos": "Goyoso Saez", "rut": "55.666.777-4", "telefono": "+56987654324"},
]

pacientes_creados = []
for pac_data in pacientes_data:
    pac, created = Paciente.objects.get_or_create(
        rut=pac_data["rut"],
        defaults={
            "sucursal": sucursal,
            "nombres": pac_data["nombres"],
            "apellidos": pac_data["apellidos"],
            "telefono": pac_data["telefono"],
            "tipo_cliente": "recurrente",
            "activo": True,
        }
    )
    if created:
        print(f"✓ Paciente creado: {pac.nombres} {pac.apellidos}")
    pacientes_creados.append(pac)

# ──────────────────────────────────────────────────────────────────────────────
# 6. CREAR CITAS DE PRUEBA PARA ESTA SEMANA
# ──────────────────────────────────────────────────────────────────────────────

hoy = date.today()
# Encontrar el próximo lunes
dias_hasta_lunes = (7 - hoy.weekday()) % 7
if dias_hasta_lunes == 0:
    dias_hasta_lunes = 7
fecha_lunes = hoy + timedelta(days=dias_hasta_lunes)

citas_data = [
    {"fecha_offset": 0, "hora": time(10, 0), "prof_idx": 0, "pac_idx": 0, "srv_idx": 0, "estado": "confirmado", "pago": 75000},
    {"fecha_offset": 0, "hora": time(10, 30), "prof_idx": 1, "pac_idx": 1, "srv_idx": 1, "estado": "confirmado", "pago": 100000},
    {"fecha_offset": 0, "hora": time(14, 30), "prof_idx": 2, "pac_idx": 2, "srv_idx": 0, "estado": "en_espera", "pago": 0},
    {"fecha_offset": 1, "hora": time(11, 0), "prof_idx": 0, "pac_idx": 3, "srv_idx": 1, "estado": "reservado", "pago": 0},
    {"fecha_offset": 2, "hora": time(15, 0), "prof_idx": 1, "pac_idx": 0, "srv_idx": 2, "estado": "confirmado", "pago": 50000},
]

for cita_data in citas_data:
    fecha = fecha_lunes + timedelta(days=cita_data["fecha_offset"])
    cita, created = Cita.objects.get_or_create(
        sucursal=sucursal,
        paciente=pacientes_creados[cita_data["pac_idx"]],
        profesional=profesionales_creados[cita_data["prof_idx"]],
        servicio=servicios_creados[cita_data["srv_idx"]],
        fecha=fecha,
        hora_inicio=cita_data["hora"],
        defaults={
            "estado": cita_data["estado"],
            "monto_total": servicios_creados[cita_data["srv_idx"]].precio,
            "monto_pagado": cita_data["pago"],
        }
    )
    if created:
        print(f"✓ Cita creada: {fecha.strftime('%d/%m')} {cita_data['hora'].strftime('%H:%M')} - {cita.paciente.nombres}")

print("\n✨ ¡Datos de prueba agregados correctamente!")
print(f"📅 Próximas citas desde: {fecha_lunes.strftime('%d/%m/%Y')}")
