from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse

from .models import (
    Empresa,
    UnidadNegocio,
    CategoriaServicio,
    Profesional,
    HorarioProfesional,
    Servicio,
    SeguimientoPaciente,
    Cita,
    Pago,
    Paciente,
    Sucursal,
)
from .utils import obtener_agenda_completa

DIAS_SEMANA = [
    (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
    (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
]


# ── DASHBOARD ─────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    hoy = date.today()
    citas_del_dia = Cita.objects.filter(fecha=hoy).select_related(
        'paciente', 'profesional', 'servicio'
    ).order_by('hora_inicio')
    seguimientos = SeguimientoPaciente.objects.filter(
        estado='pendiente'
    ).select_related('paciente', 'servicio').order_by('fecha_objetivo')[:5]

    context = {
        'hoy': hoy,
        'citas_del_dia': citas_del_dia,
        'citas_hoy': citas_del_dia.count(),
        'citas_confirmadas': citas_del_dia.filter(estado='confirmado').count(),
        'en_espera': citas_del_dia.filter(estado='en_espera').count(),
        'recaudado_hoy': sum(c.monto_pagado for c in citas_del_dia),
        'pagos_hoy': citas_del_dia.filter(estado_pago__in=['pagado', 'abonado']).count(),
        'seguimientos_pendientes': SeguimientoPaciente.objects.filter(estado='pendiente').count(),
        'seguimientos_vencidos': SeguimientoPaciente.objects.filter(
            estado='pendiente', fecha_objetivo__lt=hoy
        ).count(),
        'seguimientos_proximos': seguimientos,
    }
    return render(request, 'core/dashboard.html', context)


# ── AGENDA ────────────────────────────────────────────────────────────────
@login_required
def agenda_view(request):
    fecha_param = request.GET.get('fecha')
    servicio_id = request.GET.get('servicio', '')
    fecha = date.today()
    if fecha_param:
        try:
            fecha = datetime.strptime(fecha_param, "%Y-%m-%d").date()
        except ValueError:
            pass

    profesionales = Profesional.objects.filter(activo=True)
    servicios = Servicio.objects.filter(activo=True).select_related('unidad_negocio')
    pacientes = Paciente.objects.filter(activo=True).order_by('nombres', 'apellidos')

    agenda_general = []
    horas_base = None
    for profesional in profesionales:
        agenda = obtener_agenda_completa(profesional, fecha)
        if not horas_base and agenda:
            horas_base = [b["hora"] for b in agenda]
        agenda_general.append({
            "profesional": profesional,
            "agenda": {b["hora"]: b for b in agenda},
        })

    SLOT_H = 28  # px por bloque de 15 minutos
    horas_labels = []
    hora_now_top = None

    if horas_base:
        base_minutes = horas_base[0].hour * 60 + horas_base[0].minute
        total_slots = len(horas_base)

        for h in horas_base:
            if h.minute == 0:
                m_off = h.hour * 60 + h.minute - base_minutes
                horas_labels.append({
                    'label': h.strftime('%H:%M'),
                    'top_px': (m_off // 15) * SLOT_H,
                })

        if fecha == date.today():
            now = datetime.now().time()
            now_min = now.hour * 60 + now.minute - base_minutes
            if now_min > 0:
                hora_now_top = round((now_min / 15) * SLOT_H)

        for item in agenda_general:
            seen_citas = set()
            citas_render = []
            slots_render = []
            for bloque in sorted(item['agenda'].values(), key=lambda b: b['hora']):
                h = bloque['hora']
                m_off = h.hour * 60 + h.minute - base_minutes
                top_px = (m_off // 15) * SLOT_H
                if bloque['cita']:
                    c = bloque['cita']
                    if c.id not in seen_citas:
                        seen_citas.add(c.id)
                        dur = c.servicio.duracion_minutos
                        citas_render.append({
                            'cita': c,
                            'estado': bloque['estado'],
                            'top_px': top_px,
                            'height_px': max((dur // 15) * SLOT_H, SLOT_H) - 3,
                        })
                else:
                    slots_render.append({
                        'hora': h.strftime('%H:%M'),
                        'top_px': top_px,
                    })
            item['citas_render'] = citas_render
            item['slots_render'] = slots_render

        total_height_px = total_slots * SLOT_H
    else:
        base_minutes = 0
        total_height_px = 0
        for item in agenda_general:
            item['citas_render'] = []
            item['slots_render'] = []

    context = {
        "fecha": fecha,
        "hoy": date.today(),
        "fecha_anterior": fecha - timedelta(days=1),
        "fecha_siguiente": fecha + timedelta(days=1),
        "horas": horas_base or [],
        "agenda_general": agenda_general,
        "servicio_id": servicio_id,
        "servicios": servicios,
        "pacientes": pacientes,
        "total_height_px": total_height_px,
        "horas_labels": horas_labels,
        "hora_now_top": hora_now_top,
        "slot_h": SLOT_H,
    }
    return render(request, "core/agenda.html", context)


# ── CREAR CITA ────────────────────────────────────────────────────────────
@login_required
def crear_cita(request):
    if request.method != 'POST':
        return redirect('agenda')
    fecha_str = request.POST.get('fecha', '')
    try:
        paciente = get_object_or_404(Paciente, id=request.POST.get('paciente'))
        servicio = get_object_or_404(Servicio, id=request.POST.get('servicio'))
        profesional = get_object_or_404(Profesional, id=request.POST.get('profesional'))
        sucursal = profesional.sucursal_principal or Sucursal.objects.filter(activo=True).first()
        if not sucursal:
            messages.error(request, 'No hay sucursal activa. Créala en Administración.')
            return redirect(f'/agenda/?fecha={fecha_str}')
        hora_str = request.POST.get('hora_inicio', '')
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        hora = datetime.strptime(hora_str, '%H:%M').time()
        cita = Cita(
            sucursal=sucursal, paciente=paciente, profesional=profesional,
            servicio=servicio, fecha=fecha, hora_inicio=hora,
            observaciones=request.POST.get('observaciones', ''),
        )
        cita.save()
        messages.success(request,
            f'Cita agendada: {paciente.nombres} {paciente.apellidos} · {servicio.nombre} · {hora.strftime("%H:%M")}')
    except ValidationError as e:
        for msg in e.messages:
            messages.error(request, msg)
    except Exception as e:
        messages.error(request, f'No se pudo agendar: {e}')
    return redirect(f'/agenda/?fecha={fecha_str}')


# ── CITA: DETALLE (AJAX) ──────────────────────────────────────────────────
@login_required
def detalle_cita(request, cita_id):
    cita = get_object_or_404(
        Cita.objects.select_related('paciente', 'profesional', 'servicio'),
        id=cita_id
    )
    metodos_display = dict(Pago.METODOS_PAGO)
    pagos = [
        {
            'id': p.id,
            'monto': p.monto,
            'monto_fmt': f"${p.monto:,}".replace(',', '.'),
            'metodo': metodos_display.get(p.metodo, p.metodo),
            'fecha': p.fecha.strftime('%d/%m/%Y %H:%M'),
            'observacion': p.observacion,
        }
        for p in cita.pagos.all()
    ]
    return JsonResponse({
        'id': cita.id,
        'paciente': f"{cita.paciente.nombres} {cita.paciente.apellidos}",
        'paciente_rut': cita.paciente.rut,
        'paciente_telefono': cita.paciente.telefono,
        'servicio': cita.servicio.nombre,
        'profesional': str(cita.profesional),
        'profesional_id': cita.profesional.id,
        'fecha': cita.fecha.strftime('%d/%m/%Y'),
        'fecha_iso': cita.fecha.strftime('%Y-%m-%d'),
        'hora_inicio': cita.hora_inicio.strftime('%H:%M'),
        'hora_fin': cita.hora_fin.strftime('%H:%M') if cita.hora_fin else '',
        'estado': cita.estado,
        'estado_display': cita.get_estado_display(),
        'estado_pago': cita.estado_pago,
        'estado_pago_display': cita.get_estado_pago_display(),
        'monto_total': cita.monto_total,
        'monto_total_fmt': f"${cita.monto_total:,}".replace(',', '.'),
        'monto_pagado': cita.monto_pagado,
        'monto_pagado_fmt': f"${cita.monto_pagado:,}".replace(',', '.'),
        'saldo_pendiente': cita.saldo_pendiente,
        'saldo_pendiente_fmt': f"${cita.saldo_pendiente:,}".replace(',', '.'),
        'observaciones': cita.observaciones,
        'pagos': pagos,
    })


# ── CITA: CAMBIAR ESTADO (AJAX) ───────────────────────────────────────────
@login_required
def actualizar_estado_cita(request, cita_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    cita = get_object_or_404(Cita, id=cita_id)
    nuevo_estado = request.POST.get('estado')
    if nuevo_estado not in [e[0] for e in Cita.ESTADOS]:
        return JsonResponse({'error': 'Estado no válido'}, status=400)
    cita.estado = nuevo_estado
    cita.save()
    return JsonResponse({
        'ok': True,
        'estado': cita.estado,
        'estado_display': cita.get_estado_display(),
    })


# ── CITA: REGISTRAR PAGO (AJAX) ───────────────────────────────────────────
@login_required
def registrar_pago_cita(request, cita_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    cita = get_object_or_404(Cita, id=cita_id)
    try:
        monto_str = request.POST.get('monto', '0').replace('.', '').replace(',', '')
        monto = int(monto_str)
        if monto <= 0:
            return JsonResponse({'error': 'El monto debe ser mayor a cero'}, status=400)
        metodo = request.POST.get('metodo', 'efectivo')
        if metodo not in [m[0] for m in Pago.METODOS_PAGO]:
            return JsonResponse({'error': 'Método no válido'}, status=400)
        pago = Pago.objects.create(
            cita=cita, monto=monto, metodo=metodo,
            observacion=request.POST.get('observacion', '')
        )
        cita.refresh_from_db()
        return JsonResponse({
            'ok': True,
            'pago_id': pago.id,
            'pago_monto_fmt': f"${pago.monto:,}".replace(',', '.'),
            'pago_metodo': dict(Pago.METODOS_PAGO).get(metodo, metodo),
            'pago_fecha': pago.fecha.strftime('%d/%m/%Y %H:%M'),
            'monto_pagado': cita.monto_pagado,
            'monto_pagado_fmt': f"${cita.monto_pagado:,}".replace(',', '.'),
            'saldo_pendiente': cita.saldo_pendiente,
            'saldo_pendiente_fmt': f"${cita.saldo_pendiente:,}".replace(',', '.'),
            'estado_pago': cita.estado_pago,
            'estado_pago_display': cita.get_estado_pago_display(),
        })
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Monto inválido: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ── CITA: REAGENDAR (AJAX) ────────────────────────────────────────────────
@login_required
def reagendar_cita(request, cita_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    cita_original = get_object_or_404(Cita, id=cita_id)
    try:
        nueva_fecha_str = request.POST.get('nueva_fecha', '')
        nueva_hora_str = request.POST.get('nueva_hora', '')
        if not nueva_fecha_str or not nueva_hora_str:
            return JsonResponse({'error': 'Ingresa fecha y hora para reagendar'}, status=400)
        nueva_fecha = datetime.strptime(nueva_fecha_str, '%Y-%m-%d').date()
        nueva_hora = datetime.strptime(nueva_hora_str, '%H:%M').time()
        nueva_cita = Cita(
            sucursal=cita_original.sucursal,
            paciente=cita_original.paciente,
            profesional=cita_original.profesional,
            servicio=cita_original.servicio,
            fecha=nueva_fecha,
            hora_inicio=nueva_hora,
            cita_origen=cita_original,
            observaciones=f'Reagendada desde cita del {cita_original.fecha.strftime("%d/%m/%Y")} {cita_original.hora_inicio.strftime("%H:%M")}.',
        )
        nueva_cita.save()
        cita_original.estado = 'reprogramada'
        cita_original.save()
        return JsonResponse({
            'ok': True,
            'nueva_fecha': nueva_fecha.strftime('%Y-%m-%d'),
            'redirect': f'/agenda/?fecha={nueva_fecha.strftime("%Y-%m-%d")}',
        })
    except ValidationError as e:
        return JsonResponse({'error': ' '.join(e.messages)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ── HORARIOS ──────────────────────────────────────────────────────────────
@login_required
def horarios_view(request):
    profesionales = Profesional.objects.filter(activo=True)
    profesionales_data = []
    for prof in profesionales:
        horarios_map = {h.dia_semana: h for h in prof.horarios.all()}
        horarios_list = [
            {'dia_num': num, 'dia_nombre': nombre, 'h': horarios_map.get(num)}
            for num, nombre in DIAS_SEMANA
        ]
        profesionales_data.append({'profesional': prof, 'horarios': horarios_list})

    context = {'profesionales_data': profesionales_data}
    return render(request, 'core/horarios.html', context)


@login_required
def guardar_horarios(request, profesional_id):
    if request.method != 'POST':
        return redirect('horarios')
    profesional = get_object_or_404(Profesional, id=profesional_id)
    for dia, _ in DIAS_SEMANA:
        activo = request.POST.get(f'activo_{dia}') == 'on'
        hi_str = request.POST.get(f'hora_inicio_{dia}', '')
        hf_str = request.POST.get(f'hora_fin_{dia}', '')
        tiene_descanso = request.POST.get(f'tiene_descanso_{dia}') == 'on'
        id_str = request.POST.get(f'inicio_descanso_{dia}', '')
        fd_str = request.POST.get(f'fin_descanso_{dia}', '')
        try:
            hi = datetime.strptime(hi_str, '%H:%M').time() if hi_str else None
            hf = datetime.strptime(hf_str, '%H:%M').time() if hf_str else None
            id_ = datetime.strptime(id_str, '%H:%M').time() if id_str and tiene_descanso else None
            fd_ = datetime.strptime(fd_str, '%H:%M').time() if fd_str and tiene_descanso else None
        except ValueError:
            continue
        HorarioProfesional.objects.update_or_create(
            profesional=profesional, dia_semana=dia,
            defaults={
                'activo': activo, 'hora_inicio': hi, 'hora_fin': hf,
                'tiene_descanso': tiene_descanso,
                'inicio_descanso': id_, 'fin_descanso': fd_,
            }
        )
    messages.success(request, f'Horarios de {profesional} actualizados.')
    return redirect('horarios')


# ── SERVICIOS ─────────────────────────────────────────────────────────────
@login_required
def servicios_view(request):
    servicios = Servicio.objects.select_related('unidad_negocio', 'categoria').order_by('nombre')
    context = {
        'servicios': servicios,
        'unidades': UnidadNegocio.objects.filter(activa=True),
        'categorias': CategoriaServicio.objects.filter(activa=True),
        'profesionales': Profesional.objects.filter(activo=True),
    }
    return render(request, 'core/servicios.html', context)


@login_required
def crear_servicio(request):
    if request.method != 'POST':
        return redirect('servicios')
    try:
        empresa = Empresa.objects.filter(activa=True).first()
        if not empresa:
            messages.error(request, 'No hay empresa activa. Créala en Administración.')
            return redirect('servicios')
        unidad = get_object_or_404(UnidadNegocio, id=request.POST.get('unidad_negocio'))
        cat_id = request.POST.get('categoria')
        categoria = CategoriaServicio.objects.filter(id=cat_id).first() if cat_id else None
        precio = int(request.POST.get('precio', '0').replace('.', '').replace(',', ''))
        dias_seg = request.POST.get('dias_seguimiento') or None
        servicio = Servicio.objects.create(
            empresa=empresa,
            unidad_negocio=unidad,
            categoria=categoria,
            nombre=request.POST.get('nombre', '').strip(),
            descripcion=request.POST.get('descripcion', '').strip(),
            duracion_minutos=int(request.POST.get('duracion_minutos', 60)),
            precio=precio,
            requiere_seguimiento=request.POST.get('requiere_seguimiento') == 'on',
            dias_seguimiento=int(dias_seg) if dias_seg else None,
        )
        prof_ids = request.POST.getlist('profesionales')
        if prof_ids:
            servicio.profesionales.set(Profesional.objects.filter(id__in=prof_ids))
        messages.success(request, f'Servicio "{servicio.nombre}" creado.')
    except Exception as e:
        messages.error(request, f'Error al crear el servicio: {e}')
    return redirect('servicios')


@login_required
def toggle_servicio(request, servicio_id):
    if request.method != 'POST':
        return redirect('servicios')
    s = get_object_or_404(Servicio, id=servicio_id)
    s.activo = not s.activo
    s.save()
    estado = 'activado' if s.activo else 'desactivado'
    messages.success(request, f'Servicio "{s.nombre}" {estado}.')
    return redirect('servicios')


# ── USUARIOS ──────────────────────────────────────────────────────────────
@login_required
def usuarios_view(request):
    if not request.user.is_staff:
        messages.error(request, 'Solo administradores pueden gestionar usuarios.')
        return redirect('dashboard')
    for nombre in ['Admin', 'Recepcionista', 'Profesional']:
        Group.objects.get_or_create(name=nombre)
    context = {
        'usuarios': User.objects.prefetch_related('groups').order_by('first_name', 'last_name'),
        'grupos': Group.objects.all().order_by('name'),
    }
    return render(request, 'core/usuarios.html', context)


@login_required
def crear_usuario(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method != 'POST':
        return redirect('usuarios')
    try:
        username = request.POST.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            messages.error(request, f'El usuario "{username}" ya existe.')
            return redirect('usuarios')
        user = User.objects.create_user(
            username=username,
            first_name=request.POST.get('first_name', '').strip(),
            last_name=request.POST.get('last_name', '').strip(),
            email=request.POST.get('email', '').strip(),
            password=request.POST.get('password', ''),
        )
        if request.POST.get('is_staff') == 'on':
            user.is_staff = True
            user.save()
        grupo_id = request.POST.get('grupo')
        if grupo_id:
            grupo = Group.objects.filter(id=grupo_id).first()
            if grupo:
                user.groups.add(grupo)
        messages.success(request, f'Usuario "{username}" creado.')
    except Exception as e:
        messages.error(request, f'Error al crear usuario: {e}')
    return redirect('usuarios')


@login_required
def toggle_usuario(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    if request.method != 'POST':
        return redirect('usuarios')
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, 'No puedes desactivar tu propio usuario.')
        return redirect('usuarios')
    user.is_active = not user.is_active
    user.save()
    estado = 'activado' if user.is_active else 'desactivado'
    messages.success(request, f'Usuario "{user.username}" {estado}.')
    return redirect('usuarios')


# ── SEGUIMIENTOS ──────────────────────────────────────────────────────────
@login_required
def seguimientos_view(request):
    hoy = date.today()
    seguimientos = SeguimientoPaciente.objects.filter(
        estado='pendiente'
    ).select_related('paciente', 'servicio', 'cita_origen').order_by('fecha_objetivo')
    context = {"hoy": hoy, "seguimientos": seguimientos}
    return render(request, "core/seguimientos.html", context)


@login_required
def actualizar_seguimiento(request, seguimiento_id):
    seguimiento = get_object_or_404(SeguimientoPaciente, id=seguimiento_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in ['contactado', 'agendado', 'descartado']:
            seguimiento.estado = nuevo_estado
            seguimiento.save()
    return redirect('seguimientos')


# Alias para compatibilidad con URL existente
@login_required
def marcar_seguimiento_contactado(request, seguimiento_id):
    return actualizar_seguimiento(request, seguimiento_id)
