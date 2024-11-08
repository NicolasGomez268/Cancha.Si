from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Notificacion

class NotificacionService:
    @staticmethod
    def enviar_notificacion(usuario, tipo, titulo, mensaje, url='', enviar_email=True):
        # Crear notificación en la base de datos
        notificacion = Notificacion.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            url=url
        )
        
        # Enviar notificación en tiempo real
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{usuario.id}",
            {
                'type': 'notificacion',
                'tipo': tipo,
                'titulo': titulo,
                'mensaje': mensaje,
                'url': url,
                'fecha': timezone.now().isoformat(),
            }
        )
        
        # Enviar email si está habilitado
        if enviar_email and usuario.email:
            try:
                NotificacionService.enviar_email_notificacion(
                    usuario=usuario,
                    tipo=tipo,
                    titulo=titulo,
                    mensaje=mensaje,
                    url=url
                )
            except Exception as e:
                print(f"Error al enviar email: {str(e)}")
        
        return notificacion

    @staticmethod
    def enviar_email_notificacion(usuario, tipo, titulo, mensaje, url):
        # Preparar contexto para el template
        context = {
            'usuario': usuario,
            'titulo': titulo,
            'mensaje': mensaje,
            'tipo': tipo,
            'url': url,
            'fecha': timezone.now(),
        }
        
        # Renderizar templates
        html_message = render_to_string('emails/notificacion.html', context)
        plain_message = strip_tags(html_message)
        
        # Enviar email
        send_mail(
            subject=titulo,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.email],
            html_message=html_message,
            fail_silently=False,
        )

    @staticmethod
    def obtener_notificaciones_no_leidas(usuario):
        return Notificacion.objects.filter(
            usuario=usuario,
            leida=False
        ).order_by('-fecha')

    @staticmethod
    def marcar_como_leida(notificacion_id, usuario):
        notificacion = Notificacion.objects.get(
            id=notificacion_id,
            usuario=usuario
        )
        notificacion.leida = True
        notificacion.save()
        return notificacion

    @staticmethod
    def marcar_todas_como_leidas(usuario):
        Notificacion.objects.filter(
            usuario=usuario,
            leida=False
        ).update(leida=True)

    @staticmethod
    def notificar_nueva_reserva(reserva):
        # Notificar al jugador
        NotificacionService.enviar_notificacion(
            usuario=reserva.jugador,
            tipo='RESERVA',
            titulo='¡Reserva confirmada!',
            mensaje=f'Tu reserva para {reserva.cancha.nombre} el {reserva.fecha_hora.strftime("%d/%m/%Y %H:%M")}',
            url=reverse('canchas:detalle_reserva', args=[reserva.id])
        )
        
        # Notificar al dueño
        NotificacionService.enviar_notificacion(
            usuario=reserva.cancha.complejo.dueno.usuario,
            tipo='RESERVA',
            titulo='Nueva reserva recibida',
            mensaje=f'Nueva reserva para {reserva.cancha.nombre} el {reserva.fecha_hora.strftime("%d/%m/%Y %H:%M")}',
            url=reverse('canchas:detalle_reserva', args=[reserva.id])
        )
    
    @staticmethod
    def notificar_pago(pago):
        NotificacionService.enviar_notificacion(
            usuario=pago.reserva.jugador,
            tipo='PAGO',
            titulo='Pago procesado',
            mensaje=f'Tu pago de ${pago.monto} ha sido procesado correctamente.',
            url=reverse('canchas:detalle_reserva', args=[pago.reserva.id])
        )
    
    @staticmethod
    def notificar_cancelacion(reserva):
        # Notificar al jugador
        NotificacionService.enviar_notificacion(
            usuario=reserva.jugador,
            tipo='CANCELACION',
            titulo='Reserva cancelada',
            mensaje=f'Tu reserva para {reserva.cancha.nombre} ha sido cancelada.',
            url=reverse('canchas:detalle_reserva', args=[reserva.id])
        )
        
        # Notificar al dueño
        NotificacionService.enviar_notificacion(
            usuario=reserva.cancha.complejo.dueno.usuario,
            tipo='CANCELACION',
            titulo='Reserva cancelada',
            mensaje=f'Una reserva para {reserva.cancha.nombre} ha sido cancelada.',
            url=reverse('canchas:detalle_reserva', args=[reserva.id])
        )
    
    @staticmethod
    def enviar_recordatorio_reserva():
        """Envía recordatorios 24h antes de la reserva"""
        manana = timezone.now() + timezone.timedelta(days=1)
        from canchas.models import Reserva
        
        reservas_manana = Reserva.objects.filter(
            fecha_hora__date=manana.date(),
            cancelada=False
        )
        
        for reserva in reservas_manana:
            NotificacionService.enviar_notificacion(
                usuario=reserva.jugador,
                tipo='RECORDATORIO',
                titulo='Recordatorio de reserva',
                mensaje=f'Recuerda tu reserva mañana en {reserva.cancha.nombre} a las {reserva.fecha_hora.strftime("%H:%M")}',
                url=reverse('canchas:detalle_reserva', args=[reserva.id])
            )
