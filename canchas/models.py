from django.db import models
from django.contrib.auth.models import User
from usuarios.models import PerfilCliente
from decimal import Decimal
from django.utils import timezone

# Create your models here.

class Complejo(models.Model):
    dueno = models.ForeignKey(PerfilCliente, on_delete=models.CASCADE, related_name='complejos')
    nombre = models.CharField(max_length=200)
    ubicacion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    stock_cantina = models.JSONField(default=dict)
    ingresos_mensuales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hora_apertura = models.TimeField(
        verbose_name="Hora de apertura",
        default=timezone.datetime.strptime('08:00', '%H:%M').time()
    )
    hora_cierre = models.TimeField(
        verbose_name="Hora de cierre",
        default=timezone.datetime.strptime('22:00', '%H:%M').time()
    )
    
    class Meta:
        verbose_name = "Complejo"
        verbose_name_plural = "Complejos"
    
    def __str__(self):
        return self.nombre

class Cancha(models.Model):
    complejo = models.ForeignKey(Complejo, on_delete=models.CASCADE, related_name='canchas')
    foto = models.ImageField(upload_to='canchas/')
    nombre = models.CharField(max_length=200)
    precio_hora = models.DecimalField(max_digits=8, decimal_places=2)
    servicios = models.JSONField(default=dict)  # Para parrillas, mesas, cantina, etc.
    
    def __str__(self):
        return f'{self.nombre} - {self.complejo.nombre}'

class Pago(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]
    
    TIPO_CHOICES = [
        ('SENA', 'Seña'),
        ('TOTAL', 'Pago Total'),
    ]
    
    reserva = models.ForeignKey('Reserva', on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='PENDIENTE')
    tipo = models.CharField(max_length=5, choices=TIPO_CHOICES)
    referencia_pago = models.CharField(max_length=100, blank=True)  # Para guardar ID de transacción
    
    def __str__(self):
        return f"Pago {self.tipo} - Reserva {self.reserva.id}"

class Reserva(models.Model):
    TURNO_CHOICES = [
        ('MD', 'Medio día'),
        ('N', 'Noche'),
    ]
    
    jugador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservas')
    cancha = models.ForeignKey(Cancha, on_delete=models.CASCADE, related_name='reservas')
    fecha_hora = models.DateTimeField()
    precio_total = models.DecimalField(max_digits=8, decimal_places=2)
    sena_pagada = models.BooleanField(default=False)
    cancelada = models.BooleanField(default=False)
    hora_cancelacion = models.DateTimeField(null=True, blank=True)
    turno_servicios = models.CharField(max_length=2, choices=TURNO_CHOICES, null=True, blank=True)

    @property
    def monto_sena(self):
        return self.precio_total * Decimal('0.5')  # 50% del total
    
    @property
    def estado_pago(self):
        pagos = self.pagos.filter(estado='APROBADO')
        if not pagos.exists():
            return 'PENDIENTE'
        elif pagos.filter(tipo='TOTAL').exists():
            return 'PAGADO'
        elif pagos.filter(tipo='SENA').exists():
            return 'SEÑADO'
        return 'PENDIENTE'

    def __str__(self):
        return f'Reserva de {self.jugador.get_full_name()} - {self.cancha.nombre}'
