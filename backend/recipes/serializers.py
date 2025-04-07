from rest_framework import serializers
from .models import Recipe, RecipeIngredient
from ingredients.models import Ingredient
from users.serializers import UserSerializer

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

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'name', 'image', 'text', 'cooking_time', 'is_in_shopping_cart')

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj in request.user.shopping_cart.all()

class RecipeDetailSerializer(RecipeSerializer):
    ingredients = RecipeIngredientSerializer(many=True, source='recipeingredient_set')

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ('ingredients',)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipeingredient_set')
        recipe = Recipe.objects.create(**validated_data)
        
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipeingredient_set', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if ingredients_data is not None:
            instance.recipeingredient_set.all().delete()
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient_data['ingredient'],
                    amount=ingredient_data['amount']
                )
        return instance 