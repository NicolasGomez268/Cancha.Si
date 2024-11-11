from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from .models import PerfilJugador, PerfilCliente, Equipo, Notificacion
from canchas.models import Complejo, Cancha
from datetime import date
from django.http import JsonResponse

def registro(request):
    if request.method == 'POST':
        tipo_usuario = request.POST.get('tipo_usuario')
        
        try:
            with transaction.atomic():
                # Crear usuario base
                user = User.objects.create_user(
                    username=request.POST.get('email'),
                    email=request.POST.get('email'),
                    password=request.POST.get('password1')
                )
                
                if tipo_usuario == 'jugador':
                    user.first_name = request.POST.get('nombre')
                    user.last_name = request.POST.get('apellido')
                    user.save()
                    
                    # Crear perfil jugador
                    PerfilJugador.objects.create(
                        usuario=user,
                        posicion=request.POST.get('posicion'),
                        telefono=request.POST.get('telefono', ''),
                        ubicacion=request.POST.get('ubicacion', ''),
                        edad=request.POST.get('edad', 18)
                    )
                    
                else:  # cliente
                    # Crear perfil cliente
                    PerfilCliente.objects.create(
                        usuario=user,
                        razon_social=request.POST.get('razon_social'),
                        cuit=request.POST.get('cuit'),
                        telefono=request.POST.get('telefono'),
                        direccion=request.POST.get('direccion', '')
                    )
                
                login(request, user)
                messages.success(request, '¡Registro exitoso!')
                return redirect('usuarios:perfil')
                
        except Exception as e:
            messages.error(request, f'Error en el registro: {str(e)}')
            
    return render(request, 'usuarios/registro.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')  # usamos email como username
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, '¡Bienvenido!')
            return redirect('usuarios:perfil')
        else:
            messages.error(request, 'Credenciales inválidas')
            
    return render(request, 'usuarios/login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión')
    return redirect('/')

@login_required
def perfil(request):
    # Determinar tipo de usuario y cargar datos relevantes
    try:
        perfil_jugador = request.user.perfil_jugador
        context = {
            'perfil': perfil_jugador,
            'reservas': request.user.reservas.all().order_by('-fecha_hora')
        }
        return render(request, 'usuarios/perfil_jugador.html', context)
    except PerfilJugador.DoesNotExist:
        try:
            perfil_cliente = request.user.perfil_cliente
            # Calcular estadísticas para el cliente
            total_canchas = sum(complejo.canchas.count() for complejo in perfil_cliente.complejos.all())
            reservas_hoy = sum(
                complejo.canchas.filter(reservas__fecha_hora__date=date.today()).count()
                for complejo in perfil_cliente.complejos.all()
            )
            context = {
                'perfil': perfil_cliente,
                'total_canchas': total_canchas,
                'reservas_hoy': reservas_hoy
            }
            return render(request, 'usuarios/perfil_cliente.html', context)
        except PerfilCliente.DoesNotExist:
            messages.error(request, 'No se encontró un perfil válido')
            return redirect('usuarios:registro')

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        try:
            if hasattr(request.user, 'perfil_jugador'):
                perfil = request.user.perfil_jugador
                perfil.posicion = request.POST.get('posicion')
                perfil.telefono = request.POST.get('telefono')
                perfil.ubicacion = request.POST.get('ubicacion')
                perfil.edad = request.POST.get('edad')
                if 'foto' in request.FILES:
                    perfil.foto = request.FILES['foto']
                perfil.save()
                
            else:  # perfil cliente
                perfil = request.user.perfil_cliente
                perfil.razon_social = request.POST.get('razon_social')
                perfil.telefono = request.POST.get('telefono')
                perfil.direccion = request.POST.get('direccion')
                perfil.save()
                
            messages.success(request, 'Perfil actualizado correctamente')
            return redirect('usuarios:perfil')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar perfil: {str(e)}')
            
    # GET request
    context = {
        'perfil': request.user.perfil_jugador if hasattr(request.user, 'perfil_jugador') else request.user.perfil_cliente
    }
    return render(request, 'usuarios/editar_perfil.html', context)

@login_required
def nuevo_complejo(request):
    if not hasattr(request.user, 'perfil_cliente'):
        messages.error(request, 'No tienes permisos para esta acción')
        return redirect('home')
        
    if request.method == 'POST':
        try:
            Complejo.objects.create(
                dueno=request.user.perfil_cliente,
                nombre=request.POST.get('nombre'),
                ubicacion=request.POST.get('ubicacion'),
                telefono=request.POST.get('telefono')
            )
            messages.success(request, 'Complejo creado exitosamente')
        except Exception as e:
            messages.error(request, f'Error al crear complejo: {str(e)}')
            
    return redirect('usuarios:perfil')

@login_required
def notificaciones(request):
    notificaciones = request.user.notificaciones.all()
    return render(request, 'usuarios/notificaciones.html', {
        'notificaciones': notificaciones
    })

@login_required
def marcar_notificacion_leida(request, notificacion_id):
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
    notificacion.leida = True
    notificacion.save()
    return JsonResponse({'status': 'ok'})

@login_required
def marcar_todas_leidas(request):
    request.user.notificaciones.filter(leida=False).update(leida=True)
    return JsonResponse({'status': 'ok'})
