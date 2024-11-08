from django.contrib import admin
from .models import Complejo, Cancha, Reserva

@admin.register(Complejo)
class ComplejoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'dueno', 'ubicacion', 'telefono']
    search_fields = ['nombre', 'ubicacion']

@admin.register(Cancha)
class CanchaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'complejo', 'precio_hora']
    list_filter = ['complejo']
    search_fields = ['nombre']

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['jugador', 'cancha', 'fecha_hora', 'precio_total', 'sena_pagada', 'cancelada']
    list_filter = ['sena_pagada', 'cancelada']
    search_fields = ['jugador__username', 'cancha__nombre']
