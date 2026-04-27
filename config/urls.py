from django.contrib import admin
from django.urls import path

from core.views import (
    agenda_view,
    seguimientos_view,
    marcar_seguimiento_contactado,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('agenda/', agenda_view),
    path('seguimientos/', seguimientos_view, name='seguimientos'),
    path(
        'seguimientos/<int:seguimiento_id>/contactado/',
        marcar_seguimiento_contactado,
        name='marcar_seguimiento_contactado'
    ),
]