from django.contrib import admin
from .models import PerfilCliente, PerfilJugador, Equipo, Comentario

@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'telefono', 'razon_social', 'cuit']
    search_fields = ['usuario__username', 'razon_social', 'cuit']

@admin.register(PerfilJugador)
class PerfilJugadorAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'posicion', 'edad', 'penalizado']
    list_filter = ['posicion', 'penalizado']
    search_fields = ['usuario__username']

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'capitan', 'busca_jugadores']
    list_filter = ['busca_jugadores']
    search_fields = ['nombre']

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ['autor', 'receptor', 'puntuacion', 'fecha']
    list_filter = ['puntuacion']
