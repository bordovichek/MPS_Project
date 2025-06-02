from django.contrib import admin, messages
from django.utils.safestring import mark_safe

from core.models_dir import Airplane, Airport


@admin.register(Airplane)
class AirplaneAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'year_of_manufacture', 'capacity', 'engine_power', 'consumption', 'max_distance', 'in_service',)
    fields = ('name', 'year_of_manufacture', 'capacity', 'engine_power', 'consumption', 'max_distance',
              'cruise_speed', 'in_service', 'description', 'image', 'plane_image',)
    readonly_fields = ('plane_image',)
    ordering = ['name', 'year_of_manufacture']
    actions = ['out_of_service', 'back_in_service']
    search_fields = ['name']

    @admin.action(description='Вывести из эксплуатации')
    def out_of_service(self, request, queryset):
        count = queryset.update(in_service=False)
        self.message_user(request, f"Изменено {count} самолетов", messages.WARNING)

    @admin.action(description='Вернуть в эксплуатацию')
    def back_in_service(self, request, queryset):
        count = queryset.update(in_service=True)
        self.message_user(request, f"Изменено {count} самолетов")

    @admin.display(description="Изображение")
    def plane_image(self, plane: Airplane):
        if plane.image:
            return mark_safe(f"<img src='{plane.image.url}' width=250>")
        return "No image"




@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ('iata_code', 'name', 'country', 'latitude', 'longitude',)
    fields = ('iata_code', 'name', 'country', 'latitude', 'longitude', 'description',)
    search_fields = ['name', 'iata_code', 'country']
    ordering = ['name', 'country']
    list_filter = ('country',)
    actions = ['clear_description']

    @admin.action(description='Очистить описание выбранных аэропортов')
    def clear_description(self, request, queryset):
        count = queryset.update(description="No description")
        self.message_user(request, f"Описание {count} аэропортов очищено.")