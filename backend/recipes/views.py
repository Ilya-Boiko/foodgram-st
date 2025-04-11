from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from .models import Recipe
from .serializers import (
    RecipeSerializer, RecipeDetailSerializer,
    CreateUpdateRecipeSerializer
)
from .permissions import IsAuthorOrReadOnly
from django.db.models import Sum
from django.http import HttpResponse
from datetime import datetime

# Create your views here.


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('-id')
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'author__username']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'get_link']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Recipe.objects.all().order_by('-id')

        # Фильтрация по избранному
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited and self.request.user.is_authenticated:
            queryset = queryset.filter(favorited=self.request.user)

        # Фильтрация по списку покупок
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        if is_in_shopping_cart and self.request.user.is_authenticated:
            queryset = queryset.filter(in_shopping_cart=self.request.user)

        # Фильтрация по автору
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author_id=author)

        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateUpdateRecipeSerializer
        elif self.action == 'retrieve':
            return RecipeDetailSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if recipe in request.user.shopping_cart.all():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.shopping_cart.add(recipe)
            serializer = RecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if recipe not in request.user.shopping_cart.all():
            return Response(
                {'errors': 'Рецепт не в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.shopping_cart.remove(recipe)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if recipe in request.user.favorites.all():
                return Response(
                    {'errors': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.favorites.add(recipe)
            serializer = RecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if recipe not in request.user.favorites.all():
            return Response(
                {'errors': 'Рецепт не в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.favorites.remove(recipe)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        base_url = request.build_absolute_uri('/').rstrip('/')
        frontend_url = f"{base_url}/recipes/{recipe.id}/"
        return Response({'short-link': frontend_url})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        # Получаем все рецепты из списка покупок пользователя
        recipes = request.user.shopping_cart.all()

        # Получаем список ингредиентов с суммированным количеством
        ingredients = recipes.values(
            'ingredients__name',
            'ingredients__measurement_unit'
        ).annotate(
            total_amount=Sum('recipe_ingredients__amount')
        ).order_by('ingredients__name')

        # Формируем текст списка покупок
        shopping_list = [
            "Список покупок\n",
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        ]

        # Добавляем каждый ингредиент в список
        for ingredient in ingredients:
            name = ingredient['ingredients__name']
            unit = ingredient['ingredients__measurement_unit']
            amount = ingredient['total_amount']
            shopping_list.append(f"{name} ({unit}) — {amount}\n")

        # Создаем response с файлом
        response = HttpResponse(
            ''.join(shopping_list),
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename=shopping_list_{datetime.now().strftime("%d%m%Y_%H%M")}.txt'

        return response
