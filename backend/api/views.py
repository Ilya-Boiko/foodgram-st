from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from datetime import datetime
from django.urls import reverse
from djoser.views import UserViewSet as DjoserUserViewSet
from django.http import FileResponse
from io import BytesIO
from recipes.models import Recipe, User, Ingredient, RecipeIngredient, Favorite, ShoppingCart, Subscription
from .serializers import (
    CreateUpdateRecipeSerializer,
    UserSerializer,
    SetAvatarSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    UserSubscriptionSerializer
)
from .permissions import IsAuthorOrReadOnly


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ['me', 'set_avatar', 'subscribe', 'subscriptions']:
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        subscribed_users = User.objects.filter(authors__user=request.user)
        page = self.paginate_queryset(subscribed_users)
        serializer = UserSubscriptionSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar')
    def set_avatar(self, request):
        if request.method == 'DELETE':
            if request.user.avatar:
                request.user.avatar.delete()
            return Response({"avatar": None}, status=status.HTTP_200_OK)
        
        serializer = SetAvatarSerializer(
            request.user,
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                UserSerializer(user, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, id=None):
        author = self.get_object()
        
        if request.method == 'POST':
            if request.user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            subscription, created = Subscription.objects.get_or_create(
                user=request.user,
                author=author
            )
            
            if not created:
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = self.get_serializer(author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        subscription = get_object_or_404(
            Subscription, user=request.user, author=author
        )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateUpdateRecipeSerializer
        return RecipeReadSerializer
    
    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        return recipe

    def get_queryset(self):
        queryset = Recipe.objects.all()

        # Фильтрация по избранному
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited and self.request.user.is_authenticated:
            favorite_recipes = self.request.user.favorites.values_list('recipe_id', flat=True)
            queryset = queryset.filter(id__in=favorite_recipes)

        # Фильтрация по списку покупок
        is_in_shopping_cart = self.request.query_params.get('is_in_shopping_cart')
        if is_in_shopping_cart and self.request.user.is_authenticated:
            cart_recipes = self.request.user.shopping_cart_items.values_list('recipe_id', flat=True)
            queryset = queryset.filter(id__in=cart_recipes)

        # Фильтрация по автору
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author_id=author)

        return queryset.order_by('-pub_date')

    def _handle_recipe_action(self, request, pk, model_class, error_message, success_message):
        recipe = get_object_or_404(Recipe, id=pk)
        
        if request.method == 'POST':
            item, created = model_class.objects.get_or_create(
                user=request.user,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'errors': error_message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'message': success_message},
                status=status.HTTP_201_CREATED
            )
            
        item = get_object_or_404(model_class, user=request.user, recipe=recipe)
        item.delete()
        return Response(
            {'message': f'Рецепт удален из {success_message.lower()}'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self._handle_recipe_action(
            request,
            pk,
            ShoppingCart,
            'Рецепт уже в списке покупок',
            'Рецепт добавлен в список покупок'
        )

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self._handle_recipe_action(
            request,
            pk,
            Favorite,
            'Рецепт уже в избранном',
            'Рецепт добавлен в избранное'
        )

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        frontend_url = request.build_absolute_uri(f'/recipes/{recipe.id}/')
        return Response({'short-link': frontend_url})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        # Получаем ID рецептов из корзины пользователя
        recipes_in_cart = ShoppingCart.objects.filter(user=request.user).values_list('recipe', flat=True)

        if not recipes_in_cart:
            return Response(
                {'errors': 'Список покупок пуст'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем список ингредиентов с суммированным количеством
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=recipes_in_cart
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        # Формируем текст списка покупок
        shopping_list = [
            "Список покупок\n",
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        ]

        # Добавляем каждый ингредиент в список
        for ingredient in ingredients:
            shopping_list.extend([f"{ingredient['ingredient__name'].capitalize()} ({ingredient['ingredient__measurement_unit']}) — {ingredient['total_amount']}\n"])

        # Создаем response с файлом
        response = FileResponse(
            ''.join(shopping_list),
            as_attachment=True,
            filename=f'shopping_list_{datetime.now().strftime("%d%m%Y_%H%M")}.txt',
            content_type='text/plain; charset=utf-8'
        )

        return response

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        
        if name:
            queryset = queryset.filter(name__istartswith=name)
            
        return queryset.order_by('name')
