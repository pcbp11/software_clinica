"""Señales de Django para automatizar procesos"""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Insumo


@receiver(pre_save, sender=Insumo)
def generar_sku_automaticamente(sender, instance, **kwargs):
    """
    Genera el código SKU automáticamente antes de guardar un Insumo

    Flujo:
    1. Usuario selecciona ProductoProveedor (obtiene proveedor y nombre automáticamente)
    2. Usuario selecciona fecha de compra
    3. Al guardar, se genera automáticamente el SKU en formato BOTENE_001
    """
    if not instance.codigo_sku and instance.producto_proveedor and instance.fecha_compra:
        instance.generar_codigo_sku_automatico()
