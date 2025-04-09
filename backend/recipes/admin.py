from django.contrib import admin
from .models import Recipe, RecipeIngredient
from django.db import models
from ingredients.models import Ingredient
from django.db.models import Count

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorite_count')
    list_filter = ('author',)
    search_fields = ('name', 'author__username')
    inlines = [RecipeIngredientInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            favorite_count=Count('favorited')
        ).select_related('author')

    def favorite_count(self, obj):
        return obj.favorite_count
    favorite_count.short_description = 'В избранном'
