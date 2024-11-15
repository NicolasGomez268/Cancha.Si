# Generated by Django 5.1.2 on 2024-11-14 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('canchas', '0003_remove_cancha_foto_remove_cancha_servicios_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='complejo',
            name='servicios',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='complejo',
            name='tiene_mesas',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='complejo',
            name='tiene_parrillas',
            field=models.BooleanField(default=False),
        ),
    ]