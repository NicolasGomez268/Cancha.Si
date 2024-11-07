from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_canchas, name='lista_canchas'),
]
