from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q

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
    Descuento,
    Insumo,
    ServicioInsumo,
    EstructuraComision,
    ComisionCalculada,
    Proveedor,
    ProductoProveedor,
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
    sucursal_id = request.GET.get('sucursal', '')
    profesional_id = request.GET.get('profesional', '')
    estados_param = request.GET.get('estados', '')

    fecha = date.today()
    if fecha_param:
        try:
            fecha = datetime.strptime(fecha_param, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Parsear estados filtrados
    estados_filtrados = [e.strip() for e in estados_param.split(',') if e.strip()] if estados_param else []

    profesionales = Profesional.objects.filter(activo=True)

    # Filtrar por sucursal si se especifica
    if sucursal_id:
        profesionales = profesionales.filter(sucursal_principal__id=sucursal_id)

    # Filtrar por profesional si se especifica
    if profesional_id:
        profesionales = profesionales.filter(id=profesional_id)

    servicios = Servicio.objects.filter(activo=True).select_related('unidad_negocio')
    pacientes = Paciente.objects.filter(activo=True).order_by('nombres', 'apellidos')
    sucursales = Sucursal.objects.filter(activa=True).order_by('nombre')

    agenda_general = []
    tiene_horarios_ese_dia = False
    # Recolectar las horas de TODOS los profesionales para calcular el rango
    # común (la hora más temprana de cualquiera al inicio, la más tardía al
    # final). Si solo usáramos las horas del primer profesional, la gutter y
    # el fondo se cortarían cuando otros profesionales atienden más temprano
    # o más tarde que él.
    todas_las_horas = set()

    for profesional in profesionales:
        agenda = obtener_agenda_completa(profesional, fecha)
        if agenda:
            tiene_horarios_ese_dia = True
            for b in agenda:
                todas_las_horas.add(b["hora"])
        agenda_general.append({
            "profesional": profesional,
            "agenda": {b["hora"]: b for b in agenda},
            "tiene_horarios": bool(agenda),
        })

    if todas_las_horas:
        # Rango común: del mínimo al máximo, slots de 15 minutos.
        from datetime import time
        hora_min = min(todas_las_horas)
        hora_max = max(todas_las_horas)
        min_total = hora_min.hour * 60 + hora_min.minute
        max_total = hora_max.hour * 60 + hora_max.minute
        horas_base = []
        m = min_total
        while m <= max_total:
            horas_base.append(time(m // 60, m % 60))
            m += 15
    else:
        # Si nadie atiende ese día, mostrar rango global 09:00-18:00
        from datetime import time
        horas_base = [
            time(h, mm) for h in range(9, 18) for mm in [0, 15, 30, 45]
        ]

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
            # Solo renderizar la línea si la hora actual está DENTRO del rango
            # del horario laboral (entre la primera hora y la última de la grilla).
            # Si son las 22:00 y el horario va 09:00-18:00, no tiene sentido
            # mostrar la línea — quedaría flotando fuera del grid y causaría
            # espacio en blanco abajo.
            max_min_visible = total_slots * 15
            if 0 < now_min < max_min_visible:
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

                        # Filtrar por estados si se especificaron
                        if estados_filtrados and c.estado not in estados_filtrados:
                            continue

                        dur = c.servicio.duracion_minutos
                        # Verificar si tiene descuentos aprobados
                        tiene_desc_aprobado = Descuento.objects.filter(
                            cita=c,
                            estado='aprobado'
                        ).exists()

                        citas_render.append({
                            'cita': c,
                            'estado_cita': c.estado,  # Color based on cita state
                            'estado_pago': bloque['estado'],  # Payment indicator (pagado/abonado/sin_pago)
                            'tiene_descuento_aprobado': tiene_desc_aprobado,
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
        "profesionales": profesionales,
        "sucursales": sucursales,
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

    # Procesar pagos con extracción de voucher/boleta
    pagos = []
    for p in cita.pagos.all():
        pago_data = {
            'id': p.id,
            'monto': p.monto,
            'monto_fmt': f"${p.monto:,}".replace(',', '.'),
            'metodo': metodos_display.get(p.metodo, p.metodo),
            'fecha': p.fecha.strftime('%d/%m/%Y %H:%M'),
            'observacion': p.observacion,
            'voucher': None,
            'boleta': None,
        }

        # Extraer voucher y boleta del observación
        if p.observacion:
            obs = p.observacion
            # Buscar Voucher
            if 'Voucher:' in obs:
                voucher_part = obs.split('Voucher:')[1].split('|')[0].strip()
                pago_data['voucher'] = voucher_part
            # Buscar Boleta
            if 'Boleta:' in obs:
                boleta_part = obs.split('Boleta:')[1].split('|')[0].strip()
                pago_data['boleta'] = boleta_part

        pagos.append(pago_data)

    # Obtener descuentos
    descuentos = []
    for desc in cita.descuentos.all():
        descuentos.append({
            'id': desc.id,
            'tipo': desc.get_tipo_display(),
            'valor': desc.valor,
            'monto': desc.monto_descuento,
            'monto_fmt': f"${desc.monto_descuento:,}".replace(',', '.'),
            'estado': desc.get_estado_display(),
            'razon': desc.razon,
            'solicitado_por': desc.solicitado_por,
            'fecha_solicitud': desc.fecha_solicitud.strftime('%d/%m/%Y %H:%M') if desc.fecha_solicitud else None,
        })

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
        'descuentos': descuentos,
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

        # Validar que al menos voucher o boleta esté presente
        voucher = request.POST.get('voucher', '').strip()
        boleta = request.POST.get('boleta', '').strip()
        if not voucher and not boleta:
            return JsonResponse({'error': 'Debes ingresar al menos un comprobante (Voucher o Boleta)'}, status=400)

        # Construir observación con comprobantes
        obs_base = request.POST.get('observacion', '').strip()
        comprobantes = []
        if voucher:
            comprobantes.append(f"Voucher: {voucher}")
        if boleta:
            comprobantes.append(f"Boleta: {boleta}")
        observacion = ' | '.join(comprobantes)
        if obs_base:
            observacion += f" | {obs_base}"

        pago = Pago.objects.create(
            cita=cita, monto=monto, metodo=metodo,
            observacion=observacion
        )
        cita.refresh_from_db()

        # Manejar descuento si aplica
        desc_aplicado = request.POST.get('desc_aplicado', '').strip()
        descuento_obj = None
        msg_descuento = None

        if desc_aplicado == '1':
            desc_tipo = request.POST.get('desc_tipo', 'porcentaje')
            desc_valor = int(request.POST.get('desc_valor', '0'))
            desc_monto = int(request.POST.get('desc_monto', '0'))
            desc_razon = request.POST.get('desc_razon', '').strip()

            if desc_monto > 0:
                descuento_obj = Descuento.objects.create(
                    cita=cita,
                    tipo=desc_tipo,
                    valor=desc_valor,
                    monto_descuento=desc_monto,
                    razon=desc_razon,
                    solicitado_por=request.user.get_full_name() or request.user.username,
                    estado='pendiente'
                )

                # Enviar notificación a Natalia (dueña)
                try:
                    empresa = cita.sucursal.empresa if cita.sucursal else None
                    email_admin = empresa.email if empresa and empresa.email else settings.DEFAULT_FROM_EMAIL

                    asunto = f"⚠️ Solicitud de Descuento - {cita.paciente.nombres} {cita.paciente.apellidos}"
                    mensaje = f"""
Hola,

Se ha solicitado un descuento para una cita:

📋 Paciente: {cita.paciente.nombres} {cita.paciente.apellidos}
📅 Fecha: {cita.fecha.strftime('%d/%m/%Y')} {cita.hora_inicio.strftime('%H:%M')}
💼 Servicio: {cita.servicio.nombre}
💰 Monto Total: ${cita.monto_total:,}

Descuento Solicitado:
- Tipo: {dict(Descuento.TIPOS).get(desc_tipo, desc_tipo)}
- Valor: {desc_valor}
- Monto a Descontar: ${desc_monto:,}
- Razón: {desc_razon or 'No especificada'}
- Solicitado por: {descuento_obj.solicitado_por}

Nuevo Monto Total: ${cita.monto_total - desc_monto:,}

Por favor, revisa y aprueba o rechaza este descuento en el sistema.

Saludos,
Sistema de Gestión Clínica
"""
                    send_mail(
                        asunto,
                        mensaje,
                        settings.DEFAULT_FROM_EMAIL,
                        [email_admin],
                        fail_silently=True
                    )
                except Exception as e:
                    print(f"Error al enviar email: {e}")

                msg_descuento = "Descuento registrado. Pendiente de autorización."

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
            'descuento_msg': msg_descuento,
            'descuento_id': descuento_obj.id if descuento_obj else None,
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


# ── DESCUENTOS ────────────────────────────────────────────────────────────
@login_required
def descuentos_pendientes_view(request):
    """Vista para gestionar descuentos pendientes de autorización"""
    descuentos = Descuento.objects.select_related('cita__paciente', 'cita__servicio').filter(
        estado='pendiente'
    ).order_by('-fecha_solicitud')

    context = {
        'descuentos': descuentos,
        'total_pendientes': descuentos.count(),
    }
    return render(request, 'core/descuentos_pendientes.html', context)


@login_required
def autorizar_descuento(request, descuento_id):
    """Autorizar un descuento pendiente"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    descuento = get_object_or_404(Descuento, id=descuento_id)
    if descuento.estado != 'pendiente':
        return JsonResponse({'error': 'Este descuento ya fue procesado'}, status=400)

    try:
        accion = request.POST.get('accion', 'aprobar')  # aprobar o rechazar

        if accion == 'aprobar':
            descuento.estado = 'aprobado'
            # Aquí podrías aplicar el descuento al monto_total de la cita si necesitas
            estado_msg = 'Descuento aprobado'
        else:
            descuento.estado = 'rechazado'
            estado_msg = 'Descuento rechazado'

        descuento.autorizado_por = request.user.get_full_name() or request.user.username
        descuento.fecha_autorizacion = datetime.now()
        descuento.save()

        # Enviar notificación al que solicitó
        try:
            asunto = f"Descuento {estado_msg.lower()} - {descuento.cita.paciente.nombres}"
            mensaje = f"""
Hola,

El descuento que solicitaste ha sido {estado_msg.lower()}:

📋 Paciente: {descuento.cita.paciente.nombres} {descuento.cita.paciente.apellidos}
💰 Monto: ${descuento.monto_descuento:,}
✅ Autorizado por: {descuento.autorizado_por}

Saludos,
Sistema de Gestión Clínica
"""
            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email] if request.user.email else [],
                fail_silently=True
            )
        except Exception as e:
            print(f"Error al enviar email de notificación: {e}")

        return JsonResponse({'ok': True, 'estado': descuento.get_estado_display()})
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


# ── PROFESIONALES ─────────────────────────────────────────────────────────
@login_required
def profesionales_view(request):
    profesionales = Profesional.objects.select_related('sucursal_principal').prefetch_related('estructuras_comision__unidad_negocio').order_by('nombres')

    # Agregar información de unidad de negocio a cada profesional
    for prof in profesionales:
        # Obtener solo la PRIMERA unidad de negocio activa (la principal)
        primera_unidad = prof.estructuras_comision.filter(activa=True).values_list('unidad_negocio__nombre', flat=True).first()
        prof.unidad_negocio_display = primera_unidad if primera_unidad else '—'

    context = {
        'profesionales': profesionales,
        'total': profesionales.count(),
        'activos': profesionales.filter(activo=True).count(),
    }
    return render(request, 'core/profesionales.html', context)


@login_required
def editar_profesional(request, profesional_id):
    profesional = get_object_or_404(Profesional, id=profesional_id)

    if request.method == 'POST':
        # Actualizar datos básicos
        profesional.nombres = request.POST.get('nombres', '').strip()
        profesional.apellidos = request.POST.get('apellidos', '').strip()
        profesional.nombre_publico = request.POST.get('nombre_publico', '').strip()
        profesional.telefono = request.POST.get('telefono', '').strip()
        profesional.rut = request.POST.get('rut', '').strip()

        fecha_nacimiento = request.POST.get('fecha_nacimiento', '').strip()
        if fecha_nacimiento:
            profesional.fecha_nacimiento = fecha_nacimiento

        profesional.save()

        # Actualizar horarios
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

        # Crear/actualizar usuario si se proporciona email
        email = request.POST.get('email', '').strip()
        if email:
            user, created = User.objects.get_or_create(
                username=email.split('@')[0],
                defaults={
                    'email': email,
                    'first_name': profesional.nombres,
                    'last_name': profesional.apellidos,
                }
            )
            if created:
                user.set_password(request.POST.get('password', 'temporal123'))
                user.save()
                grupo = Group.objects.filter(name='Profesional').first()
                if grupo:
                    user.groups.add(grupo)
                messages.success(request, f'Usuario "{user.username}" creado para {profesional.nombres}.')
            else:
                messages.info(request, f'El usuario "{user.username}" ya existe.')

        messages.success(request, f'Profesional "{profesional.nombres}" actualizado.')
        return redirect('profesionales')

    # GET: preparar datos para el formulario
    horarios_config = []
    for dia, dia_nombre in DIAS_SEMANA:
        h = profesional.horarios.filter(dia_semana=dia).first()
        horarios_config.append({
            'dia_num': dia,
            'dia_nombre': dia_nombre,
            'horario': h
        })

    context = {
        'profesional': profesional,
        'horarios': horarios_config,
        'estructuras_comision': profesional.estructuras_comision.all().order_by('fecha_inicio'),
        'unidades': UnidadNegocio.objects.filter(activa=True),
        'categorias': CategoriaServicio.objects.filter(activa=True),
    }
    return render(request, 'core/editar_profesional.html', context)


@login_required
def crear_estructura_comision(request, profesional_id):
    if request.method != 'POST':
        return redirect('editar_profesional', profesional_id=profesional_id)

    profesional = get_object_or_404(Profesional, id=profesional_id)

    try:
        unidad_id = request.POST.get('unidad_negocio')
        categoria_id = request.POST.get('categoria_servicio')
        tipo_tributo = request.POST.get('tipo_tributo')
        valor_comision = float(request.POST.get('valor_comision', 0))
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin') or None
        vigencia_indefinida = request.POST.get('vigencia_indefinida') == 'on'
        incluye_insumo = request.POST.get('incluye_insumo') == 'on'

        unidad = get_object_or_404(UnidadNegocio, id=unidad_id)
        categoria = get_object_or_404(CategoriaServicio, id=categoria_id)

        EstructuraComision.objects.create(
            profesional=profesional,
            unidad_negocio=unidad,
            categoria_servicio=categoria,
            tipo_tributo=tipo_tributo,
            valor_comision=int(valor_comision),
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin if not vigencia_indefinida else None,
            vigencia_indefinida=vigencia_indefinida,
            incluye_insumo=incluye_insumo,
            activa=True,
        )

        messages.success(request, f'Estructura de comisión agregada para {categoria.nombre}.')
    except Exception as e:
        messages.error(request, f'Error al crear estructura: {e}')

    return redirect('editar_profesional', profesional_id=profesional_id)


@login_required
def editar_estructura_comision(request, estructura_id):
    if request.method != 'POST':
        return redirect('profesionales')

    estructura = get_object_or_404(EstructuraComision, id=estructura_id)

    try:
        unidad_id = request.POST.get('unidad_negocio')
        categoria_id = request.POST.get('categoria_servicio')
        tipo_tributo = request.POST.get('tipo_tributo')
        valor_comision = float(request.POST.get('valor_comision', 0))
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin') or None
        vigencia_indefinida = request.POST.get('vigencia_indefinida') == 'on'
        incluye_insumo = request.POST.get('incluye_insumo') == 'on'

        unidad = get_object_or_404(UnidadNegocio, id=unidad_id)
        categoria = get_object_or_404(CategoriaServicio, id=categoria_id)

        estructura.unidad_negocio = unidad
        estructura.categoria_servicio = categoria
        estructura.tipo_tributo = tipo_tributo
        estructura.valor_comision = int(valor_comision)
        estructura.fecha_inicio = fecha_inicio
        estructura.fecha_fin = fecha_fin if not vigencia_indefinida else None
        estructura.vigencia_indefinida = vigencia_indefinida
        estructura.incluye_insumo = incluye_insumo
        estructura.save()

        messages.success(request, f'Estructura de comisión actualizada para {categoria.nombre}.')
    except Exception as e:
        messages.error(request, f'Error al actualizar estructura: {e}')

    return redirect('editar_profesional', profesional_id=estructura.profesional.id)


@login_required
def eliminar_estructura_comision(request, estructura_id):
    if request.method != 'POST':
        return redirect('profesionales')

    try:
        estructura = EstructuraComision.objects.get(id=estructura_id)
        profesional_id = estructura.profesional.id
        categoria_nombre = estructura.categoria_servicio.nombre

        estructura.delete()
        messages.success(request, f'Estructura de comisión de {categoria_nombre} eliminada.')
        return redirect('editar_profesional', profesional_id=profesional_id)
    except EstructuraComision.DoesNotExist:
        messages.error(request, f'La estructura de comisión no existe.')
        return redirect('profesionales')
    except Exception as e:
        messages.error(request, f'Error al eliminar estructura: {str(e)}')
        return redirect('profesionales')


@login_required
def toggle_profesional(request, profesional_id):
    if request.method != 'POST':
        return redirect('profesionales')
    p = get_object_or_404(Profesional, id=profesional_id)
    p.activo = not p.activo
    p.save()
    estado = 'activado' if p.activo else 'desactivado'
    messages.success(request, f'Profesional "{p.nombres}" {estado}.')
    return redirect('profesionales')


# ── CATEGORÍAS DE SERVICIO ────────────────────────────────────────────────
@login_required
def categorias_view(request):
    categorias = CategoriaServicio.objects.select_related('unidad_negocio').order_by('nombre')
    context = {
        'categorias': categorias,
        'unidades': UnidadNegocio.objects.filter(activa=True),
    }
    return render(request, 'core/categorias.html', context)


@login_required
def crear_categoria(request):
    if request.method != 'POST':
        return redirect('categorias')
    try:
        unidad = get_object_or_404(UnidadNegocio, id=request.POST.get('unidad_negocio'))
        nombre = request.POST.get('nombre', '').strip()

        if not nombre:
            messages.error(request, 'El nombre de la categoría es requerido.')
            return redirect('categorias')

        # Verificar que no existe con el mismo nombre en la misma unidad
        if CategoriaServicio.objects.filter(nombre=nombre, unidad_negocio=unidad).exists():
            messages.error(request, f'Ya existe una categoría "{nombre}" en esta unidad de negocio.')
            return redirect('categorias')

        categoria = CategoriaServicio.objects.create(
            unidad_negocio=unidad,
            nombre=nombre,
            activa=True,
        )
        messages.success(request, f'Categoría "{categoria.nombre}" creada.')
    except Exception as e:
        messages.error(request, f'Error al crear la categoría: {e}')
    return redirect('categorias')


@login_required
def editar_categoria(request, categoria_id):
    categoria = get_object_or_404(CategoriaServicio, id=categoria_id)

    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre', '').strip()

            if not nombre:
                messages.error(request, 'El nombre de la categoría es requerido.')
                return redirect('categorias')

            # Verificar que no existe otro con el mismo nombre en la misma unidad
            if CategoriaServicio.objects.filter(nombre=nombre, unidad_negocio=categoria.unidad_negocio).exclude(id=categoria.id).exists():
                messages.error(request, f'Ya existe una categoría "{nombre}" en esta unidad de negocio.')
                return redirect('categorias')

            # Actualizar unidad de negocio si se envía
            unidad_id = request.POST.get('unidad_negocio')
            if unidad_id:
                categoria.unidad_negocio = get_object_or_404(UnidadNegocio, id=unidad_id)

            categoria.nombre = nombre
            categoria.save()
            messages.success(request, f'Categoría "{categoria.nombre}" actualizada.')
        except Exception as e:
            messages.error(request, f'Error al editar la categoría: {e}')
        return redirect('categorias')

    context = {
        'categoria': categoria,
        'unidades': UnidadNegocio.objects.filter(activa=True),
        'editing': True,
    }
    return render(request, 'core/categorias.html', context)


@login_required
def toggle_categoria(request, categoria_id):
    if request.method != 'POST':
        return redirect('categorias')
    c = get_object_or_404(CategoriaServicio, id=categoria_id)
    c.activa = not c.activa
    c.save()
    estado = 'activada' if c.activa else 'desactivada'
    messages.success(request, f'Categoría "{c.nombre}" {estado}.')
    return redirect('categorias')


@login_required
def eliminar_categoria(request, categoria_id):
    if request.method != 'POST':
        return redirect('categorias')

    categoria = get_object_or_404(CategoriaServicio, id=categoria_id)
    nombre_categoria = categoria.nombre

    try:
        # Verificar si tiene servicios asociados
        if categoria.servicios.exists():
            messages.error(request, f'No se puede eliminar "{nombre_categoria}" porque tiene servicios asociados.')
        else:
            categoria.delete()
            messages.success(request, f'Categoría "{nombre_categoria}" eliminada correctamente.')
    except Exception as e:
        messages.error(request, f'Error al eliminar la categoría: {e}')

    return redirect('categorias')


# ── SERVICIOS ─────────────────────────────────────────────────────────────
@login_required
def servicios_view(request):
    servicios = Servicio.objects.select_related('unidad_negocio', 'categoria').order_by('nombre')
    context = {
        'servicios': servicios,
        'unidades': UnidadNegocio.objects.filter(activa=True),
        'categorias': CategoriaServicio.objects.filter(activa=True),
        'profesionales': Profesional.objects.filter(activo=True),
        'insumos': Insumo.objects.all(),
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

        # Agregar insumos
        insumo_ids = request.POST.getlist('insumos')
        if insumo_ids:
            for insumo_id in insumo_ids:
                try:
                    insumo = Insumo.objects.get(id=insumo_id)
                    ServicioInsumo.objects.create(servicio=servicio, insumo=insumo)
                except Insumo.DoesNotExist:
                    pass

        messages.success(request, f'Servicio "{servicio.nombre}" creado.')
    except Exception as e:
        messages.error(request, f'Error al crear el servicio: {e}')
    return redirect('servicios')


@login_required
def editar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)

    if request.method == 'POST':
        try:
            servicio.nombre = request.POST.get('nombre', servicio.nombre)
            servicio.descripcion = request.POST.get('descripcion', '')

            # Actualizar unidad de negocio
            unidad_id = request.POST.get('unidad_negocio')
            if unidad_id:
                servicio.unidad_negocio = UnidadNegocio.objects.filter(id=unidad_id).first()

            # Actualizar categoría
            cat_id = request.POST.get('categoria')
            if cat_id:
                servicio.categoria = CategoriaServicio.objects.filter(id=cat_id).first()

            precio_str = request.POST.get('precio', str(servicio.precio))
            servicio.precio = int(precio_str.replace('.', '').replace(',', ''))

            servicio.duracion_minutos = int(request.POST.get('duracion_minutos', servicio.duracion_minutos))
            servicio.requiere_seguimiento = request.POST.get('requiere_seguimiento') == 'on'

            dias_seg = request.POST.get('dias_seguimiento')
            servicio.dias_seguimiento = int(dias_seg) if dias_seg else None

            servicio.save()

            # Actualizar profesionales
            prof_ids = request.POST.getlist('profesionales')
            if prof_ids:
                servicio.profesionales.set(Profesional.objects.filter(id__in=prof_ids))
            else:
                servicio.profesionales.clear()

            # Actualizar insumos
            insumo_ids = request.POST.getlist('insumos')
            # Limpiar insumos previos
            servicio.insumos_usados.all().delete()
            # Agregar nuevos insumos
            if insumo_ids:
                for insumo_id in insumo_ids:
                    try:
                        insumo = Insumo.objects.get(id=insumo_id)
                        ServicioInsumo.objects.create(servicio=servicio, insumo=insumo)
                    except Insumo.DoesNotExist:
                        pass

            messages.success(request, f'Servicio "{servicio.nombre}" actualizado.')
            return redirect('servicios')
        except Exception as e:
            messages.error(request, f'Error al actualizar servicio: {e}')

    context = {
        'servicio': servicio,
        'servicio_prof_ids': list(servicio.profesionales.values_list('id', flat=True)),
        'servicio_insumo_ids': list(servicio.insumos_usados.values_list('insumo_id', flat=True)),
        'unidades': UnidadNegocio.objects.filter(activa=True),
        'categorias': CategoriaServicio.objects.filter(activa=True),
        'profesionales': Profesional.objects.filter(activo=True),
        'insumos': Insumo.objects.all(),
    }
    return render(request, 'core/editar_servicio.html', context)


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


@login_required
def eliminar_servicio(request, servicio_id):
    if request.method != 'POST':
        return redirect('servicios')

    servicio = get_object_or_404(Servicio, id=servicio_id)
    nombre_servicio = servicio.nombre

    try:
        servicio.delete()
        messages.success(request, f'Servicio "{nombre_servicio}" eliminado correctamente.')
    except Exception as e:
        messages.error(request, f'Error al eliminar servicio: {e}')

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


# ── DESCUENTOS Y AUTORIZACIONES ───────────────────────────────────────────────

@login_required
def descuentos_pendientes_view(request):
    """Vista admin para autorizar/rechazar descuentos pendientes"""
    if not request.user.is_staff:
        return redirect('dashboard')

    descuentos = Descuento.objects.filter(
        estado='pendiente'
    ).select_related('cita__paciente', 'cita__servicio').order_by('-fecha_solicitud')

    context = {
        'descuentos': descuentos,
        'total': descuentos.count(),
    }
    return render(request, 'core/descuentos_pendientes.html', context)


@login_required
def autorizar_descuento(request, descuento_id):
    """AJAX endpoint para autorizar o rechazar descuentos"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    try:
        descuento = get_object_or_404(Descuento, id=descuento_id)
        accion = request.POST.get('accion')

        if accion == 'aprobar':
            descuento.estado = 'aprobado'
            estado_msg = 'Aprobado'
        elif accion == 'rechazar':
            descuento.estado = 'rechazado'
            motivo_rechazo = request.POST.get('razon', '')
            estado_msg = 'Rechazado'
            if motivo_rechazo:
                descuento.razon = f"[RECHAZO] {motivo_rechazo}"

        descuento.autorizado_por = request.user.get_full_name() or request.user.username
        descuento.fecha_autorizacion = datetime.now()
        descuento.save()

        # Enviar notificación al que solicitó
        try:
            asunto = f"Descuento {estado_msg.lower()} - {descuento.cita.paciente.nombres}"

            # Mensaje base
            mensaje = f"""
Hola,

El descuento que solicitaste ha sido {estado_msg.lower()}:

📋 Paciente: {descuento.cita.paciente.nombres} {descuento.cita.paciente.apellidos}
💰 Monto: ${descuento.monto_descuento:,}
✅ Autorizado por: {descuento.autorizado_por}
"""

            # Agregar motivo de rechazo si aplica
            if descuento.estado == 'rechazado' and descuento.razon:
                motivo = descuento.razon.replace('[RECHAZO] ', '')
                mensaje += f"\n❌ Motivo: {motivo}\n"

            mensaje += """
Saludos,
Sistema de Gestión Clínica
"""
            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email] if request.user.email else [],
                fail_silently=True
            )
        except Exception as e:
            print(f"Error al enviar email de notificación: {e}")

        return JsonResponse({'ok': True, 'estado': descuento.get_estado_display()})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def autorizaciones_view(request):
    """Vista del dashboard de autorizaciones de descuentos"""
    hoy = date.today()
    # Mostrar todas las autorizaciones (pendientes y aprobadas) ordenadas por fecha descendente
    autorizaciones = Descuento.objects.select_related(
        'cita__paciente', 'cita__servicio'
    ).order_by('-fecha_solicitud')

    # Separar en pendientes y procesadas
    pendientes = autorizaciones.filter(estado='pendiente')
    aprobadas = autorizaciones.filter(estado='aprobado')
    rechazadas = autorizaciones.filter(estado='rechazado')

    context = {
        'hoy': hoy,
        'autorizaciones': autorizaciones,
        'pendientes': pendientes,
        'total_pendientes': pendientes.count(),
        'total_aprobadas': aprobadas.count(),
        'total_rechazadas': rechazadas.count(),
        'user_is_staff': request.user.is_staff,
    }
    return render(request, 'core/autorizaciones.html', context)


# ── COMISIONES Y VENTAS ───────────────────────────────────────────────────────

from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce

def calcular_costo_insumos_cita(cita):
    """Calcula el costo total de insumos para una cita"""
    from .models import ServicioInsumo
    costo_total = 0
    insumos = ServicioInsumo.objects.filter(servicio=cita.servicio)
    for si in insumos:
        costo_total += int(float(si.cantidad_usada) * si.insumo.costo_unitario)
    return costo_total


def obtener_descuentos_aprobados_cita(cita):
    """Obtiene el monto total de descuentos aprobados para una cita"""
    descuentos = Descuento.objects.filter(cita=cita, estado='aprobado')
    total = sum(d.monto_descuento for d in descuentos)
    return total


def calcular_comision_cita(cita, estructura_comision):
    """
    Calcula la comisión para una cita basada en su estructura

    Fórmula: (monto_ingresos_brutos - costo_insumos - descuentos) * (porcentaje_comision / 100)
    """
    # Obtener ingresos brutos (lo que el paciente pagó o debe pagar)
    monto_bruto = cita.monto_total

    # Obtener costo de insumos
    costo_insumos = calcular_costo_insumos_cita(cita)

    # Obtener descuentos aprobados
    monto_descuentos = obtener_descuentos_aprobados_cita(cita)

    # Calcular neto
    monto_neto = monto_bruto - costo_insumos - monto_descuentos

    # Aplicar porcentaje de comisión
    if estructura_comision.tipo_comision == 'porcentaje':
        porcentaje = estructura_comision.valor_comision
        monto_comision = int(monto_neto * (porcentaje / 100))
    elif estructura_comision.tipo_comision == 'sociedad_carro':
        porcentaje = estructura_comision.valor_comision
        monto_comision = int(monto_neto * (porcentaje / 100))
    elif estructura_comision.tipo_comision == 'clinica_salud_70_30':
        # 70% al profesional, 30% a la clínica
        monto_comision = int(monto_neto * 0.70)
        porcentaje = 70
    else:
        porcentaje = 0
        monto_comision = 0

    return {
        'monto_bruto': monto_bruto,
        'costo_insumos': costo_insumos,
        'monto_descuentos': monto_descuentos,
        'monto_neto': monto_neto,
        'monto_comision': monto_comision,
        'porcentaje': porcentaje,
    }


@login_required
def comisiones_profesional_view(request):
    """Dashboard de comisiones para un profesional"""
    # Si es staff, puede ver todas las comisiones; si no, solo ve las suyas
    if request.user.is_staff:
        profesional_id = request.GET.get('profesional')
        if profesional_id:
            profesional = get_object_or_404(Profesional, id=profesional_id)
        else:
            # Mostrar lista de profesionales
            profesionales = Profesional.objects.filter(activo=True)
            context = {
                'profesionales': profesionales,
                'mode': 'lista'
            }
            return render(request, 'core/comisiones.html', context)
    else:
        # Profesional regular ve solo sus datos
        try:
            profesional = Profesional.objects.get(
                email=request.user.email
            )
        except Profesional.DoesNotExist:
            messages.error(request, 'No hay perfil de profesional asociado a tu cuenta.')
            return redirect('dashboard')

    # Mes solicitado (por defecto mes actual)
    mes_str = request.GET.get('mes', '')
    if not mes_str:
        hoy = date.today()
        mes_str = hoy.strftime('%Y-%m')

    # Obtener citas del profesional en ese mes
    try:
        fecha_inicio = datetime.strptime(mes_str, '%Y-%m').date()
        fecha_fin = (fecha_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    except ValueError:
        fecha_inicio = date.today().replace(day=1)
        fecha_fin = (date.today() + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        mes_str = fecha_inicio.strftime('%Y-%m')

    citas = Cita.objects.filter(
        profesional=profesional,
        fecha__range=[fecha_inicio, fecha_fin],
        estado__in=['confirmado', 'asistio']  # Solo citas completadas
    ).select_related('servicio', 'paciente', 'servicio__unidad_negocio')

    # Obtener estructura de comisión vigente
    estructura = EstructuraComision.objects.filter(
        profesional=profesional,
        activa=True,
        fecha_inicio__lte=fecha_fin,
        fecha_fin__isnull=True
    ).first()

    if not estructura:
        # Buscar por unidad de negocio o alguna genérica
        estructura = EstructuraComision.objects.filter(
            profesional=profesional,
            activa=True,
            fecha_inicio__lte=fecha_fin
        ).order_by('-fecha_inicio').first()

    # Procesar citas y calcular comisiones
    citas_data = []
    total_ingresos = 0
    total_insumos = 0
    total_descuentos = 0
    total_neto = 0
    total_comision = 0
    cantidad_citas = 0

    for cita in citas:
        comision_data = calcular_comision_cita(cita, estructura) if estructura else {}

        cita_data = {
            'cita': cita,
            'fecha': cita.fecha,
            'paciente': cita.paciente,
            'servicio': cita.servicio,
            **comision_data
        }
        citas_data.append(cita_data)

        total_ingresos += comision_data.get('monto_bruto', 0)
        total_insumos += comision_data.get('costo_insumos', 0)
        total_descuentos += comision_data.get('monto_descuentos', 0)
        total_neto += comision_data.get('monto_neto', 0)
        total_comision += comision_data.get('monto_comision', 0)
        cantidad_citas += 1

    # Agrupar por servicio para análisis de rentabilidad
    servicios_stats = {}
    for cita_data in citas_data:
        servicio_nombre = cita_data['servicio'].nombre
        if servicio_nombre not in servicios_stats:
            servicios_stats[servicio_nombre] = {
                'cantidad': 0,
                'ingresos': 0,
                'insumos': 0,
                'comision': 0,
                'rentabilidad_promedio': 0,
            }

        servicios_stats[servicio_nombre]['cantidad'] += 1
        servicios_stats[servicio_nombre]['ingresos'] += cita_data.get('monto_bruto', 0)
        servicios_stats[servicio_nombre]['insumos'] += cita_data.get('costo_insumos', 0)
        servicios_stats[servicio_nombre]['comision'] += cita_data.get('monto_comision', 0)

    # Calcular rentabilidad promedio por servicio
    for servicio in servicios_stats:
        ingresos = servicios_stats[servicio]['ingresos']
        if ingresos > 0:
            servicios_stats[servicio]['rentabilidad_promedio'] = (
                servicios_stats[servicio]['comision'] / ingresos
            ) * 100

    context = {
        'profesional': profesional,
        'mes': mes_str,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estructura_comision': estructura,
        'citas_data': citas_data,
        'cantidad_citas': cantidad_citas,
        'total_ingresos': total_ingresos,
        'total_insumos': total_insumos,
        'total_descuentos': total_descuentos,
        'total_neto': total_neto,
        'total_comision': total_comision,
        'servicios_stats': servicios_stats,
        'promedio_comision_por_cita': total_comision // cantidad_citas if cantidad_citas > 0 else 0,
    }

    return render(request, 'core/comisiones.html', context)


@login_required
def comisiones_proyeccion_view(request):
    """Vista de simulación y proyección de comisiones"""
    if request.user.is_staff:
        profesional_id = request.GET.get('profesional')
        if profesional_id:
            profesional = get_object_or_404(Profesional, id=profesional_id)
        else:
            profesionales = Profesional.objects.filter(activo=True)
            context = {'profesionales': profesionales, 'mode': 'lista'}
            return render(request, 'core/comisiones_proyeccion.html', context)
    else:
        try:
            profesional = Profesional.objects.get(email=request.user.email)
        except Profesional.DoesNotExist:
            messages.error(request, 'No hay perfil de profesional asociado.')
            return redirect('dashboard')

    # Obtener estructura actual
    estructura = EstructuraComision.objects.filter(
        profesional=profesional,
        activa=True
    ).order_by('-fecha_inicio').first()

    if not estructura:
        messages.error(request, 'No hay estructura de comisión definida.')
        return redirect('dashboard')

    # Datos para simulación
    servicios = Servicio.objects.filter(
        activo=True,
        profesionales=profesional
    ).select_related('unidad_negocio')

    # Calcular datos históricos (últimos 3 meses)
    hoy = date.today()
    hace_3_meses = hoy - timedelta(days=90)

    citas_históricas = Cita.objects.filter(
        profesional=profesional,
        fecha__gte=hace_3_meses,
        estado__in=['confirmado', 'asistio']
    ).select_related('servicio')

    # Agrupar por servicio
    servicios_historico = {}
    for cita in citas_históricas:
        s = cita.servicio
        if s.id not in servicios_historico:
            servicios_historico[s.id] = {
                'nombre': s.nombre,
                'cantidad': 0,
                'ingresos_promedio': 0,
                'total_ingresos': 0,
            }
        servicios_historico[s.id]['cantidad'] += 1
        servicios_historico[s.id]['total_ingresos'] += s.precio

    for s_id in servicios_historico:
        if servicios_historico[s_id]['cantidad'] > 0:
            servicios_historico[s_id]['ingresos_promedio'] = (
                servicios_historico[s_id]['total_ingresos'] / servicios_historico[s_id]['cantidad']
            )

    context = {
        'profesional': profesional,
        'estructura_comision': estructura,
        'servicios': servicios,
        'servicios_historico': servicios_historico,
    }

    return render(request, 'core/comisiones_proyeccion.html', context)


@login_required
def comisiones_todas_view(request):
    """Vista consolidada de TODAS las comisiones (solo para staff/admin)"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permiso para acceder a esta vista.')
        return redirect('comisiones')

    # Parámetros de filtro
    fecha_inicio_param = request.GET.get('fecha_inicio', '')
    fecha_fin_param = request.GET.get('fecha_fin', '')
    profesional_id = request.GET.get('profesional', '')
    unidad_negocio_id = request.GET.get('unidad_negocio', '')

    # Determinar rango de fechas
    hoy = date.today()
    if fecha_inicio_param and fecha_fin_param:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_param, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_param, "%Y-%m-%d").date()
        except:
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = (fecha_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    else:
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = (fecha_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Filtrar profesionales
    profesionales_qs = Profesional.objects.filter(activo=True)
    if profesional_id:
        profesionales_qs = profesionales_qs.filter(id=profesional_id)

    # Datos consolidados
    datos_comisiones = []
    total_citas = 0
    total_ingresos_general = 0
    total_insumos_general = 0
    total_descuentos_general = 0
    total_neto_general = 0
    total_comision_general = 0

    for prof in profesionales_qs:
        # Citas del profesional en el período
        citas_query = Cita.objects.filter(
            profesional=prof,
            fecha__range=[fecha_inicio, fecha_fin],
            estado__in=['confirmado', 'asistio']
        ).select_related('servicio', 'servicio__unidad_negocio')

        # Filtro por unidad de negocio si aplica
        if unidad_negocio_id:
            citas_query = citas_query.filter(servicio__unidad_negocio_id=unidad_negocio_id)

        citas = citas_query

        if not citas.exists():
            continue

        # Estructura de comisión del profesional
        estructura = EstructuraComision.objects.filter(
            profesional=prof,
            activa=True,
            fecha_inicio__lte=fecha_fin
        ).order_by('-fecha_inicio').first()

        # Calcular montos
        monto_ingresos = 0
        monto_insumos = 0
        monto_descuentos = 0
        monto_neto = 0
        monto_comision = 0
        cantidad_citas = len(citas)

        for cita in citas:
            comision_data = calcular_comision_cita(cita, estructura) if estructura else {}
            monto_ingresos += comision_data.get('monto_bruto', 0)
            monto_insumos += comision_data.get('costo_insumos', 0)
            monto_descuentos += comision_data.get('monto_descuentos', 0)
            monto_neto += comision_data.get('monto_neto', 0)
            monto_comision += comision_data.get('monto_comision', 0)

        # Calcular porcentaje de comisión
        porcentaje_comision = (monto_comision / monto_ingresos * 100) if monto_ingresos > 0 else 0

        datos_comisiones.append({
            'profesional': prof,
            'estructura': estructura,
            'cantidad_citas': cantidad_citas,
            'monto_ingresos': monto_ingresos,
            'monto_insumos': monto_insumos,
            'monto_descuentos': monto_descuentos,
            'monto_neto': monto_neto,
            'monto_comision': monto_comision,
            'porcentaje_comision': porcentaje_comision,
        })

        total_citas += cantidad_citas
        total_ingresos_general += monto_ingresos
        total_insumos_general += monto_insumos
        total_descuentos_general += monto_descuentos
        total_neto_general += monto_neto
        total_comision_general += monto_comision

    # Lista de profesionales para filtro
    profesionales_list = Profesional.objects.filter(activo=True).order_by('nombres')
    unidades_negocio = UnidadNegocio.objects.filter(activa=True)

    context = {
        'datos_comisiones': datos_comisiones,
        'total_citas': total_citas,
        'total_ingresos_general': total_ingresos_general,
        'total_insumos_general': total_insumos_general,
        'total_descuentos_general': total_descuentos_general,
        'total_neto_general': total_neto_general,
        'total_comision_general': total_comision_general,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'profesionales_filter': profesionales_list,
        'unidades_negocio_filter': unidades_negocio,
        'profesional_selected': profesional_id,
        'unidad_selected': unidad_negocio_id,
    }

    return render(request, 'core/comisiones_todas.html', context)


def generar_sku_avanzado(producto, fecha, unidad_negocio=None):
    """SKU inteligente — versión mejorada de Insumo.generar_sku.

    Reglas del prefijo del producto (basado en el nombre):
      * Una palabra (ej: 'Botox') → primeras 3 letras → 'BOT'
      * Dos palabras (ej: 'Rejeunesse Shape') → 2 primeras de la 1ra + 1ra de la 2da → 'RES'
      * Tres+ palabras → 1 primera letra de cada (max 3) → 'ACH' para 'Acido Hialuronico Compuesto'

    Acentos y caracteres no alfabéticos se ignoran (Á→A, ç→C, etc).

    Si la unidad de negocio contiene "Imagen" (ej. 'Imagen Mía Servicios'),
    se antepone una 'I' al SKU completo: 'IBOTMAY_001' en lugar de 'BOTMAY_001'.

    Mes y correlativo siguen la lógica original de Insumo.generar_sku.
    """
    if not producto or not fecha:
        return None

    import unicodedata

    # Normalizar nombre: quitar acentos, mayúsculas, solo alfabéticas y espacios
    nombre = producto.nombre or ''
    nombre_norm = unicodedata.normalize('NFKD', nombre)
    nombre_norm = ''.join(c for c in nombre_norm if not unicodedata.combining(c))
    nombre_norm = nombre_norm.upper()

    # Solo letras y espacios
    nombre_limpio = ''.join(c if (c.isalpha() or c == ' ') else '' for c in nombre_norm)
    palabras = [p for p in nombre_limpio.split() if p]

    if not palabras:
        prefijo_prod = 'XXX'
    elif len(palabras) == 1:
        prefijo_prod = palabras[0][:3].ljust(3, 'X')  # 'BOT', 'BOX' (relleno con X si corto)
    elif len(palabras) == 2:
        # 2 primeras letras de la 1ra palabra + 1ra letra de la 2da
        prefijo_prod = (palabras[0][:2] + palabras[1][:1]).ljust(3, 'X')
    else:
        # 1ra letra de cada palabra (hasta 3)
        prefijo_prod = ''.join(p[:1] for p in palabras[:3]).ljust(3, 'X')

    # Meses en español abreviados
    meses_es = {
        1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR', 5: 'MAY', 6: 'JUN',
        7: 'JUL', 8: 'AGO', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DIC',
    }
    mes_abr = meses_es.get(fecha.month, 'XXX')

    # Prefijo de unidad de negocio: "I" si es Imagen Mía
    prefijo_unidad = ''
    if unidad_negocio and 'imagen' in (unidad_negocio.nombre or '').lower():
        prefijo_unidad = 'I'

    sku_prefix = f"{prefijo_unidad}{prefijo_prod}{mes_abr}_"

    # Contar insumos con el mismo prefijo para asignar correlativo
    insumos_mismo = Insumo.objects.filter(codigo_sku__startswith=sku_prefix)
    if not insumos_mismo.exists():
        correlativo = 1
    else:
        ultimos = []
        for ins in insumos_mismo:
            try:
                ultimos.append(int(ins.codigo_sku.split('_')[-1]))
            except (ValueError, IndexError):
                pass
        correlativo = (max(ultimos) + 1) if ultimos else 1

    return f"{sku_prefix}{correlativo:03d}"


# ── INSUMOS ────────────────────────────────────────────────────────────────
@login_required
def insumos_view(request):
    """Vista consolidada de INSUMOS por UnidadNegocio"""
    unidad_id = request.GET.get('unidad', '')
    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')

    # Obtener todas las unidades de negocio activas
    unidades = UnidadNegocio.objects.filter(activa=True).order_by('id')  # 'id' = orden de creación → Sociedad Mia Carro primero

    # Obtener insumos base
    insumos = Insumo.objects.select_related(
        'producto_proveedor',
        'producto_proveedor__proveedor',
        'unidad_negocio',
        'paciente'
    ).order_by('-fecha_creacion')

    # Filtrar por estado (vigente, vencido, vendido, cancelado)
    if estado_filtro:
        insumos = insumos.filter(estado=estado_filtro)
    else:
        # Por defecto mostrar solo vigentes
        insumos = insumos.filter(estado='vigente')

    # Filtrar por unidad de negocio
    if unidad_id:
        insumos = insumos.filter(unidad_negocio__id=unidad_id)

    # Filtrar por búsqueda (nombre de producto o código SKU)
    if busqueda:
        insumos = insumos.filter(
            Q(codigo_sku__icontains=busqueda) |
            Q(producto_proveedor__nombre__icontains=busqueda) |
            Q(producto_proveedor__proveedor__nombre__icontains=busqueda)
        )

    # Calcular estadísticas
    total_insumos = insumos.count()
    total_valor_costo = sum(i.costo_neto * (i.cantidad_disponible or 0) for i in insumos if i.cantidad_disponible)
    total_valor_venta = sum(i.precio_venta_neto * (i.cantidad_disponible or 0) for i in insumos if i.cantidad_disponible)
    insumos_por_vencer = insumos.filter(
        fecha_vencimiento__isnull=False,
        fecha_vencimiento__lte=date.today() + timedelta(days=30),
        estado='vigente'
    ).count()

    # Obtener nombre de la unidad si se filtra
    unidad_nombre = ''
    if unidad_id:
        try:
            unidad_obj = UnidadNegocio.objects.get(id=unidad_id)
            unidad_nombre = unidad_obj.nombre
        except UnidadNegocio.DoesNotExist:
            pass

    context = {
        'insumos': insumos,
        'unidades': unidades,
        'total_insumos': total_insumos,
        'total_valor_costo': total_valor_costo,
        'total_valor_venta': total_valor_venta,
        'insumos_por_vencer': insumos_por_vencer,
        'unidad_selected': unidad_id,
        'unidad_nombre': unidad_nombre,
        'estado_selected': estado_filtro,
        'busqueda': busqueda,
    }

    return render(request, 'core/insumos.html', context)


@login_required
def crear_insumo(request):
    """Crear nuevo insumo.

    La unidad de negocio NO se pide en el formulario — se toma del query
    param ?unidad=X (la unidad en la que estaba el usuario al llegar aquí).
    El SKU se genera automáticamente usando Insumo.generar_sku().
    La cantidad disponible siempre es 1 (cada insumo es un lote unitario).
    """
    unidad_id = request.GET.get('unidad', '')

    # Determinar la unidad de negocio: query param > primera activa
    unidad_negocio = None
    if unidad_id:
        unidad_negocio = UnidadNegocio.objects.filter(id=unidad_id, activa=True).first()
    if not unidad_negocio:
        unidad_negocio = UnidadNegocio.objects.filter(activa=True).order_by('id').first()

    if request.method == 'POST':
        try:
            producto_proveedor_id = request.POST.get('producto_proveedor')
            fecha_compra = request.POST.get('fecha_compra')
            fecha_vencimiento = request.POST.get('fecha_vencimiento', '')
            costo_neto = int(request.POST.get('costo_neto', 0) or 0)
            costo_con_iva = int(request.POST.get('costo_con_iva', 0) or 0)
            precio_venta_neto = int(request.POST.get('precio_venta_neto', 0) or 0)
            precio_venta_con_iva = int(request.POST.get('precio_venta_con_iva', 0) or 0)
            tiempo_maximo_proyectado = request.POST.get('tiempo_maximo_proyectado', '')
            unidad_tiempo = request.POST.get('unidad_tiempo', 'meses')
            descripcion = request.POST.get('descripcion', '')

            # Validar datos requeridos
            if not producto_proveedor_id or not fecha_compra:
                messages.error(request, 'Producto y fecha de compra son obligatorios.')
                return redirect(f'/insumos/crear/?unidad={unidad_negocio.id}' if unidad_negocio else 'insumos')

            if not unidad_negocio:
                messages.error(request, 'No hay unidad de negocio activa configurada.')
                return redirect('insumos')

            producto = get_object_or_404(ProductoProveedor, id=producto_proveedor_id)

            # Si el costo con IVA viene en 0 pero hay neto, calcularlo (IVA 19%)
            if costo_neto and not costo_con_iva:
                costo_con_iva = round(costo_neto * 1.19)
            if precio_venta_neto and not precio_venta_con_iva:
                precio_venta_con_iva = round(precio_venta_neto * 1.19)

            # Crear insumo (cantidad = 1 fija: cada insumo es un lote unitario)
            insumo = Insumo(
                producto_proveedor=producto,
                unidad_negocio=unidad_negocio,
                fecha_compra=fecha_compra,
                fecha_vencimiento=fecha_vencimiento or None,
                costo_neto=costo_neto,
                costo_con_iva=costo_con_iva,
                precio_venta_neto=precio_venta_neto or None,
                precio_venta_con_iva=precio_venta_con_iva or None,
                cantidad_disponible=1,
                unidad=producto.unidad,  # unidad de medida del producto
                tiempo_maximo_proyectado=tiempo_maximo_proyectado or None,
                unidad_tiempo=unidad_tiempo,
                descripcion=descripcion,
                estado='vigente',
            )

            # Generar SKU automáticamente
            from datetime import datetime as dt
            fecha_obj = dt.strptime(fecha_compra, '%Y-%m-%d').date()
            insumo.codigo_sku = generar_sku_avanzado(producto, fecha_obj, unidad_negocio)

            insumo.save()

            messages.success(request, f'Insumo {insumo.codigo_sku} creado correctamente.')
            return redirect(f'/insumos/?unidad={unidad_negocio.id}')

        except Exception as e:
            messages.error(request, f'Error al crear insumo: {str(e)}')
            return redirect(f'/insumos/crear/?unidad={unidad_negocio.id}' if unidad_negocio else 'insumos')

    # GET: mostrar formulario
    productos_proveedores = ProductoProveedor.objects.select_related('proveedor').filter(activo=True).order_by('nombre')

    context = {
        'productos_proveedores': productos_proveedores,
        'unidad_negocio': unidad_negocio,
        'unidad_selected': unidad_id,
    }

    return render(request, 'core/crear_insumo.html', context)


@login_required
def sku_preview(request):
    """Endpoint AJAX que devuelve el SKU sugerido para producto+fecha+unidad.

    Uso: GET /insumos/sku-preview/?producto=ID&fecha=YYYY-MM-DD&unidad=ID
    Respuesta JSON: {"sku": "BOTENE_001"} o {"error": "..."}
    """
    producto_id = request.GET.get('producto', '')
    fecha_str = request.GET.get('fecha', '')
    unidad_id = request.GET.get('unidad', '')

    if not producto_id or not fecha_str:
        return JsonResponse({'sku': '', 'error': 'Falta producto o fecha'})

    try:
        producto = ProductoProveedor.objects.get(id=producto_id)
        from datetime import datetime as dt
        fecha = dt.strptime(fecha_str, '%Y-%m-%d').date()

        unidad_negocio = None
        if unidad_id:
            unidad_negocio = UnidadNegocio.objects.filter(id=unidad_id).first()

        sku = generar_sku_avanzado(producto, fecha, unidad_negocio)
        return JsonResponse({'sku': sku or ''})
    except ProductoProveedor.DoesNotExist:
        return JsonResponse({'sku': '', 'error': 'Producto no existe'})
    except ValueError:
        return JsonResponse({'sku': '', 'error': 'Fecha inválida'})
    except Exception as e:
        return JsonResponse({'sku': '', 'error': str(e)})


@login_required
def editar_insumo(request, insumo_id):
    """Editar insumo existente"""
    insumo = get_object_or_404(Insumo, id=insumo_id)

    if request.method == 'POST':
        try:
            insumo.producto_proveedor_id = request.POST.get('producto_proveedor')
            insumo.unidad_negocio_id = request.POST.get('unidad_negocio')
            insumo.fecha_compra = request.POST.get('fecha_compra')
            insumo.fecha_vencimiento = request.POST.get('fecha_vencimiento') or None
            insumo.costo_neto = int(request.POST.get('costo_neto', 0))
            insumo.costo_con_iva = int(request.POST.get('costo_con_iva', 0))
            insumo.precio_venta_neto = int(request.POST.get('precio_venta_neto', 0))
            insumo.precio_venta_con_iva = int(request.POST.get('precio_venta_con_iva', 0))
            insumo.cantidad_disponible = int(request.POST.get('cantidad_disponible', 0))
            insumo.unidad = request.POST.get('unidad', '')
            insumo.tiempo_maximo_proyectado = request.POST.get('tiempo_maximo_proyectado') or None
            insumo.unidad_tiempo = request.POST.get('unidad_tiempo', 'dias')
            insumo.descripcion = request.POST.get('descripcion', '')
            insumo.estado = request.POST.get('estado', 'vigente')

            # Transferencia: estado y fecha
            estado_transf = request.POST.get('estado_transferencia', 'pendiente')
            fecha_transf = request.POST.get('fecha_transferencia', '')
            # Si se marca realizada sin fecha → usar hoy
            if estado_transf == 'realizada' and not fecha_transf:
                fecha_transf = date.today().isoformat()
            # Si se vuelve a pendiente, limpiar la fecha
            if estado_transf == 'pendiente':
                fecha_transf = ''
            insumo.estado_transferencia = estado_transf
            insumo.fecha_transferencia = fecha_transf or None

            insumo.save()

            messages.success(request, f'Insumo {insumo.codigo_sku} actualizado correctamente.')
            return redirect('insumos')

        except Exception as e:
            messages.error(request, f'Error al actualizar insumo: {str(e)}')

    # GET: mostrar formulario
    productos_proveedores = ProductoProveedor.objects.select_related('proveedor').filter(activo=True).order_by('nombre')
    unidades_negocio = UnidadNegocio.objects.filter(activa=True).order_by('nombre')

    context = {
        'insumo': insumo,
        'productos_proveedores': productos_proveedores,
        'unidades_negocio': unidades_negocio,
    }

    return render(request, 'core/editar_insumo.html', context)


@login_required
def toggle_insumo(request, insumo_id):
    """Activar/desactivar insumo (cambia estado vigente/terminado)"""
    insumo = get_object_or_404(Insumo, id=insumo_id)

    if request.method == 'POST':
        try:
            if insumo.estado == 'terminado':
                insumo.estado = 'vigente'
                messages.success(request, f'Insumo {insumo.codigo_sku} reactivado.')
            else:
                insumo.estado = 'terminado'
                messages.success(request, f'Insumo {insumo.codigo_sku} marcado como terminado.')

            insumo.save()
        except Exception as e:
            messages.error(request, f'Error al cambiar estado: {str(e)}')

    return redirect('insumos')


@login_required
def eliminar_insumo(request, insumo_id):
    """Eliminar insumo (en realidad cambia estado)"""
    return toggle_insumo(request, insumo_id)


# ── PROVEEDORES ────────────────────────────────────────────────────────────
@login_required
def proveedores_view(request):
    """Listado de proveedores con sus productos asociados"""
    busqueda = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '')

    proveedores = Proveedor.objects.prefetch_related('productos').order_by('nombre')

    if busqueda:
        proveedores = proveedores.filter(
            Q(nombre__icontains=busqueda) |
            Q(razon_social__icontains=busqueda) |
            Q(rut__icontains=busqueda) |
            Q(contacto__icontains=busqueda)
        )

    if estado_filtro == 'activos':
        proveedores = proveedores.filter(activo=True)
    elif estado_filtro == 'inactivos':
        proveedores = proveedores.filter(activo=False)

    total_proveedores = proveedores.count()
    total_activos = proveedores.filter(activo=True).count()

    context = {
        'proveedores': proveedores,
        'total_proveedores': total_proveedores,
        'total_activos': total_activos,
        'busqueda': busqueda,
        'estado_selected': estado_filtro,
    }
    return render(request, 'core/proveedores.html', context)


@login_required
def crear_proveedor(request):
    if request.method != 'POST':
        return redirect('proveedores')
    try:
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del proveedor es requerido.')
            return redirect('proveedores')

        empresa = Empresa.objects.filter(activa=True).first()
        if not empresa:
            messages.error(request, 'No hay empresa activa configurada. Revisa el admin.')
            return redirect('proveedores')

        if Proveedor.objects.filter(empresa=empresa, nombre__iexact=nombre).exists():
            messages.error(request, f'Ya existe un proveedor con el nombre "{nombre}".')
            return redirect('proveedores')

        proveedor = Proveedor.objects.create(
            empresa=empresa,
            nombre=nombre,
            razon_social=request.POST.get('razon_social', '').strip(),
            rut=request.POST.get('rut', '').strip(),
            telefono=request.POST.get('telefono', '').strip(),
            email=request.POST.get('email', '').strip(),
            contacto=request.POST.get('contacto', '').strip(),
            activo=True,
        )
        messages.success(request, f'Proveedor "{proveedor.nombre}" creado correctamente.')
    except Exception as e:
        messages.error(request, f'Error al crear proveedor: {e}')
    return redirect('proveedores')


@login_required
def editar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    if request.method != 'POST':
        return redirect('proveedores')
    try:
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del proveedor es requerido.')
            return redirect('proveedores')

        if Proveedor.objects.filter(
            empresa=proveedor.empresa, nombre__iexact=nombre
        ).exclude(id=proveedor.id).exists():
            messages.error(request, f'Ya existe otro proveedor con el nombre "{nombre}".')
            return redirect('proveedores')

        proveedor.nombre = nombre
        proveedor.razon_social = request.POST.get('razon_social', '').strip()
        proveedor.rut = request.POST.get('rut', '').strip()
        proveedor.telefono = request.POST.get('telefono', '').strip()
        proveedor.email = request.POST.get('email', '').strip()
        proveedor.contacto = request.POST.get('contacto', '').strip()
        proveedor.save()
        messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado.')
    except Exception as e:
        messages.error(request, f'Error al editar proveedor: {e}')
    return redirect('proveedores')


@login_required
def toggle_proveedor(request, proveedor_id):
    if request.method != 'POST':
        return redirect('proveedores')
    p = get_object_or_404(Proveedor, id=proveedor_id)
    p.activo = not p.activo
    p.save()
    estado = 'activado' if p.activo else 'desactivado'
    messages.success(request, f'Proveedor "{p.nombre}" {estado}.')
    return redirect('proveedores')


@login_required
def eliminar_proveedor(request, proveedor_id):
    if request.method != 'POST':
        return redirect('proveedores')
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    nombre = proveedor.nombre
    try:
        tiene_insumos = Insumo.objects.filter(
            producto_proveedor__proveedor=proveedor
        ).exists()
        if tiene_insumos:
            messages.error(
                request,
                f'No se puede eliminar "{nombre}" porque tiene insumos registrados. '
                'Desactivalo en lugar de eliminarlo.'
            )
        else:
            proveedor.delete()
            messages.success(request, f'Proveedor "{nombre}" eliminado.')
    except Exception as e:
        messages.error(request, f'Error al eliminar proveedor: {e}')
    return redirect('proveedores')


# ── PRODUCTOS DEL PROVEEDOR ────────────────────────────────────────────────
@login_required
def productos_proveedor_view(request):
    """Listado de productos que ofrecen los proveedores"""
    proveedor_id = request.GET.get('proveedor', '')
    busqueda = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '')

    productos = ProductoProveedor.objects.select_related('proveedor').order_by(
        'proveedor__nombre', 'nombre'
    )

    if proveedor_id:
        productos = productos.filter(proveedor_id=proveedor_id)
    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) |
            Q(proveedor__nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda)
        )
    if estado_filtro == 'activos':
        productos = productos.filter(activo=True)
    elif estado_filtro == 'inactivos':
        productos = productos.filter(activo=False)

    proveedor_nombre = ''
    if proveedor_id:
        try:
            proveedor_nombre = Proveedor.objects.get(id=proveedor_id).nombre
        except Proveedor.DoesNotExist:
            pass

    context = {
        'productos': productos,
        'proveedores': Proveedor.objects.filter(activo=True).order_by('nombre'),
        'proveedor_selected': proveedor_id,
        'proveedor_nombre': proveedor_nombre,
        'busqueda': busqueda,
        'estado_selected': estado_filtro,
        'total_productos': productos.count(),
    }
    return render(request, 'core/productos_proveedor.html', context)


@login_required
def crear_producto_proveedor(request):
    if request.method != 'POST':
        return redirect('productos_proveedor')
    try:
        proveedor = get_object_or_404(Proveedor, id=request.POST.get('proveedor'))
        nombre = request.POST.get('nombre', '').strip()

        if not nombre:
            messages.error(request, 'El nombre del producto es requerido.')
            return redirect('productos_proveedor')

        if ProductoProveedor.objects.filter(proveedor=proveedor, nombre__iexact=nombre).exists():
            messages.error(
                request,
                f'El proveedor "{proveedor.nombre}" ya tiene un producto llamado "{nombre}".'
            )
            return redirect('productos_proveedor')

        producto = ProductoProveedor.objects.create(
            proveedor=proveedor,
            nombre=nombre,
            descripcion=request.POST.get('descripcion', '').strip(),
            unidad=request.POST.get('unidad', 'unidad'),
            activo=True,
        )
        messages.success(request, f'Producto "{producto.nombre}" agregado a {proveedor.nombre}.')
    except Exception as e:
        messages.error(request, f'Error al crear producto: {e}')
    return redirect('productos_proveedor')


@login_required
def editar_producto_proveedor(request, producto_id):
    producto = get_object_or_404(ProductoProveedor, id=producto_id)
    if request.method != 'POST':
        return redirect('productos_proveedor')
    try:
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del producto es requerido.')
            return redirect('productos_proveedor')

        proveedor_id = request.POST.get('proveedor')
        if proveedor_id:
            producto.proveedor = get_object_or_404(Proveedor, id=proveedor_id)

        if ProductoProveedor.objects.filter(
            proveedor=producto.proveedor, nombre__iexact=nombre
        ).exclude(id=producto.id).exists():
            messages.error(
                request,
                f'El proveedor ya tiene otro producto llamado "{nombre}".'
            )
            return redirect('productos_proveedor')

        producto.nombre = nombre
        producto.descripcion = request.POST.get('descripcion', '').strip()
        producto.unidad = request.POST.get('unidad', 'unidad')
        producto.save()
        messages.success(request, f'Producto "{producto.nombre}" actualizado.')
    except Exception as e:
        messages.error(request, f'Error al editar producto: {e}')
    return redirect('productos_proveedor')


@login_required
def toggle_producto_proveedor(request, producto_id):
    if request.method != 'POST':
        return redirect('productos_proveedor')
    p = get_object_or_404(ProductoProveedor, id=producto_id)
    p.activo = not p.activo
    p.save()
    estado = 'activado' if p.activo else 'desactivado'
    messages.success(request, f'Producto "{p.nombre}" {estado}.')
    return redirect('productos_proveedor')


@login_required
def eliminar_producto_proveedor(request, producto_id):
    if request.method != 'POST':
        return redirect('productos_proveedor')
    producto = get_object_or_404(ProductoProveedor, id=producto_id)
    nombre = producto.nombre
    try:
        if producto.insumos.exists():
            messages.error(
                request,
                f'No se puede eliminar "{nombre}" porque tiene insumos registrados. '
                'Desactivalo en lugar de eliminarlo.'
            )
        else:
            producto.delete()
            messages.success(request, f'Producto "{nombre}" eliminado.')
    except Exception as e:
        messages.error(request, f'Error al eliminar producto: {e}')
    return redirect('productos_proveedor')
