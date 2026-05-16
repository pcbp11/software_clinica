# -*- coding: utf-8 -*-
"""
Script para agregar datos de prueba SIN caracteres especiales
Ejecutar con: cat seed_clean.py | python manage.py shell
"""

from datetime import date, time, timedelta
from core.models import (
    Profesional, HorarioProfesional, Sucursal, Paciente,
    Servicio, Cita, Empresa, UnidadNegocio, CategoriaServicio
)

# Obtener datos existentes
empresa = Empresa.objects.first()
sucursal = Sucursal.objects.filter(empresa=empresa).first()

print("Creando profesionales (nombres sin acentos)...")

# Profesional 1
prof1, created = Profesional.objects.get_or_create(
    rut="11.222.333-4",
    defaults={
        "empresa": empresa,
        "sucursal_principal": sucursal,
        "nombres": "MARIA GONZALEZ LOPEZ",
        "apellidos": "",
        "nombre_publico": "Dra. Maria Gonzalez",
        "telefono": "+56912111111",
        "activo": True,
    }
)
if created:
    print(f"  ✓ Creado: {prof1.nombres}")
else:
    print(f"  ✓ Existe: {prof1.nombres}")

# Profesional 2
prof2, created = Profesional.objects.get_or_create(
    rut="22.333.444-5",
    defaults={
        "empresa": empresa,
        "sucursal_principal": sucursal,
        "nombres": "CARLOS RODRIGUEZ PEREZ",
        "apellidos": "",
        "nombre_publico": "Dr. Carlos Rodriguez",
        "telefono": "+56912222222",
        "activo": True,
    }
)
if created:
    print(f"  ✓ Creado: {prof2.nombres}")
else:
    print(f"  ✓ Existe: {prof2.nombres}")

# Profesional 3
prof3, created = Profesional.objects.get_or_create(
    rut="33.444.555-6",
    defaults={
        "empresa": empresa,
        "sucursal_principal": sucursal,
        "nombres": "ANDREA MARTINEZ SILVA",
        "apellidos": "",
        "nombre_publico": "Dra. Andrea Martinez",
        "telefono": "+56912333333",
        "activo": True,
    }
)
if created:
    print(f"  ✓ Creado: {prof3.nombres}")
else:
    print(f"  ✓ Existe: {prof3.nombres}")

profs = [prof1, prof2, prof3]

print("\nConfigurando horarios (Lunes a Viernes)...")
horarios_config = [
    (0, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Lunes
    (1, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Martes
    (2, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Miercoles
    (3, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Jueves
    (4, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),   # Viernes
    (5, False, None, None, False, None, None),                             # Sabado - No atiende
    (6, False, None, None, False, None, None),                             # Domingo - No atiende
]

dia_nombres = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']

for prof in profs:
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
            estado = "ABIERTO" if activo else "CERRADO"
            print(f"  ✓ {prof.nombres[:20]}: {dia_nombres[dia]:12} - {estado}")

print("\nConfigurando servicios...")
unidad, _ = UnidadNegocio.objects.get_or_create(
    empresa=empresa,
    nombre="Tratamientos Esteticos",
    defaults={"tipo_impuesto": "exento"}
)

categoria, _ = CategoriaServicio.objects.get_or_create(
    unidad_negocio=unidad,
    nombre="Inyectables"
)

servicios = []
servicios_data = [
    ("Botox", 30, 150000),
    ("Relleno de Labios", 45, 200000),
    ("Consulta Inicial", 30, 50000)
]

for nom, dur, precio in servicios_data:
    srv, created = Servicio.objects.get_or_create(
        empresa=empresa,
        nombre=nom,
        defaults={
            "unidad_negocio": unidad,
            "categoria": categoria,
            "duracion_minutos": dur,
            "precio": precio,
            "requiere_seguimiento": True,
            "dias_seguimiento": 90 if "Botox" in nom else 60,
            "activo": True,
        }
    )
    if created:
        print(f"  ✓ Servicio: {nom}")
    srv.profesionales.set(profs)
    servicios.append(srv)

print("\nCreando citas de prueba...")
hoy = date.today()
dias_hasta_lunes = (7 - hoy.weekday()) % 7
if dias_hasta_lunes == 0:
    dias_hasta_lunes = 7
fecha_lunes = hoy + timedelta(days=dias_hasta_lunes)

# Obtener un paciente activo
pac = Paciente.objects.filter(activo=True).first()
if pac:
    citas_data = [
        (0, time(10, 0), prof1, servicios[0], 75000),
        (0, time(10, 30), prof2, servicios[1], 100000),
        (0, time(14, 30), prof3, servicios[0], 0),
        (1, time(11, 0), prof1, servicios[1], 0),
        (2, time(15, 0), prof2, servicios[2], 50000),
    ]

    for offset, hora, prof, serv, pagado in citas_data:
        fecha = fecha_lunes + timedelta(days=offset)
        cita, created = Cita.objects.get_or_create(
            sucursal=sucursal,
            paciente=pac,
            profesional=prof,
            servicio=serv,
            fecha=fecha,
            hora_inicio=hora,
            defaults={
                "estado": "confirmado",
                "monto_total": serv.precio,
                "monto_pagado": pagado,
            }
        )
        if created:
            print(f"  ✓ Cita: {fecha.strftime('%d/%m')} {hora.strftime('%H:%M')} - {prof.nombres[:15]}")

print("\n✨ Datos agregados correctamente!")
print(f"📅 Proximas citas desde: {fecha_lunes.strftime('%d/%m/%Y')}")
