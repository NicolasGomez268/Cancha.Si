from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

class PerfilCliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_cliente')
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=200)
    razon_social = models.CharField(max_length=200)
    cuit = models.CharField(max_length=13)
    
    def __str__(self):
        return f"Dueño: {self.usuario.get_full_name()}"

class PerfilJugador(models.Model):
    POSICIONES = [
        ('ARQ', 'Arquero'),
        ('DEF', 'Defensor'),
        ('MED', 'Mediocampista'),
        ('DEL', 'Delantero'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_jugador')
    foto = models.ImageField(upload_to='perfiles/', null=True, blank=True)
    posicion = models.CharField(max_length=3, choices=POSICIONES)
    telefono = models.CharField(max_length=20)
    ubicacion = models.CharField(max_length=200)
    edad = models.IntegerField()
    penalizado = models.BooleanField(default=False)
    fin_penalizacion = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"Jugador: {self.usuario.get_full_name()}"

class Equipo(models.Model):
    nombre = models.CharField(max_length=200)
    capitan = models.ForeignKey(User, on_delete=models.CASCADE, related_name='equipos_capitan')
    jugadores = models.ManyToManyField(User, related_name='equipos')
    busca_jugadores = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nombre

class Comentario(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comentarios_realizados')
    receptor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comentarios_recibidos')
    texto = models.TextField()
    puntuacion = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    fecha = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Comentario de {self.autor} a {self.receptor}'

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('RESERVA', 'Nueva Reserva'),
        ('PAGO', 'Pago Recibido'),
        ('CANCELACION', 'Cancelación'),
        ('RECORDATORIO', 'Recordatorio'),
        ('SISTEMA', 'Sistema')
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=100)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)
    url = models.CharField(max_length=200, blank=True)  # URL relacionada con la notificación
    
    class Meta:
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.tipo} - {self.titulo}"

class PreferenciasNotificaciones(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferencias_notificaciones')
    email_reservas = models.BooleanField(default=True)
    email_pagos = models.BooleanField(default=True)
    email_cancelaciones = models.BooleanField(default=True)
    email_recordatorios = models.BooleanField(default=True)
    email_sistema = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Preferencias de notificaciones'
        verbose_name_plural = 'Preferencias de notificaciones'

    def __str__(self):
        return f'Preferencias de {self.usuario.username}'
