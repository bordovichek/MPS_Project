from django.db import models


class Airport(models.Model):
    iata_code = models.CharField("IATA код", max_length=3, unique=True)
    country = models.CharField("Страна", max_length=100)
    city = models.CharField("Город", max_length=100)
    rus_city = models.CharField("Город НА РУССКОМ", max_length=100, null=True, blank=True)
    latitude = models.FloatField("Широта")
    longitude = models.FloatField("Долгота")

    def __str__(self):
        return (
            f"{self.iata_code} — "
            f"{self.city} ({self.rus_city or 'рус. не указано'}), "
            f"{self.country}, "
            f"Координаты: {self.latitude}, {self.longitude}"
        )
