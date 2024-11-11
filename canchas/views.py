from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import FileResponse
from .models import Cancha, Reserva, Complejo, Pago
from .services import ReporteService, EstadisticasService, exportar_estadisticas_complejo_excel
from usuarios.services import NotificacionService
from django.urls import reverse
import os
import json
from django.core.serializers.json import DjangoJSONEncoder
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from django.http import HttpResponse
from django.db import models
from django.db.models.functions import TruncMonth
from datetime import datetime
from django.shortcuts import render
from django.db.models import Q
import locale
from django.utils import translation
from django.utils.formats import date_format
from .models import Cancha


def home(request):
    # Obtener todas las canchas
    canchas = Cancha.objects.all()
    
    # Obtener parámetros de filtro básicos
    ubicacion = request.GET.get('ubicacion', '')
    nombre = request.GET.get('nombre', '')
    
    # Aplicar filtros si existen
    if ubicacion:
        canchas = canchas.filter(complejo__ubicacion__icontains=ubicacion)
    if nombre:
        canchas = canchas.filter(
            Q(nombre__icontains=nombre) | 
            Q(complejo__nombre__icontains=nombre)
        )
    
    return render(request, 'canchas/home.html', {
        'canchas': canchas,
    })

@login_required
def lista_canchas(request):
    # Forzar el idioma español
    translation.activate('es')
    
    # Obtener fecha y hora seleccionadas
    selected_date = request.GET.get('fecha', datetime.now().date().strftime('%Y-%m-%d'))
    selected_hour = int(request.GET.get('hora', '8'))

    # Obtener parámetros de filtro básicos
    ubicacion = request.GET.get('ubicacion', '')
    nombre = request.GET.get('nombre', '')
    ordenar = request.GET.get('ordenar', '')

    # Iniciar el queryset
    canchas = Cancha.objects.all()

    # Convertir fecha string a objeto date
    fecha_seleccionada = datetime.strptime(selected_date, '%Y-%m-%d').date()

    # Filtrar canchas disponibles
    todas_canchas = canchas
    canchas_disponibles = [
        cancha for cancha in todas_canchas 
        if cancha.esta_disponible(fecha_seleccionada, selected_hour)
    ]

    # Aplicar filtros de búsqueda
    if ubicacion:
        canchas_disponibles = [c for c in canchas_disponibles 
                             if ubicacion.lower() in c.complejo.ubicacion.lower()]
    
    if nombre:
        canchas_disponibles = [c for c in canchas_disponibles 
                             if nombre.lower() in c.nombre.lower() or 
                             nombre.lower() in c.complejo.nombre.lower()]

    # Aplicar ordenamiento
    if ordenar:
        if ordenar == 'precio_asc':
            canchas_disponibles.sort(key=lambda x: x.precio_hora)
        elif ordenar == 'precio_desc':
            canchas_disponibles.sort(key=lambda x: x.precio_hora, reverse=True)
        elif ordenar == 'nombre':
            canchas_disponibles.sort(key=lambda x: x.nombre)

    # Generar fechas para el calendario
    today = datetime.now().date()
    dates = [today + timedelta(days=x) for x in range(30)]
    
    # Generar horas disponibles
    hours = range(8, 24)

    context = {
        'canchas': canchas_disponibles,
        'dates': dates,
        'hours': hours,
        'selected_date': fecha_seleccionada,
        'selected_hour': selected_hour
    }
    
    return render(request, 'canchas/lista_canchas.html', context)

@login_required
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
    cancha = get_object_or_404(Cancha, id=cancha_id)
    complejo = cancha.complejo
    fecha_actual = datetime.now().date()
    
    # Obtener fecha seleccionada del GET, si no hay usa la fecha actual
    fecha_seleccionada = request.GET.get('fecha')
    if fecha_seleccionada:
        fecha_seleccionada = datetime.strptime(fecha_seleccionada, '%Y-%m-%d').date()
    else:
        fecha_seleccionada = fecha_actual

    # Obtener reservas existentes para la fecha seleccionada
    reservas_del_dia = Reserva.objects.filter(
        cancha=cancha,
        fecha_hora__date=fecha_seleccionada,
        cancelada=False
    )

    # Crear lista de horarios ocupados
    horas_ocupadas = set()
    for reserva in reservas_del_dia:
        hora_inicio = reserva.fecha_hora.hour
        for i in range(reserva.duracion):  # duracion en horas
            horas_ocupadas.add(hora_inicio + i)

    # Generar lista de horarios disponibles
    horarios_disponibles = []
    for hora in range(complejo.hora_apertura.hour, complejo.hora_cierre.hour):
        disponible = hora not in horas_ocupadas
        horarios_disponibles.append({
            'hora': hora,
            'hora_formato': f"{hora:02d}:00",
            'disponible': disponible
        })

    context = {
        'cancha': cancha,
        'complejo': complejo,
        'fecha_seleccionada': fecha_seleccionada,
        'fecha_minima': fecha_actual,
        'horarios_disponibles': horarios_disponibles,
    }
    
    return render(request, 'canchas/reservar.html', context)

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
    """Vista para mostrar estadísticas del complejo"""
    complejo = get_object_or_404(Complejo, id=complejo_id)
    
    # Verificar que el usuario sea el dueño del complejo
    if request.user.perfilcliente != complejo.dueno:
        messages.error(request, 'No tienes permiso para ver estas estadísticas.')
        return redirect('canchas:lista_complejos')
    
    # Estadísticas generales
    total_canchas = complejo.canchas.count()
    total_reservas = Reserva.objects.filter(cancha__complejo=complejo).count()
    reservas_activas = Reserva.objects.filter(cancha__complejo=complejo, cancelada=False).count()
    
    # Estadísticas por mes
    stats_mensuales = (
        Reserva.objects
        .filter(cancha__complejo=complejo)
        .annotate(mes=TruncMonth('fecha_hora'))
        .values('mes')
        .annotate(
            total=models.Count('id'),
            canceladas=models.Count('id', filter=models.Q(cancelada=True)),
            ingresos=models.Sum('precio_total', filter=models.Q(cancelada=False))
        )
        .order_by('-mes')
    )
    
    context = {
        'complejo': complejo,
        'total_canchas': total_canchas,
        'total_reservas': total_reservas,
        'reservas_activas': reservas_activas,
        'stats_mensuales': stats_mensuales,
    }
    
    return render(request, 'canchas/estadisticas_complejo.html', context)

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
        complejo = Complejo.objects.get(id=complejo_id)
        
        # Verificar que el usuario sea el dueño del complejo
        if request.user.perfilcliente != complejo.dueno:
            messages.error(request, 'No tienes permiso para exportar estas estadísticas.')
            return redirect('canchas:detalle_complejo', complejo_id=complejo_id)
        
        # Generar el archivo Excel
        filename = exportar_estadisticas_complejo_excel(complejo_id)
        
        # Ruta completa al archivo
        filepath = os.path.join('media', 'reportes', filename)
        
        # Devolver el archivo como respuesta
        response = FileResponse(
            open(filepath, 'rb'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Complejo.DoesNotExist:
        messages.error(request, 'El complejo no existe.')
        return redirect('canchas:lista_complejos')
    except Exception as e:
        messages.error(request, f'Error al exportar estadísticas: {str(e)}')
        return redirect('canchas:detalle_complejo', complejo_id=complejo_id)
