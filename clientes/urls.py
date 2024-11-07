from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='clientes_home'),  # Ruta principal de la aplicación
    # Agrega más rutas según tus vistas
]
