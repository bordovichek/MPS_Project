from django.db import models
from django.core.cache import cache
from sympy import Plane


class Airplane(models.Model):
    name = models.CharField("Название самолета", max_length=50, default="Boeing")
    year_of_manufacture = models.PositiveIntegerField("Год выпуска", null=True, blank=True)
    capacity = models.PositiveIntegerField("Вместимость пассажиров", null=True, blank=True)
    engine_power = models.PositiveIntegerField("Мощность двигателя (л.с.)", null=True, blank=True)
    consumption = models.PositiveIntegerField("Расход топлива (кг/час)", default=8000)
    cruise_speed = models.PositiveIntegerField("Крейсерская скорость (км/час)",default=1000)
    max_distance = models.PositiveIntegerField("Максимальное расстояние (км)", default=6000)

    def __str__(self):
        return (
            f"{self.name} — "
            f"Год выпуска: {self.year_of_manufacture or 'не указан'}, "
            f"Вместимость: {self.capacity or 'не указана'} чел., "
            f"Мощность: {self.engine_power or 'не указана'} л.с., "
            f"Расход топлива: {self.consumption} кг/час"
            f"Крейсерская скорость: {self.cruise_speed} км/час"
            f"Максимальное расстояние: {self.max_distance} км"
        )

def get_all_planes():
    planes = cache.get("planes_all")
    if not(planes):
        planes = list(Plane.objects.all())
        cache.set("planes_all", planes, timeout=300)#щас 5 минут, потом бы поменять на побольше
    return planes