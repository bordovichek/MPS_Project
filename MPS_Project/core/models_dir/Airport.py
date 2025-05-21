from django.db import models


class Airport(models.Model):
    iata_code = models.CharField("IATA код", max_length=3, unique=True, blank=True)
    country = models.CharField("Страна", max_length=100)
    name = models.CharField("название", max_length=100, default='NameOfAirport')
    #city = models.CharField("Город", max_length=100)
    latitude = models.FloatField("Широта", default=0.0)
    longitude = models.FloatField("Долгота", default=0.0)

    def save(self, *args, **kwargs):
        if not self.iata_code:
            base = "N"
            i = 1
            while True:
                code = f"{base}{i:02d}"
                if len(code) > 3:
                    raise ValueError("Не удалось сгенерировать уникальный IATA код — исчерпаны комбинации.")
                if not Airport.objects.filter(iata_code=code).exists():
                    self.iata_code = code
                    break
                i += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.iata_code} — "
            f"{self.city} ({self.rus_city or 'рус. не указано'}), "
            f"{self.country}, "
            f"Координаты: {self.latitude}, {self.longitude}"
        )
