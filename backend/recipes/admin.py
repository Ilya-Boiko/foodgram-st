from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Recipe, Ingredient, RecipeIngredient
from django.utils.safestring import mark_safe
from statistics import quantiles

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1
    verbose_name = 'Продукт'
    verbose_name_plural = 'Продукты'

class CookingTimeFilter(admin.SimpleListFilter):
    title = 'время приготовления'
    parameter_name = 'cooking_time'

    def lookups(self, request, model_admin):
        cooking_times = Recipe.objects.values_list(
            'cooking_time', flat=True
        ).distinct().order_by('cooking_time')
        
        if not cooking_times:
            return []

        times_list = list(cooking_times)
        if len(times_list) >= 3:
            # Используем только существующие значения для расчета квантилей
            q1, q2 = quantiles(times_list, n=3)
            # Округляем значения до ближайших 5 минут вверх
            q1 = max(5, ((q1 + 4) // 5) * 5)
            q2 = max(10, ((q2 + 4) // 5) * 5)
        else:
            # Если мало рецептов, используем фиксированные интервалы
            q1, q2 = 15, 30

        fast_count = Recipe.objects.filter(cooking_time__lte=q1).count()
        medium_count = Recipe.objects.filter(
            cooking_time__gt=q1, cooking_time__lte=q2
        ).count()
        slow_count = Recipe.objects.filter(cooking_time__gt=q2).count()

        return [
            ('fast', f'До {q1} минут ({fast_count})'),
            ('medium', f'{q1}-{q2} минут ({medium_count})'),
            ('slow', f'Более {q2} минут ({slow_count})'),
        ]

    def queryset(self, request, queryset):
        times = Recipe.objects.values_list(
            'cooking_time', flat=True
        ).distinct().order_by('cooking_time')
        
        if not times:
            return queryset

        times_list = list(times)
        if len(times_list) >= 3:
            q1, q2 = quantiles(times_list, n=3)
            # Используем те же округленные значения
            q1 = max(5, ((q1 + 4) // 5) * 5)
            q2 = max(10, ((q2 + 4) // 5) * 5)
        else:
            q1, q2 = 15, 30

        if self.value() == 'fast':
            return queryset.filter(cooking_time__lte=q1)
        if self.value() == 'medium':
            return queryset.filter(cooking_time__gt=q1, cooking_time__lte=q2)
        if self.value() == 'slow':
            return queryset.filter(cooking_time__gt=q2)
        return queryset

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'id', 'username', 'get_full_name', 'email',
        'get_avatar', 'get_recipes_count',
        'get_subscriptions_count', 'get_subscribers_count'
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

    @admin.display(description='ФИО')
    def get_full_name(self, obj):
        return f'{obj.first_name} {obj.last_name}'.strip() or '—'

    @admin.display(description='Аватар')
    @mark_safe
    def get_avatar(self, obj):
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="50" height="50" />'
        return '—'

    @admin.display(description='Рецептов')
    def get_recipes_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Подписок')
    def get_subscriptions_count(self, obj):
        return obj.subscriptions.count()

    @admin.display(description='Подписчиков')
    def get_subscribers_count(self, obj):
        return obj.subscribers.count()

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'recipes', 'subscriptions', 'subscribers'
        )

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'cooking_time', 'author', 'get_favorites_count', 'get_ingredients', 'get_image')
    list_filter = ('author', CookingTimeFilter)
    search_fields = ('name', 'author__username')
    inlines = [RecipeIngredientInline]
    readonly_fields = ('get_favorites_count',)

    @admin.display(description='В избранном')
    def get_favorites_count(self, recipe):
        return recipe.in_favorites.count()

    @admin.display(description='Продукты')
    @mark_safe
    def get_ingredients(self, recipe):
        ingredients = recipe.recipe_ingredients.select_related('ingredient')
        return '<br>'.join(
            f'{ingredient.ingredient.name} - {ingredient.amount} {ingredient.ingredient.measurement_unit}'
            for ingredient in ingredients
        )

    @admin.display(description='Изображение')
    @mark_safe
    def get_image(self, recipe):
        if recipe.image:
            return f'<img src="{recipe.image.url}" width="80" height="60" />'
        return 'Нет изображения'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author')

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('measurement_unit',)
    search_fields = ('name',)

