from datetime import date
from .models import SeguimientoPaciente


def datos_globales(request):
    if not request.user.is_authenticated:
        return {}
    hoy = date.today()
    pendientes = SeguimientoPaciente.objects.filter(estado="pendiente")
    return {
        "global_seguimientos_pendientes": pendientes.count(),
        "global_seguimientos_vencidos": pendientes.filter(fecha_objetivo__lt=hoy).count(),
    }
