# Script simple para agregar datos de prueba
# Ejecutar con: cat seed_simple.py | python manage.py shell

from datetime import date, time, timedelta
from core.models import (
    Profesional, HorarioProfesional, Sucursal, Paciente,
    Servicio, Cita, Empresa, UnidadNegocio, CategoriaServicio
)

# Obtener datos existentes
empresa = Empresa.objects.first()
sucursal = Sucursal.objects.filter(empresa=empresa).first()

print("Creando profesionales...")

# Profesional 2
prof2, _ = Profesional.objects.get_or_create(
    rut="11.222.333-4",
    defaults={
        "empresa": empresa,
        "sucursal_principal": sucursal,
        "nombres": "Maria",
        "apellidos": "Gonzalez",
        "nombre_publico": "Dra. Maria",
        "telefono": "+56912111111",
        "activo": True,
    }
)
print(f"  Profesional: {prof2.nombres}")

# Profesional 3
prof3, _ = Profesional.objects.get_or_create(
    rut="22.333.444-5",
    defaults={
        "empresa": empresa,
        "sucursal_principal": sucursal,
        "nombres": "Carlos",
        "apellidos": "Rodriguez",
        "nombre_publico": "Dr. Carlos",
        "telefono": "+56912222222",
        "activo": True,
    }
)
print(f"  Profesional: {prof3.nombres}")

# Profesional 4
prof4, _ = Profesional.objects.get_or_create(
    rut="33.444.555-6",
    defaults={
        "empresa": empresa,
        "sucursal_principal": sucursal,
        "nombres": "Andrea",
        "apellidos": "Martinez",
        "nombre_publico": "Dra. Andrea",
        "telefono": "+56912333333",
        "activo": True,
    }
)
print(f"  Profesional: {prof4.nombres}")

profs = [prof2, prof3, prof4]

print("\nConfigurando horarios...")
horarios_config = [
    (0, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),
    (1, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),
    (2, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),
    (3, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),
    (4, True, time(9, 0), time(18, 0), True, time(13, 0), time(14, 0)),
    (5, False, None, None, False, None, None),
    (6, False, None, None, False, None, None),
]

for prof in profs:
    for dia, activo, h_inicio, h_fin, tiene_descanso, des_inicio, des_fin in horarios_config:
        HorarioProfesional.objects.get_or_create(
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

print("Configurando servicios...")
unidad, _ = UnidadNegocio.objects.get_or_create(
    empresa=empresa,
    nombre="Tratamientos",
    defaults={"tipo_impuesto": "exento"}
)

categoria, _ = CategoriaServicio.objects.get_or_create(
    unidad_negocio=unidad,
    nombre="Inyectables"
)

servicios = []
for nom, dur, precio in [("Botox", 30, 150000), ("Relleno", 45, 200000)]:
    srv, _ = Servicio.objects.get_or_create(
        empresa=empresa,
        nombre=nom,
        defaults={
            "unidad_negocio": unidad,
            "categoria": categoria,
            "duracion_minutos": dur,
            "precio": precio,
            "requiere_seguimiento": True,
            "dias_seguimiento": 90,
            "activo": True,
        }
    )
    srv.profesionales.set(profs)
    servicios.append(srv)
    print(f"  Servicio: {nom}")

print("\nCreando citas de prueba...")
hoy = date.today()
dias_hasta_lunes = (7 - hoy.weekday()) % 7
if dias_hasta_lunes == 0:
    dias_hasta_lunes = 7
fecha_lunes = hoy + timedelta(days=dias_hasta_lunes)

citas = [
    (0, time(10, 0), prof2, servicios[0], 75000),
    (0, time(11, 0), prof3, servicios[1], 100000),
    (1, time(14, 30), prof4, servicios[0], 0),
]

for offset, hora, prof, serv, pagado in citas:
    fecha = fecha_lunes + timedelta(days=offset)
    pac = Paciente.objects.filter(activo=True).first()
    if pac:
        Cita.objects.get_or_create(
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

print("\n✓ Datos agregados!")
