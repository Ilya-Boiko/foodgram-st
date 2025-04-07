from django.contrib import admin
from .models import Recipe, RecipeIngredient
from django.db import models
from ingredients.models import Ingredient

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ('ingredient',)
    min_num = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'cooking_time')
    list_filter = ('author', 'cooking_time')
    search_fields = ('name', 'author__username', 'author__email', 'text')
    inlines = [RecipeIngredientInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').prefetch_related('ingredients')

@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    list_filter = ('recipe', 'ingredient')
    search_fields = ('recipe__name', 'ingredient__name')
    autocomplete_fields = ('recipe', 'ingredient')

    #def get_queryset(self, request):
        #qs = super().get_queryset(request)
        #return qs.annotate(favorite_count=models.Count('favorites'))

    #def favorite_count(self, obj):
        #return obj.favorite_count
