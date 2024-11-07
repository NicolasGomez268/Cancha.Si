from django.shortcuts import render
from .models import Cancha


# Create your views here.
from django.http import HttpResponse

def home(request):
    return render(request, 'home.html')


def lista(request):
    return render(request, 'canchas/lista.html')

def lista_canchas(request):
    canchas = Cancha.objects.all()
    return render(request, 'canchas/lista_canchas.html', {'canchas': canchas})
