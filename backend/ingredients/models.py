from django.db import models

class Ingredient(models.Model):
    name = models.CharField(max_length=128, verbose_name='Название')
    measurement_unit = models.CharField(max_length=64, verbose_name='Единица измерения')

    def __str__(self):
        return self.name
