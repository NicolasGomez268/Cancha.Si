import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

class NotificacionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.room_name = f"user_{self.scope['user'].id}"
            await self.channel_layer.group_add(
                self.room_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(
                self.room_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Manejar mensajes recibidos del WebSocket (si es necesario)
        pass

    async def notificacion(self, event):
        # Enviar notificación al WebSocket
        await self.send(text_data=json.dumps({
            'tipo': event['tipo'],
            'titulo': event['titulo'],
            'mensaje': event['mensaje'],
            'url': event.get('url', ''),
            'fecha': event.get('fecha', ''),
        }))
