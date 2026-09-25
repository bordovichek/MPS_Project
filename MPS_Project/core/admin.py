from django.contrib import admin, messages
from django.utils.html import format_html

from core.models import Airplane, Airport


@admin.register(Airplane)
class AirplaneAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "year_of_manufacture",
        "capacity",
        "max_distance",
        "cruise_speed",
        "consumption",
        "in_service",
    )
    list_filter = ("in_service",)
    search_fields = ("name", "engines")
    readonly_fields = ("photo_preview",)
    fields = (
        "name",
        "year_of_manufacture",
        "capacity",
        "engines",
        "consumption",
        "cruise_speed",
        "max_distance",
        "in_service",
        "description",
        "image",
        "photo_preview",
    )
    actions = ("retire", "return_to_service")

    @admin.display(description="Превью")
    def photo_preview(self, airplane: Airplane) -> str:
        if not airplane.image:
            return "—"
        return format_html('<img src="{}" alt="" style="max-width: 320px; border-radius: 8px">', airplane.image.url)

    @admin.action(description="Вывести из эксплуатации")
    def retire(self, request, queryset):
        count = queryset.update(in_service=False)
        self.message_user(request, f"Выведено из эксплуатации: {count}", messages.WARNING)

    @admin.action(description="Вернуть в эксплуатацию")
    def return_to_service(self, request, queryset):
        count = queryset.update(in_service=True)
        self.message_user(request, f"Возвращено в эксплуатацию: {count}")


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("iata_code", "name", "country", "latitude", "longitude")
    list_filter = ("country",)
    search_fields = ("iata_code", "name")
    fields = ("iata_code", "name", "country", "latitude", "longitude", "description")
    ordering = ("iata_code",)
    list_per_page = 50
    actions = ("clear_description",)

    @admin.action(description="Очистить описание")
    def clear_description(self, request, queryset):
        count = queryset.update(description="")
        self.message_user(request, f"Описание очищено у {count} аэропортов.")
