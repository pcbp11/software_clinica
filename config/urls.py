from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Principales
    path('', views.dashboard, name='dashboard'),
    path('agenda/', views.agenda_view, name='agenda'),

    # Citas
    path('citas/nueva/', views.crear_cita, name='crear_cita'),
    path('citas/<int:cita_id>/detalle/', views.detalle_cita, name='detalle_cita'),
    path('citas/<int:cita_id>/estado/', views.actualizar_estado_cita, name='actualizar_estado_cita'),
    path('citas/<int:cita_id>/pago/', views.registrar_pago_cita, name='registrar_pago_cita'),
    path('citas/<int:cita_id>/reagendar/', views.reagendar_cita, name='reagendar_cita'),

    # Horarios profesionales
    path('horarios/', views.horarios_view, name='horarios'),
    path('horarios/<int:profesional_id>/guardar/', views.guardar_horarios, name='guardar_horarios'),

    # Profesionales
    path('profesionales/', views.profesionales_view, name='profesionales'),
    path('profesionales/<int:profesional_id>/editar/', views.editar_profesional, name='editar_profesional'),
    path('profesionales/<int:profesional_id>/toggle/', views.toggle_profesional, name='toggle_profesional'),

    # Servicios
    path('servicios/', views.servicios_view, name='servicios'),
    path('servicios/crear/', views.crear_servicio, name='crear_servicio'),
    path('servicios/<int:servicio_id>/toggle/', views.toggle_servicio, name='toggle_servicio'),

    # Usuarios
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:user_id>/toggle/', views.toggle_usuario, name='toggle_usuario'),

    # Seguimientos
    path('seguimientos/', views.seguimientos_view, name='seguimientos'),
    path('seguimientos/<int:seguimiento_id>/estado/', views.actualizar_seguimiento, name='actualizar_seguimiento'),
    path('seguimientos/<int:seguimiento_id>/contactado/', views.marcar_seguimiento_contactado, name='marcar_seguimiento_contactado'),
]
