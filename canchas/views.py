from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import FileResponse
from .models import Cancha, Reserva, Complejo, Pago
from .services import ReporteService, EstadisticasService
from usuarios.services import NotificacionService
from django.urls import reverse
import os
import json
from django.core.serializers.json import DjangoJSONEncoder
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from django.http import HttpResponse

def home(request):
    # Obtener canchas destacadas o más reservadas
    canchas_destacadas = Cancha.objects.all()[:6]
    return render(request, 'home.html', {
        'canchas_destacadas': canchas_destacadas
    })

def lista_canchas(request):
    # Filtros
    ubicacion = request.GET.get('ubicacion')
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    
    canchas = Cancha.objects.all()
    
    if ubicacion:
        canchas = canchas.filter(complejo__ubicacion__icontains=ubicacion)
    if precio_min:
        canchas = canchas.filter(precio_hora__gte=precio_min)
    if precio_max:
        canchas = canchas.filter(precio_hora__lte=precio_max)
        
    return render(request, 'canchas/lista.html', {
        'canchas': canchas
    })

def detalle_cancha(request, pk):
    cancha = get_object_or_404(Cancha, pk=pk)
    
    # Obtener horarios disponibles para los próximos 7 días
    fecha_actual = timezone.now()
    fecha_limite = fecha_actual + timedelta(days=7)
    reservas_existentes = cancha.reservas.filter(
        fecha_hora__gte=fecha_actual,
        fecha_hora__lte=fecha_limite,
        cancelada=False
    )
    
    # Crear lista de horarios disponibles
    horarios_disponibles = []
    for dia in range(8):
        fecha = fecha_actual.date() + timedelta(days=dia)
        for hora in range(8, 23):  # De 8:00 a 22:00
            datetime_slot = datetime.combine(fecha, datetime.min.time().replace(hour=hora))
            if not reservas_existentes.filter(fecha_hora=datetime_slot).exists():
                horarios_disponibles.append(datetime_slot)
    
    return render(request, 'canchas/detalle.html', {
        'cancha': cancha,
        'horarios_disponibles': horarios_disponibles
    })

@login_required
def reservar_cancha(request, cancha_id):
    if request.method == 'POST':
        cancha = get_object_or_404(Cancha, pk=cancha_id)
        fecha_hora_str = request.POST.get('fecha_hora')
        
        try:
            fecha_hora = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')
            
            # Verificar si el horario ya está reservado
            if Reserva.objects.filter(
                cancha=cancha,
                fecha_hora=fecha_hora,
                cancelada=False
            ).exists():
                messages.error(request, 'Este horario ya está reservado')
                return redirect('canchas:detalle_cancha', pk=cancha_id)
            
            # Crear la reserva
            Reserva.objects.create(
                jugador=request.user,
                cancha=cancha,
                fecha_hora=fecha_hora,
                precio_total=cancha.precio_hora,
                turno_servicios=request.POST.get('turno_servicios')
            )
            
            # Notificar al jugador
            NotificacionService.enviar_notificacion(
                usuario=request.user,
                tipo='RESERVA',
                titulo='¡Reserva confirmada!',
                mensaje=f'Tu reserva para {cancha.nombre} el {fecha_hora.strftime("%d/%m/%Y %H:%M")} ha sido confirmada.',
                url=reverse('canchas:detalle_reserva', args=[reserva.id])
            )
            
            # Notificar al dueño de la cancha
            NotificacionService.enviar_notificacion(
                usuario=cancha.complejo.dueno.usuario,
                tipo='RESERVA',
                titulo='Nueva reserva recibida',
                mensaje=f'Nueva reserva para {cancha.nombre} el {fecha_hora.strftime("%d/%m/%Y %H:%M")}',
                url=reverse('canchas:detalle_reserva', args=[reserva.id])
            )
            
            messages.success(request, '¡Reserva realizada con éxito!')
            return redirect('usuarios:perfil')
            
        except ValueError:
            messages.error(request, 'Formato de fecha y hora inválido')
            
    return redirect('canchas:detalle_cancha', pk=cancha_id)

@login_required
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id, jugador=request.user)
    
    # Verificar si la reserva puede ser cancelada (por ejemplo, 24h antes)
    if reserva.fecha_hora - timezone.now() < timedelta(hours=24):
        messages.error(request, 'No se puede cancelar con menos de 24h de anticipación')
        return redirect('usuarios:perfil')
    
    reserva.cancelada = True
    reserva.hora_cancelacion = timezone.now()
    reserva.save()
    
    # Notificar al jugador
    NotificacionService.enviar_notificacion(
        usuario=reserva.jugador,
        tipo='CANCELACION',
        titulo='Reserva cancelada',
        mensaje=f'Tu reserva para {reserva.cancha.nombre} el {reserva.fecha_hora.strftime("%d/%m/%Y %H:%M")} ha sido cancelada.',
        url=reverse('canchas:detalle_reserva', args=[reserva.id])
    )
    
    # Notificar al dueño
    NotificacionService.enviar_notificacion(
        usuario=reserva.cancha.complejo.dueno.usuario,
        tipo='CANCELACION',
        titulo='Reserva cancelada',
        mensaje=f'Una reserva para {reserva.cancha.nombre} el {reserva.fecha_hora.strftime("%d/%m/%Y %H:%M")} ha sido cancelada.',
        url=reverse('canchas:detalle_reserva', args=[reserva.id])
    )
    
    messages.success(request, 'Reserva cancelada con éxito')
    return redirect('usuarios:perfil')

@login_required
def procesar_pago(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id, jugador=request.user)
    tipo_pago = request.POST.get('tipo_pago')
    
    if tipo_pago not in ['SENA', 'TOTAL']:
        messages.error(request, 'Tipo de pago inválido')
        return redirect('canchas:detalle_reserva', pk=reserva_id)
    
    monto = reserva.monto_sena if tipo_pago == 'SENA' else reserva.precio_total
    
    try:
        # Aquí iría la integración con el sistema de pagos (por ejemplo, MercadoPago)
        # Por ahora, simulamos un pago exitoso
        pago = Pago.objects.create(
            reserva=reserva,
            monto=monto,
            tipo=tipo_pago,
            estado='APROBADO',
            referencia_pago='SIMULADO_' + str(timezone.now().timestamp())
        )
        
        if pago.estado == 'APROBADO':
            NotificacionService.enviar_notificacion(
                usuario=reserva.jugador,
                tipo='PAGO',
                titulo='Pago procesado exitosamente',
                mensaje=f'Tu pago de ${pago.monto} para la reserva en {reserva.cancha.nombre} ha sido confirmado.',
                url=reverse('canchas:detalle_reserva', args=[reserva.id])
            )
            
            NotificacionService.enviar_notificacion(
                usuario=reserva.cancha.complejo.dueno.usuario,
                tipo='PAGO',
                titulo='Pago recibido',
                mensaje=f'Se ha recibido un pago de ${pago.monto} para la reserva en {reserva.cancha.nombre}',
                url=reverse('canchas:detalle_reserva', args=[reserva.id])
            )
        
        messages.success(request, f'Pago de ${monto} procesado con éxito')
        return redirect('usuarios:perfil')
        
    except Exception as e:
        messages.error(request, f'Error al procesar el pago: {str(e)}')
        return redirect('canchas:detalle_reserva', pk=reserva_id)

def es_dueno(user):
    return hasattr(user, 'perfil_cliente')

@user_passes_test(es_dueno)
def panel_admin(request):
    perfil = request.user.perfil_cliente
    complejos = perfil.complejos.all()
    
    # Estadísticas generales
    total_canchas = sum(complejo.canchas.count() for complejo in complejos)
    reservas_hoy = sum(
        complejo.canchas.filter(
            reservas__fecha_hora__date=timezone.now().date(),
            reservas__cancelada=False
        ).count() for complejo in complejos
    )
    
    # Ingresos del último mes
    fecha_inicio = timezone.now() - timedelta(days=30)
    ingresos_mes = Pago.objects.filter(
        reserva__cancha__complejo__in=complejos,
        estado='APROBADO',
        fecha__gte=fecha_inicio
    ).aggregate(total=Sum('monto'))['total'] or 0
    
    # Notificar si hay baja ocupación
    for complejo in complejos:
        tasa_ocupacion = complejo.calcular_tasa_ocupacion()
        if tasa_ocupacion < 30:  # menos del 30% de ocupación
            NotificacionService.enviar_notificacion(
                usuario=request.user,
                tipo='SISTEMA',
                titulo='Baja ocupación detectada',
                mensaje=f'Tu complejo {complejo.nombre} tiene una tasa de ocupación del {tasa_ocupacion}%',
                url=reverse('canchas:estadisticas_complejo', args=[complejo.id])
            )
    
    context = {
        'complejos': complejos,
        'total_canchas': total_canchas,
        'reservas_hoy': reservas_hoy,
        'ingresos_mes': ingresos_mes,
    }
    return render(request, 'canchas/panel_admin.html', context)

@user_passes_test(es_dueno)
def estadisticas_complejo(request, complejo_id):
    try:
        complejo = get_object_or_404(Complejo, id=complejo_id, dueno__usuario=request.user)
        
        # Obtener período de tiempo
        periodo = request.GET.get('periodo', 'semana')
        fecha_fin = timezone.now().date()
        
        # Determinar fecha de inicio según el período
        if periodo == 'semana':
            fecha_inicio = fecha_fin - timedelta(days=7)
            titulo_periodo = 'Esta Semana'
        elif periodo == 'mes':
            fecha_inicio = fecha_fin - timedelta(days=30)
            titulo_periodo = 'Este Mes'
        elif periodo == 'año':
            fecha_inicio = fecha_fin - timedelta(days=365)
            titulo_periodo = 'Este Año'
        else:
            fecha_inicio = fecha_fin - timedelta(days=7)
            titulo_periodo = 'Esta Semana'

        # Obtener estadísticas
        estadisticas = EstadisticasService.obtener_estadisticas_complejo(
            complejo=complejo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        # Preparar datos para los gráficos
        reservas_por_dia = {}
        ingresos_por_cancha = {}
        
        # Inicializar todas las fechas en el rango
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            reservas_por_dia[fecha_actual.strftime('%d/%m')] = 0
            fecha_actual += timedelta(days=1)

        # Obtener reservas en el período
        reservas = Reserva.objects.filter(
            cancha__complejo=complejo,
            fecha_hora__date__range=[fecha_inicio, fecha_fin]
        ).select_related('cancha')

        # Poblar datos de reservas por día
        for reserva in reservas:
            fecha_str = reserva.fecha_hora.strftime('%d/%m')
            reservas_por_dia[fecha_str] = reservas_por_dia.get(fecha_str, 0) + 1

        # Calcular ingresos por cancha
        for cancha in complejo.canchas.all():
            ingresos = sum(
                reserva.monto_total 
                for reserva in reservas 
                if reserva.cancha_id == cancha.id and reserva.pagado
            )
            if ingresos > 0:
                ingresos_por_cancha[cancha.nombre] = ingresos

        # Calcular comparación con período anterior
        periodo_anterior_inicio = fecha_inicio - (fecha_fin - fecha_inicio)
        periodo_anterior_fin = fecha_inicio - timedelta(days=1)
        
        estadisticas_anterior = EstadisticasService.obtener_estadisticas_complejo(
            complejo=complejo,
            fecha_inicio=periodo_anterior_inicio,
            fecha_fin=periodo_anterior_fin
        )

        # Calcular variaciones
        def calcular_variacion(actual, anterior):
            if anterior == 0:
                return 100 if actual > 0 else 0
            return ((actual - anterior) / anterior) * 100

        variaciones = {
            'reservas': calcular_variacion(
                estadisticas['total_reservas'],
                estadisticas_anterior['total_reservas']
            ),
            'ingresos': calcular_variacion(
                estadisticas['ingresos_totales'],
                estadisticas_anterior['ingresos_totales']
            ),
            'ocupacion': calcular_variacion(
                estadisticas['tasa_ocupacion'],
                estadisticas_anterior['tasa_ocupacion']
            ),
            'cancelaciones': calcular_variacion(
                estadisticas['reservas_canceladas'],
                estadisticas_anterior['reservas_canceladas']
            ) * -1  # Invertir para que la reducción sea positiva
        }

        context = {
            'complejo': complejo,
            'estadisticas': estadisticas,
            'periodo': periodo,
            'titulo_periodo': titulo_periodo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'reservas_por_dia_labels': json.dumps(list(reservas_por_dia.keys())),
            'reservas_por_dia_data': json.dumps(list(reservas_por_dia.values())),
            'ingresos_por_cancha_labels': json.dumps(list(ingresos_por_cancha.keys())),
            'ingresos_por_cancha_data': json.dumps(list(ingresos_por_cancha.values())),
            'variaciones': variaciones,
            'reservas_recientes': reservas.order_by('-fecha_hora')[:10]
        }
        
        return render(request, 'canchas/estadisticas_complejo.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar las estadísticas: {str(e)}')
        return redirect('canchas:panel_admin')

@user_passes_test(es_dueno)
def gestionar_cancha(request, cancha_id=None):
    # Si es una cancha existente
    if cancha_id:
        cancha = get_object_or_404(Cancha, id=cancha_id, complejo__dueno=request.user.perfil_cliente)
    else:
        cancha = None
        complejo_id = request.GET.get('complejo_id')
        complejo = get_object_or_404(Complejo, id=complejo_id, dueno=request.user.perfil_cliente)
    
    if request.method == 'POST':
        try:
            if cancha:
                # Actualizar cancha existente
                cancha.nombre = request.POST.get('nombre')
                cancha.descripcion = request.POST.get('descripcion')
                cancha.precio_hora = request.POST.get('precio_hora')
                if 'foto' in request.FILES:
                    cancha.foto = request.FILES['foto']
            else:
                # Crear nueva cancha
                cancha = Cancha.objects.create(
                    complejo=complejo,
                    nombre=request.POST.get('nombre'),
                    descripcion=request.POST.get('descripcion'),
                    precio_hora=request.POST.get('precio_hora'),
                    foto=request.FILES.get('foto')
                )
            
            # Actualizar servicios
            servicios = {}
            for key in request.POST:
                if key.startswith('servicio_'):
                    servicio = key.replace('servicio_', '')
                    servicios[servicio] = True
            cancha.servicios = servicios
            
            cancha.save()
            messages.success(request, f'Cancha {"actualizada" if cancha_id else "creada"} correctamente')
            return redirect('canchas:panel_admin')
            
        except Exception as e:
            messages.error(request, f'Error al {"actualizar" if cancha_id else "crear"} la cancha: {str(e)}')
    
    context = {
        'cancha': cancha,
        'complejo': complejo if not cancha else cancha.complejo,
        'servicios_disponibles': [
            ('VESTUARIOS', 'Vestuarios'),
            ('DUCHAS', 'Duchas'),
            ('ILUMINACION', 'Iluminación'),
            ('ESTACIONAMIENTO', 'Estacionamiento'),
            ('BAR', 'Bar/Cantina'),
            ('WIFI', 'WiFi'),
        ]
    }
    return render(request, 'canchas/gestionar_cancha.html', context)

@user_passes_test(es_dueno)
def eliminar_cancha(request, cancha_id):
    cancha = get_object_or_404(Cancha, id=cancha_id, complejo__dueno=request.user.perfil_cliente)
    
    if request.method == 'POST':
        try:
            nombre_cancha = cancha.nombre
            cancha.delete()
            messages.success(request, f'La cancha {nombre_cancha} ha sido eliminada')
        except Exception as e:
            messages.error(request, f'Error al eliminar la cancha: {str(e)}')
    
    return redirect('canchas:panel_admin')

@user_passes_test(es_dueno)
def descargar_reporte(request, complejo_id):
    complejo = get_object_or_404(Complejo, id=complejo_id, dueno=request.user.perfil_cliente)
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Si no se proporcionan fechas válidas, usar último mes
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=30)
    
    filepath = ReporteService.generar_reporte_complejo(complejo, fecha_inicio, fecha_fin)
    
    return FileResponse(
        open(filepath, 'rb'),
        as_attachment=True,
        filename=f'reporte_{complejo.nombre}_{fecha_inicio}_{fecha_fin}.pdf'
    )

@login_required
@user_passes_test(es_dueno)
def generar_reporte_complejo(request, complejo_id):
    """Vista para generar y descargar el reporte del complejo"""
    try:
        complejo = Complejo.objects.get(id=complejo_id, dueno__usuario=request.user)
        
        # Obtener fechas del request o usar valores por defecto
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        
        # Generar el reporte
        ruta_archivo = ReporteService.generar_reporte_complejo(
            complejo=complejo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        if ruta_archivo and os.path.exists(ruta_archivo):
            response = FileResponse(
                open(ruta_archivo, 'rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="reporte_{complejo.nombre}.pdf"'
            return response
        else:
            messages.error(request, 'No se pudo generar el reporte. Por favor, intente más tarde.')
            return redirect('canchas:panel_admin')
            
    except Complejo.DoesNotExist:
        messages.error(request, 'No tienes permiso para acceder a este complejo.')
        return redirect('canchas:panel_admin')
    except Exception as e:
        messages.error(request, f'Error al generar el reporte: {str(e)}')
        return redirect('canchas:panel_admin')

@login_required
def descargar_comprobante_reserva(request, reserva_id):
    """Vista para generar y descargar el comprobante de una reserva"""
    try:
        # Verificar que el usuario sea el dueño de la reserva o del complejo
        reserva = Reserva.objects.select_related(
            'cancha__complejo__dueno__usuario',
            'jugador'
        ).get(id=reserva_id)
        
        if not (request.user == reserva.jugador or 
                request.user == reserva.cancha.complejo.dueno.usuario):
            messages.error(request, 'No tienes permiso para acceder a este comprobante.')
            return redirect('canchas:mis_reservas')
        
        # Generar el comprobante
        ruta_archivo = ReporteService.generar_reporte_reserva(reserva)
        
        if ruta_archivo and os.path.exists(ruta_archivo):
            response = FileResponse(
                open(ruta_archivo, 'rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="comprobante_reserva_{reserva.id}.pdf"'
            return response
        else:
            messages.error(request, 'No se pudo generar el comprobante. Por favor, intente más tarde.')
            return redirect('canchas:detalle_reserva', reserva_id=reserva.id)
            
    except Reserva.DoesNotExist:
        messages.error(request, 'La reserva no existe.')
        return redirect('canchas:mis_reservas')
    except Exception as e:
        messages.error(request, f'Error al generar el comprobante: {str(e)}')
        return redirect('canchas:detalle_reserva', reserva_id=reserva_id)

@login_required
@user_passes_test(es_dueno)
def exportar_estadisticas_excel(request, complejo_id):
    try:
        complejo = get_object_or_404(Complejo, id=complejo_id, dueno__usuario=request.user)
        
        # Obtener período de tiempo
        periodo = request.GET.get('periodo', 'semana')
        fecha_fin = timezone.now().date()
        
        if periodo == 'semana':
            fecha_inicio = fecha_fin - timedelta(days=7)
        elif periodo == 'mes':
            fecha_inicio = fecha_fin - timedelta(days=30)
        elif periodo == 'año':
            fecha_inicio = fecha_fin - timedelta(days=365)
        else:
            fecha_inicio = fecha_fin - timedelta(days=7)

        # Obtener estadísticas
        estadisticas = EstadisticasService.obtener_estadisticas_complejo(
            complejo=complejo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        # Crear workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Estadísticas"

        # Estilos
        titulo_style = Font(bold=True, size=14)
        header_style = Font(bold=True)
        header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

        # Título
        ws['A1'] = f"Estadísticas de {complejo.nombre}"
        ws['A1'].font = titulo_style
        ws.merge_cells('A1:D1')
        ws['A2'] = f"Período: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
        ws.merge_cells('A2:D2')

        # Resumen General
        ws['A4'] = "Resumen General"
        ws['A4'].font = header_style
        ws.merge_cells('A4:D4')

        headers = ['Métrica', 'Valor']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=5, column=col)
            cell.value = header
            cell.font = header_style
            cell.fill = header_fill

        # Datos del resumen
        resumen_data = [
            ('Total Reservas', estadisticas['total_reservas']),
            ('Ingresos Totales', f"${estadisticas['ingresos_totales']:.2f}"),
            ('Tasa de Ocupación', f"{estadisticas['tasa_ocupacion']:.1f}%"),
            ('Reservas Canceladas', estadisticas['reservas_canceladas']),
        ]

        for row, (metrica, valor) in enumerate(resumen_data, 6):
            ws.cell(row=row, column=1, value=metrica)
            ws.cell(row=row, column=2, value=valor)

        # Reservas por Cancha
        ws['A10'] = "Reservas por Cancha"
        ws['A10'].font = header_style
        ws.merge_cells('A10:D10')

        headers = ['Cancha', 'Reservas', 'Ingresos']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=11, column=col)
            cell.value = header
            cell.font = header_style
            cell.fill = header_fill

        # Datos por cancha
        row = 12
        for cancha in complejo.canchas.all():
            reservas_cancha = cancha.reservas.filter(
                fecha_hora__date__range=[fecha_inicio, fecha_fin]
            )
            ingresos_cancha = sum(
                r.monto_total for r in reservas_cancha if r.pagado
            )
            
            ws.cell(row=row, column=1, value=cancha.nombre)
            ws.cell(row=row, column=2, value=reservas_cancha.count())
            ws.cell(row=row, column=3, value=f"${ingresos_cancha:.2f}")
            row += 1

        # Ajustar anchos de columna
        for column in ws.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column[0].column_letter].width = adjusted_width

        # Crear respuesta HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=estadisticas_{complejo.nombre}_{periodo}.xlsx'

        # Guardar el archivo
        wb.save(response)

        return response
        
    except Exception as e:
        messages.error(request, f'Error al exportar las estadísticas: {str(e)}')
        return redirect('canchas:estadisticas_complejo', complejo_id=complejo_id)
