from django.db import models
from django.core.cache import cache


class Airport(models.Model):
    iata_code = models.CharField("IATA код", max_length=3, unique=True, blank=True)
    country = models.CharField("Страна", max_length=100)
    name = models.CharField("название", max_length=100, default="NameOfAirport")
    latitude = models.FloatField("Широта", default=0.0)
    longitude = models.FloatField("Долгота", default=0.0)
    description = models.CharField("Описание", max_length=500, default="No description")

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



def get_all_airports():
    airports = cache.get("airports_all")
    if not (airports):
        airports = list(Airport.objects.all())
        cache.set("airports_all", airports, timeout=300)  #щас 5 минут, потом бы поменять на побольше
    return airports
