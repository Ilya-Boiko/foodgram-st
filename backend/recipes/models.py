from django.db import models
from django.contrib.auth import get_user_model
from ingredients.models import Ingredient  # Импортируем Ingredient из приложения ingredients

User = get_user_model()

class Recipe(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes', verbose_name='Автор')
    name = models.CharField(max_length=256, verbose_name='Название')
    image = models.ImageField(upload_to='recipes/images/', verbose_name='Изображение')
    text = models.TextField(verbose_name='Описание')
    ingredients = models.ManyToManyField(Ingredient, through='RecipeIngredient', verbose_name='Ингредиенты')
    cooking_time = models.PositiveIntegerField(verbose_name='Время приготовления (в минутах)')

    def __str__(self):
        return self.name

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        unique_together = ('recipe', 'ingredient')
