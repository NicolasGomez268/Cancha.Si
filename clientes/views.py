from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return HttpResponse("Bienvenido al área de clientes.")

def home(request):
    return render(request, 'clientes/home.html')
