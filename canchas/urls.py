from django.urls import path
from . import views
from .views import hacer_reserva

app_name = 'canchas'

urlpatterns = [
    path('', views.home, name='home'),
    path('canchas/', views.lista_canchas, name='lista_canchas'),
    path('cancha/<int:pk>/', views.detalle_cancha, name='detalle_cancha'),
    path('cancha/<int:cancha_id>/reservar/', views.reservar_cancha, name='reservar_cancha'),
    path('reservas/<int:reserva_id>/comprobante/', views.descargar_comprobante_reserva, name='comprobante_reserva'),
    path('complejos/<int:complejo_id>/estadisticas/', views.estadisticas_complejo, name='estadisticas_complejo'),
    path('complejos/<int:complejo_id>/exportar/', views.exportar_estadisticas_excel, name='exportar_estadisticas_excel'),
    path('', views.lista_canchas, name='lista_canchas'),  # Vista principal
    path('canchas/', views.lista_canchas, name='lista_canchas_alt'),  # URL alternativa
    path('reservar/<int:cancha_id>/', views.hacer_reserva, name='hacer_reserva'),
    path('reservas/', views.lista_reservas, name='nombre_de_la_url_de_reservas'),  # Cambia 'lista_reservas' por el nombre de tu vista
    path('confirmacion/<int:reserva_id>/', views.confirmacion_reserva, name='confirmacion_reserva'),
    path('perfil/dueno/', views.perfil_dueño, name='perfil_dueno'),
    path('complejo/<int:complejo_id>/editar/', views.editar_complejo, name='editar_complejo'),
    path('cancha/<int:cancha_id>/editar/', views.editar_cancha, name='editar_cancha'),
]
