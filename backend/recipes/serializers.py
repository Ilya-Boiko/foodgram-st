from rest_framework import serializers
from .models import Recipe, RecipeIngredient
from ingredients.models import Ingredient
from users.serializers import UserSerializer
import base64
from django.core.files.base import ContentFile

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'recipe.{ext}')
        return super().to_internal_value(data)

class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), source='ingredient')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'text', 'cooking_time', 'is_in_shopping_cart', 'is_favorited')

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj in request.user.shopping_cart.all()

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj in request.user.favorites.all()

class CreateUpdateRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True)
    ingredients = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        required=True
    )
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = ('name', 'text', 'cooking_time', 'image', 'ingredients')

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Нужен хотя бы один ингредиент")
        
        ingredient_ids = []
        for item in value:
            ingredient_id = item.get('id')
            amount = item.get('amount')
            
            if not ingredient_id:
                raise serializers.ValidationError("Отсутствует id ингредиента")
            
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError("Ингредиенты не должны повторяться")
            
            try:
                amount = int(amount)
                if amount < 1:
                    raise ValueError
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    "Количество ингредиента должно быть целым числом больше 0"
                )
            
            try:
                Ingredient.objects.get(id=ingredient_id)
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    f"Ингредиент с id={ingredient_id} не существует"
                )
            
            ingredient_ids.append(ingredient_id)
        
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients_data = validated_data.pop('ingredients')
            instance.recipe_ingredients.all().delete()
            self._create_ingredients(instance, ingredients_data)
        
        return super().update(instance, validated_data)

    def _create_ingredients(self, recipe, ingredients_data):
        for ingredient_item in ingredients_data:
            ingredient_id = ingredient_item['id']
            amount = int(ingredient_item['amount'])
            
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_id,
                amount=amount
            )

    def to_representation(self, instance):
        serializer = RecipeDetailSerializer(instance, context=self.context)
        return serializer.data

class RecipeDetailSerializer(RecipeSerializer):
    ingredients = serializers.SerializerMethodField()

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ('ingredients',)

    def get_ingredients(self, obj):
        recipe_ingredients = obj.recipe_ingredients.all()
        return RecipeIngredientSerializer(recipe_ingredients, many=True).data

    def create(self, validated_data):
        ingredients_data = self.context.get('request').data.get('ingredients')
        if not ingredients_data:
            raise serializers.ValidationError({"ingredients": "Это поле обязательно."})
            
        recipe = Recipe.objects.create(**validated_data)
        
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = self.context.get('request').data.get('ingredients')
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient_id=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )
        return instance 