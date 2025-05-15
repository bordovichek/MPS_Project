from django.db import models

class Airport(models.Model):
    country = models.CharField("Страна", max_length=100)
    city = models.CharField("Город", max_length=100)

    def __str__(self):
        return f"Аэропорт в {self.city}, {self.country}"

