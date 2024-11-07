from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    dni = models.CharField(max_length=20)
    direccion = models.CharField(max_length=200)
    fecha_registro = models.DateTimeField(auto_now_add=True)
