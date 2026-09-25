from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django_countries.fields import CountryField

iata_validator = RegexValidator(r"^[A-Z]{3}$", "IATA-код — три латинские буквы, например SVO.")


class Airplane(models.Model):
    name = models.CharField("Модель", max_length=100, unique=True)
    year_of_manufacture = models.PositiveSmallIntegerField("Год выпуска", null=True, blank=True)
    capacity = models.PositiveIntegerField("Пассажировместимость", null=True, blank=True)
    engines = models.CharField("Двигатели", max_length=120, blank=True, help_text="Например: 2 × CFM56-7B")
    consumption = models.PositiveIntegerField("Расход топлива, кг/ч", validators=[MinValueValidator(1)])
    cruise_speed = models.PositiveIntegerField("Крейсерская скорость, км/ч", validators=[MinValueValidator(1)])
    max_distance = models.PositiveIntegerField("Максимальная дальность, км", validators=[MinValueValidator(1)])
    in_service = models.BooleanField("В эксплуатации", default=True)
    description = models.TextField("Описание", blank=True)
    image = models.ImageField("Фото", upload_to="airplanes/", null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "самолёт"
        verbose_name_plural = "самолёты"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("web:airplane_detail", args=[self.pk])

    @property
    def fuel_per_seat_100km(self) -> float | None:
        """Расход топлива в кг на одного пассажира на 100 км при полной загрузке."""
        if not self.capacity:
            return None
        return self.consumption / (self.capacity * self.cruise_speed) * 100


class Airport(models.Model):
    iata_code = models.CharField("IATA-код", max_length=3, unique=True, validators=[iata_validator])
    name = models.CharField("Название", max_length=150)
    country = CountryField("Страна")
    latitude = models.FloatField("Широта", validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField("Долгота", validators=[MinValueValidator(-180), MaxValueValidator(180)])
    description = models.TextField("Описание", blank=True)
    updated_at = models.DateTimeField("Изменён", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "аэропорт"
        verbose_name_plural = "аэропорты"
        indexes = [models.Index(fields=["country"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.iata_code})"

    def save(self, *args, **kwargs):
        self.iata_code = self.iata_code.strip().upper()
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("web:airport_detail", args=[self.iata_code])
