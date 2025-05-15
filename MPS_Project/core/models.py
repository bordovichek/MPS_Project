from django.db import models


class Airplane(models.Model):
    """Пока заглушка, просто чтобы что-то было"""
    year_of_manufacture = models.PositiveIntegerField("Год выпуска")
    capacity = models.PositiveIntegerField("Вместимость (кол-во мест)")
    engine_power = models.PositiveIntegerField("Мощность двигателя (л.с.)")

    def __str__(self):
        return f"Самолёт {self.id} — {self.year_of_manufacture} г., {self.capacity} мест, {self.engine_power} л.с."
