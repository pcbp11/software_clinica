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
    path('profesionales/<int:profesional_id>/estructura/crear/', views.crear_estructura_comision, name='crear_estructura_comision'),
    path('profesionales/estructura/<int:estructura_id>/editar/', views.editar_estructura_comision, name='editar_estructura_comision'),
    path('profesionales/estructura/<int:estructura_id>/eliminar/', views.eliminar_estructura_comision, name='eliminar_estructura_comision'),

    # Categorías de Servicio
    path('categorias/', views.categorias_view, name='categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/<int:categoria_id>/editar/', views.editar_categoria, name='editar_categoria'),
    path('categorias/<int:categoria_id>/toggle/', views.toggle_categoria, name='toggle_categoria'),
    path('categorias/<int:categoria_id>/eliminar/', views.eliminar_categoria, name='eliminar_categoria'),

    # Insumos
    path('insumos/', views.insumos_view, name='insumos'),
    path('insumos/crear/', views.crear_insumo, name='crear_insumo'),
    path('insumos/<int:insumo_id>/editar/', views.editar_insumo, name='editar_insumo'),
    path('insumos/<int:insumo_id>/toggle/', views.toggle_insumo, name='toggle_insumo'),
    path('insumos/<int:insumo_id>/eliminar/', views.eliminar_insumo, name='eliminar_insumo'),

    # Servicios
    path('servicios/', views.servicios_view, name='servicios'),
    path('servicios/crear/', views.crear_servicio, name='crear_servicio'),
    path('servicios/<int:servicio_id>/editar/', views.editar_servicio, name='editar_servicio'),
    path('servicios/<int:servicio_id>/toggle/', views.toggle_servicio, name='toggle_servicio'),
    path('servicios/<int:servicio_id>/eliminar/', views.eliminar_servicio, name='eliminar_servicio'),

    # Usuarios
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:user_id>/toggle/', views.toggle_usuario, name='toggle_usuario'),

    # Seguimientos
    path('seguimientos/', views.seguimientos_view, name='seguimientos'),
    path('seguimientos/<int:seguimiento_id>/estado/', views.actualizar_seguimiento, name='actualizar_seguimiento'),
    path('seguimientos/<int:seguimiento_id>/contactado/', views.marcar_seguimiento_contactado, name='marcar_seguimiento_contactado'),

    # Descuentos
    path('descuentos/pendientes/', views.descuentos_pendientes_view, name='descuentos_pendientes'),
    path('descuentos/<int:descuento_id>/autorizar/', views.autorizar_descuento, name='autorizar_descuento'),

    # Autorizaciones (Dashboard)
    path('autorizaciones/', views.autorizaciones_view, name='autorizaciones'),

    # Comisiones y Ventas
    path('comisiones/', views.comisiones_profesional_view, name='comisiones'),
    path('comisiones/proyeccion/', views.comisiones_proyeccion_view, name='comisiones_proyeccion'),
    path('comisiones/todas/', views.comisiones_todas_view, name='comisiones_todas'),
]
