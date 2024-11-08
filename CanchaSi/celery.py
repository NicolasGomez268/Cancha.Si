import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Establecer la configuración de Django por defecto para celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CanchaSi.settings')

# Crear la aplicación celery
app = Celery('CanchaSi')

# Configurar usando el objeto settings de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Cargar tareas de todas las aplicaciones Django registradas
app.autodiscover_tasks()

# Configurar tareas periódicas
app.conf.beat_schedule = {
    'enviar-recordatorios-diarios': {
        'task': 'canchas.tasks.enviar_recordatorios',
        'schedule': crontab(hour=9, minute=0),  # Ejecutar todos los días a las 9:00 AM
    },
    'generar-reportes-diarios': {
        'task': 'canchas.tasks.generar_reporte_diario',
        'schedule': crontab(hour=23, minute=59),  # Ejecutar todos los días a las 23:59
    },
    'verificar-ocupacion': {
        'task': 'canchas.tasks.verificar_ocupacion',
        'schedule': crontab(hour='*/4'),  # Ejecutar cada 4 horas
    },
}
