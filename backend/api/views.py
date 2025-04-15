from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse
from datetime import datetime

from recipes.models import Recipe, User, Ingredient, RecipeIngredient, Favorite, ShoppingCart, Subscription
from .serializers import (
    RecipeSerializer,
    CreateUpdateRecipeSerializer,
    UserSerializer,
    UserCreateSerializer,
    SetPasswordSerializer,
    SetAvatarSerializer,
    UserSubscriptionSerializer,
    IngredientSerializer,
    RecipeMinifiedSerializer
)
from .permissions import IsAuthorOrReadOnly

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'

    def get_permissions(self):
        if self.action in ['create', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['subscribe', 'subscriptions']:
            return UserSubscriptionSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        subscribed_users = User.objects.filter(subscribers__user=request.user)
        page = self.paginate_queryset(subscribed_users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(subscribed_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def set_password(self, request):
        serializer = SetPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            if Subscription.objects.filter(user=request.user, author=author).exists():
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=request.user, author=author)
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
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

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
            cart_recipes = self.request.user.shopping_cart.values_list('recipe_id', flat=True)
            queryset = queryset.filter(id__in=cart_recipes)

        # Фильтрация по автору
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author_id=author)

        return queryset.order_by('-pub_date')

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeMinifiedSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            cart_item = get_object_or_404(
                ShoppingCart, user=request.user, recipe=recipe
            )
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeMinifiedSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite = get_object_or_404(
                Favorite, user=request.user, recipe=recipe
            )
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        base_url = request.build_absolute_uri('/').rstrip('/')
        frontend_url = f"{base_url}/recipes/{recipe.id}/"
        return Response({'short-link': frontend_url})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        # Получаем ID рецептов из корзины пользователя
        recipes_in_cart = ShoppingCart.objects.filter(user=request.user).values_list('recipe', flat=True)

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
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__measurement_unit']
            amount = ingredient['total_amount']
            shopping_list.append(f"{name} ({unit}) — {amount}\n")

        # Создаем response с файлом
        response = HttpResponse(
            ''.join(shopping_list),
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename=shopping_list_{datetime.now().strftime("%d%m%Y_%H%M")}.txt'

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
