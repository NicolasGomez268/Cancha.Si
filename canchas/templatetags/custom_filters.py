from django import template

register = template.Library()

@register.filter
def diccionario_dias(day):
    dias = {
        'Mon': 'LUN',
        'Tue': 'MAR',
        'Wed': 'MIÉ',
        'Thu': 'JUE',
        'Fri': 'VIE',
        'Sat': 'SÁB',
        'Sun': 'DOM'
    }
    return dias.get(day, day)
