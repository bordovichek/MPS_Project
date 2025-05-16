from django.db import models


class Airplane(models.Model):
    name = models.CharField("Название самолета", max_length=50, unique=True)
    year_of_manufacture = models.PositiveIntegerField("Год выпуска", null=True, blank=True)
    capacity = models.PositiveIntegerField("Вместимость пассажиров", null=True, blank=True)
    engine_power = models.PositiveIntegerField("Мощность двигателя (л.с.)", null=True, blank=True)
    consumption = models.IntegerField("Расход топлива (кг/час)")

    def __str__(self):
        return (
            f"{self.name} — "
            f"Год выпуска: {self.year_of_manufacture or 'не указан'}, "
            f"Вместимость: {self.capacity or 'не указана'} чел., "
            f"Мощность: {self.engine_power or 'не указана'} л.с., "
            f"Расход топлива: {self.consumption} кг/час"
        )
