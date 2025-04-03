from django.contrib import admin
from .models import Recipe, RecipeIngredient
from django.db import models
from ingredients.models import Ingredient

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ('ingredient',)

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    search_fields = ('name', 'author__username', 'ingredients__name')
    inlines = [RecipeIngredientInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('ingredients')

    #def get_queryset(self, request):
        #qs = super().get_queryset(request)
        #return qs.annotate(favorite_count=models.Count('favorites'))

    #def favorite_count(self, obj):
        #return obj.favorite_count
