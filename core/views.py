from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404

from .models import Profesional, Servicio, SeguimientoPaciente
from .utils import obtener_agenda_completa


def agenda_view(request):
    fecha_param = request.GET.get('fecha')
    servicio_id = request.GET.get('servicio')

    fecha = date.today()

    if fecha_param:
        fecha = datetime.strptime(fecha_param, "%Y-%m-%d").date()

    profesionales = Profesional.objects.filter(activo=True)
    servicios = Servicio.objects.filter(activo=True)

    agenda_general = []
    horas_base = None

    for profesional in profesionales:
        agenda = obtener_agenda_completa(profesional, fecha)

        if not horas_base:
            horas_base = [b["hora"] for b in agenda]

        agenda_dict = {b["hora"]: b for b in agenda}

        agenda_general.append({
            "profesional": profesional,
            "agenda": agenda_dict
        })

    context = {
        "fecha": fecha,
        "horas": horas_base,
        "agenda_general": agenda_general,
        "servicio_id": servicio_id,
        "servicios": servicios,
    }

    return render(request, "agenda.html", context)


def seguimientos_view(request):
    hoy = date.today()

    seguimientos = SeguimientoPaciente.objects.filter(
        estado='pendiente'
    ).order_by('fecha_objetivo')

    context = {
        "hoy": hoy,
        "seguimientos": seguimientos,
    }

    return render(request, "seguimientos.html", context)


def marcar_seguimiento_contactado(request, seguimiento_id):
    seguimiento = get_object_or_404(SeguimientoPaciente, id=seguimiento_id)

    if request.method == "POST":
        seguimiento.estado = "contactado"
        seguimiento.save()

    return redirect("seguimientos")