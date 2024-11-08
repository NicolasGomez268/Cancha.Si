from django import forms
from .models import Perfil

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['nombre', 'foto', 'posicion', 'telefono', 'ubicacion', 'edad']
