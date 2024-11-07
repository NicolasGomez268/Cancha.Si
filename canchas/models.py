from django.db import models

# Create your models here.

class Cancha(models.Model):
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50)  # Ejemplo: Fútbol 5, Fútbol 7, etc.
    precio_hora = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
