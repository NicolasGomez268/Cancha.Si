from django.template.loader import render_to_string
from django.utils import timezone
from datetime import datetime, timedelta
import os

try:
    from weasyprint import HTML
    WEASYPRINT_ENABLED = True
except OSError:
    WEASYPRINT_ENABLED = False
    print("WeasyPrint no está disponible. Los reportes PDF no funcionarán.")

class ReporteService:
    @staticmethod
    def generar_reporte_complejo(complejo, fecha_inicio=None, fecha_fin=None):
        """
        Genera un reporte PDF para un complejo deportivo en un rango de fechas.
        Si no se especifican fechas, genera el reporte del último mes.
        """
        if not WEASYPRINT_ENABLED:
            return None

        # Si no se especifican fechas, usar el último mes
        if not fecha_fin:
            fecha_fin = timezone.now().date()
        if not fecha_inicio:
            fecha_inicio = fecha_fin - timedelta(days=30)

        # Obtener datos para el reporte
        reservas = complejo.reservas.filter(
            fecha_hora__date__range=[fecha_inicio, fecha_fin],
            cancelada=False
        ).select_related('cancha', 'jugador')

        # Calcular estadísticas
        total_reservas = reservas.count()
        ingresos_totales = sum(r.monto_total for r in reservas if r.pagado)
        canchas_mas_reservadas = complejo.canchas.all().order_by('-reservas__count')[:5]
        
        # Preparar datos por día
        datos_diarios = {}
        for reserva in reservas:
            fecha = reserva.fecha_hora.date()
            if fecha not in datos_diarios:
                datos_diarios[fecha] = {
                    'total_reservas': 0,
                    'ingresos': 0,
                }
            datos_diarios[fecha]['total_reservas'] += 1
            if reserva.pagado:
                datos_diarios[fecha]['ingresos'] += reserva.monto_total

        # Preparar contexto para el template
        context = {
            'complejo': complejo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'fecha_generacion': timezone.now(),
            'total_reservas': total_reservas,
            'ingresos_totales': ingresos_totales,
            'promedio_diario': ingresos_totales / (fecha_fin - fecha_inicio).days if total_reservas > 0 else 0,
            'canchas_mas_reservadas': canchas_mas_reservadas,
            'datos_diarios': sorted(datos_diarios.items()),
            'reservas': reservas,
        }

        # Renderizar el HTML
        html_string = render_to_string('canchas/reportes/reporte_complejo.html', context)

        # Crear el PDF
        html = HTML(string=html_string)
        
        # Crear directorio para reportes si no existe
        reportes_dir = os.path.join('media', 'reportes')
        os.makedirs(reportes_dir, exist_ok=True)
        
        # Generar nombre de archivo
        nombre_archivo = f'reporte_{complejo.id}_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}.pdf'
        ruta_archivo = os.path.join(reportes_dir, nombre_archivo)
        
        # Guardar PDF
        html.write_pdf(ruta_archivo)
        
        return ruta_archivo

    @staticmethod
    def generar_reporte_reserva(reserva):
        """
        Genera un PDF con los detalles de una reserva específica
        """
        if not WEASYPRINT_ENABLED:
            return None

        context = {
            'reserva': reserva,
            'fecha_generacion': timezone.now(),
        }

        html_string = render_to_string('canchas/reportes/comprobante_reserva.html', context)
        html = HTML(string=html_string)
        
        reportes_dir = os.path.join('media', 'reportes', 'comprobantes')
        os.makedirs(reportes_dir, exist_ok=True)
        
        nombre_archivo = f'comprobante_reserva_{reserva.id}.pdf'
        ruta_archivo = os.path.join(reportes_dir, nombre_archivo)
        
        html.write_pdf(ruta_archivo)
        return ruta_archivo

class EstadisticasService:
    @staticmethod
    def obtener_estadisticas_complejo(complejo, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene estadísticas detalladas de un complejo para un rango de fechas
        """
        if not fecha_fin:
            fecha_fin = timezone.now().date()
        if not fecha_inicio:
            fecha_inicio = fecha_fin - timedelta(days=30)

        reservas = complejo.reservas.filter(
            fecha_hora__date__range=[fecha_inicio, fecha_fin]
        )

        return {
            'total_reservas': reservas.count(),
            'ingresos_totales': sum(r.monto_total for r in reservas if r.pagado),
            'reservas_canceladas': reservas.filter(cancelada=True).count(),
            'tasa_ocupacion': complejo.calcular_tasa_ocupacion(fecha_inicio, fecha_fin),
            'horarios_populares': complejo.obtener_horarios_populares(),
            'canchas_mas_reservadas': complejo.obtener_canchas_mas_reservadas(),
        }
