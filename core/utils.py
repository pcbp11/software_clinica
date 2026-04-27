from datetime import datetime, timedelta

from .models import HorarioProfesional, Cita


def generar_bloques(hora_inicio, hora_fin, duracion_minutos=15):
    bloques = []

    inicio = datetime.combine(datetime.today(), hora_inicio)
    fin = datetime.combine(datetime.today(), hora_fin)

    while inicio < fin:
        bloques.append(inicio.time())
        inicio += timedelta(minutes=duracion_minutos)

    return bloques


def obtener_horas_disponibles(profesional, fecha, duracion_servicio):
    dia_semana = fecha.weekday()

    horario = HorarioProfesional.objects.filter(
        profesional=profesional,
        dia_semana=dia_semana,
        activo=True
    ).first()

    if not horario:
        return []

    bloques = generar_bloques(horario.hora_inicio, horario.hora_fin)

    citas = Cita.objects.filter(
        profesional=profesional,
        fecha=fecha
    ).exclude(
        estado__in=['cancelada', 'reprogramada']
    )

    bloques_disponibles = []

    for bloque in bloques:
        inicio = datetime.combine(fecha, bloque)
        fin = inicio + timedelta(minutes=duracion_servicio)

        conflicto = False

        for cita in citas:
            if not cita.hora_fin:
                continue

            cita_inicio = datetime.combine(fecha, cita.hora_inicio)
            cita_fin = datetime.combine(fecha, cita.hora_fin)

            if inicio < cita_fin and fin > cita_inicio:
                conflicto = True
                break

        if not conflicto:
            bloques_disponibles.append(bloque)

    return bloques_disponibles


# 🔥 ESTA ES LA NUEVA FUNCIÓN (LA QUE FALTABA)
def obtener_agenda_completa(profesional, fecha):
    dia_semana = fecha.weekday()

    horario = HorarioProfesional.objects.filter(
        profesional=profesional,
        dia_semana=dia_semana,
        activo=True
    ).first()

    if not horario:
        return []

    bloques = generar_bloques(horario.hora_inicio, horario.hora_fin)

    citas = Cita.objects.filter(
        profesional=profesional,
        fecha=fecha
    ).exclude(
        estado__in=['cancelada', 'reprogramada']
    )

    agenda = []

    for bloque in bloques:
        estado = "disponible"
        cita_encontrada = None

        for cita in citas:
            if not cita.hora_fin:
                continue

            if cita.hora_inicio <= bloque < cita.hora_fin:
                cita_encontrada = cita

                if cita.estado_pago == 'pagado':
                    estado = "pagado"
                elif cita.estado_pago == 'abonado':
                    estado = "abonado"
                else:
                    estado = "ocupado"

                break

        agenda.append({
            "hora": bloque,
            "estado": estado,
            "cita": cita_encontrada
        })

    return agenda