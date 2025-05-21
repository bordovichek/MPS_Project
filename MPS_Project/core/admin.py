from django.contrib import admin
from core.models_dir import Airplane, Airport


@admin.register(Airplane)
class AirplaneAdmin(admin.ModelAdmin):
    list_display = ('name', 'year_of_manufacture', 'capacity', 'engine_power', 'consumption')

@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ('iata_code', 'country', 'name', 'latitude', 'longitude')
