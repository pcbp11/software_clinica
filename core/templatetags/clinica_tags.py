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
