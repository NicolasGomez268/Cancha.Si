from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from usuarios.services import NotificacionService
from .models import Reserva, Complejo
from .services import ReporteService

@shared_task
def enviar_recordatorios():
    """Envía recordatorios 24h antes de la reserva"""
    manana = timezone.now() + timedelta(days=1)
    
    reservas_manana = Reserva.objects.filter(
        fecha_hora__date=manana.date(),
        cancelada=False
    ).select_related('jugador', 'cancha', 'cancha__complejo')
    
    for reserva in reservas_manana:
        NotificacionService.enviar_notificacion(
            usuario=reserva.jugador,
            tipo='RECORDATORIO',
            titulo='Recordatorio de reserva para mañana',
            mensaje=f'Te recordamos tu reserva mañana en {reserva.cancha.nombre} a las {reserva.fecha_hora.strftime("%H:%M")}',
            url=f'/canchas/reservas/{reserva.id}/'
        )
    
    return f"Enviados {len(reservas_manana)} recordatorios"

@shared_task
def generar_reporte_diario():
    """Genera y envía reportes diarios a los dueños de complejos"""
    hoy = timezone.now().date()
    
    for complejo in Complejo.objects.select_related('dueno__usuario').all():
        try:
            # Generar reporte PDF
            reporte_path = ReporteService.generar_reporte_complejo(
                complejo=complejo,
                fecha_inicio=hoy,
                fecha_fin=hoy
            )
            
            # Enviar notificación y email al dueño
            context = {
                'complejo': complejo,
                'fecha': hoy,
                'total_reservas': complejo.reservas.filter(fecha_hora__date=hoy).count(),
                'ingresos_dia': complejo.calcular_ingresos_dia(hoy)
            }
            
            html_content = render_to_string('emails/reporte_diario.html', context)
            
            send_mail(
                subject=f'Reporte diario - {complejo.nombre}',
                message='',
                from_email=None,  # Usar el default configurado
                recipient_list=[complejo.dueno.usuario.email],
                html_message=html_content,
                attachments=[(
                    f'reporte_{complejo.nombre}_{hoy}.pdf',
                    open(reporte_path, 'rb').read(),
                    'application/pdf'
                )]
            )
            
        except Exception as e:
            print(f"Error generando reporte para {complejo.nombre}: {str(e)}")
    
    return "Reportes diarios generados"

@shared_task
def verificar_ocupacion():
    """Verifica la ocupación de los complejos y envía alertas"""
    for complejo in Complejo.objects.select_related('dueno__usuario').all():
        tasa_ocupacion = complejo.calcular_tasa_ocupacion()
        
        if tasa_ocupacion < 30:  # Si la ocupación es menor al 30%
            NotificacionService.enviar_notificacion(
                usuario=complejo.dueno.usuario,
                tipo='SISTEMA',
                titulo='Alerta de baja ocupación',
                mensaje=f'Tu complejo {complejo.nombre} tiene una tasa de ocupación del {tasa_ocupacion}%. '
                       f'Considera realizar promociones para aumentar las reservas.',
                url=f'/canchas/complejos/{complejo.id}/estadisticas/'
            )
    
    return "Verificación de ocupación completada"

@shared_task
def limpiar_reservas_vencidas():
    """Limpia reservas vencidas sin pago"""
    limite = timezone.now() - timedelta(hours=1)
    
    reservas_vencidas = Reserva.objects.filter(
        fecha_creacion__lt=limite,
        estado_pago='PENDIENTE'
    )
    
    for reserva in reservas_vencidas:
        NotificacionService.enviar_notificacion(
            usuario=reserva.jugador,
            tipo='SISTEMA',
            titulo='Reserva cancelada por falta de pago',
            mensaje=f'Tu reserva para {reserva.cancha.nombre} ha sido cancelada por falta de pago.',
            url=f'/canchas/reservas/{reserva.id}/'
        )
        
        reserva.cancelada = True
        reserva.save()
    
    return f"Limpiadas {reservas_vencidas.count()} reservas vencidas"
