from django.urls import path
from . import views

app_name = 'canchas'

urlpatterns = [
    path('', views.home, name='home'),
    path('canchas/', views.lista_canchas, name='lista_canchas'),
    path('cancha/<int:pk>/', views.detalle_cancha, name='detalle_cancha'),
    path('reservar/<int:cancha_id>/', views.reservar_cancha, name='reservar_cancha'),
    # path('complejos/<int:complejo_id>/reporte/', views.reporte_complejo, name='reporte_complejo'),
    path('reservas/<int:reserva_id>/comprobante/', views.descargar_comprobante_reserva, name='comprobante_reserva'),
    path('complejos/<int:complejo_id>/estadisticas/', views.estadisticas_complejo, name='estadisticas_complejo'),
    path('complejos/<int:complejo_id>/exportar/', views.exportar_estadisticas_excel, name='exportar_estadisticas'),
]
