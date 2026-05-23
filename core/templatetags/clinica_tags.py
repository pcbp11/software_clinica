from django import template

register = template.Library()


@register.filter
def pesos(value):
    """Formatea como pesos chilenos: $45.000"""
    try:
        value = int(value) if value is not None else 0
        return "${:,}".format(value).replace(",", ".")
    except (ValueError, TypeError):
        return "$0"


@register.filter
def rut(value):
    """Formatea un RUT chileno: 25970622-K → 25.970.622-K

    Acepta valores con o sin guión, con o sin puntos. Normaliza a
    formato canónico con puntos de miles y guión antes del dígito
    verificador.
    """
    if not value:
        return ""
    # Limpiar: dejar solo dígitos y K
    limpio = ''.join(c for c in str(value).upper() if c.isdigit() or c == 'K')
    if len(limpio) < 2:
        return value  # No es un RUT válido, devolver tal cual
    cuerpo, dv = limpio[:-1], limpio[-1]
    # Insertar puntos cada 3 dígitos desde la derecha del cuerpo
    cuerpo_inverso = cuerpo[::-1]
    bloques = [cuerpo_inverso[i:i+3] for i in range(0, len(cuerpo_inverso), 3)]
    cuerpo_fmt = '.'.join(bloques)[::-1]
    return f"{cuerpo_fmt}-{dv}"
