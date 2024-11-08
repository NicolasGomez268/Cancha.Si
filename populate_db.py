# populate_db.py
import os
import django
import random
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CanchaSi.settings')
django.setup()

from usuarios.models import User, PerfilCliente, PerfilJugador
from canchas.models import Complejo, Cancha, Reserva

def crear_usuarios():
    print('Creando usuarios...')
    usuarios = []
    for i in range(5):
        user = User.objects.create_user(
            username=f'cliente{i}',
            email=f'cliente{i}@example.com',
            password='cliente123',
            first_name=f'Nombre{i}',
            last_name=f'Apellido{i}'
        )
        # Crear perfil de cliente
        perfil = PerfilCliente.objects.create(
            usuario=user,
            telefono=f'11{i}1234567',
            direccion=f'Dirección Cliente {i}'
        )
        usuarios.append(user)
    return usuarios

def crear_complejos():
    print('Creando complejos...')
    nombres = ['Complejo Norte', 'Canchas del Sur', 'Centro Deportivo Este']
    complejos = []
    
    # Crear un usuario dueño
    dueno = User.objects.create_user(
        username='dueno',
        email='dueno@example.com',
        password='dueno123',
        first_name='Juan',
        last_name='Dueño'
    )
    perfil_dueno = PerfilCliente.objects.create(
        usuario=dueno,
        telefono='1123456789',
        direccion='Dirección Dueño'
    )
    
    for nombre in nombres:
        complejo = Complejo.objects.create(
            nombre=nombre,
            ubicacion=f'Ubicación de {nombre}',
            telefono='1123456789',
            dueno=perfil_dueno,
            stock_cantina=100,
            ingresos_mensuales=0
        )
        complejos.append(complejo)
    return complejos

def crear_canchas(complejos):
    print('Creando canchas...')
    for complejo in complejos:
        for i in range(3):
            Cancha.objects.create(
                complejo=complejo,
                nombre=f'Cancha {i+1}',
                precio_hora=random.randint(2000, 5000),
                servicios='Iluminación, Vestuarios',
                # foto es opcional, así que lo dejamos vacío
            )

def crear_reservas(usuarios, complejos):
    print('Creando reservas...')
    # Crear algunas reservas para los próximos días
    for _ in range(10):
        usuario = random.choice(usuarios)
        complejo = random.choice(complejos)
        cancha = random.choice(complejo.canchas.all())
        
        # Fecha aleatoria en los próximos 7 días
        fecha = datetime.now() + timedelta(
            days=random.randint(1, 7),
            hours=random.randint(8, 22)
        )
        
        Reserva.objects.create(
            cancha=cancha,
            jugador=usuario,
            fecha_hora=fecha,
            precio_total=cancha.precio_hora,
            sena_pagada=True,
            cancelada=False,
            turno_servicios=False  # o True si quieres algunas reservas con servicios
        )

def main():
    # Limpiar datos existentes
    print('Limpiando datos existentes...')
    Reserva.objects.all().delete()
    Cancha.objects.all().delete()
    Complejo.objects.all().delete()
    PerfilCliente.objects.all().delete()
    PerfilJugador.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    
    print('Creando datos de prueba...')
    usuarios = crear_usuarios()
    complejos = crear_complejos()
    crear_canchas(complejos)
    crear_reservas(usuarios, complejos)
    print('¡Datos de prueba creados exitosamente!')
    
    # Mostrar resumen
    print('\nResumen:')
    print(f'Usuarios creados: {User.objects.count()}')
    print(f'Complejos creados: {Complejo.objects.count()}')
    print(f'Canchas creadas: {Cancha.objects.count()}')
    print(f'Reservas creadas: {Reserva.objects.count()}')

if __name__ == '__main__':
    main()
