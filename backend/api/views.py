from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from datetime import datetime
from django.urls import reverse
from djoser.views import UserViewSet as DjoserUserViewSet
from recipes.models import Recipe, User, Ingredient, RecipeIngredient, Favorite, ShoppingCart, Subscription
from .serializers import (
    CreateUpdateRecipeSerializer,
    UserSerializer,
    SetAvatarSerializer,
    IngredientSerializer,
    RecipeMinifiedSerializer,
    RecipeReadSerializer
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
    def me(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        subscribed_users = User.objects.filter(authors__user=request.user)
        page = self.paginate_queryset(subscribed_users)
        return self.get_serializer(page, many=True)

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
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        # Используем RecipeReadSerializer для полного ответа
        response_serializer = RecipeReadSerializer(
            recipe, 
            context={'request': request}
        )
        return Response(
            response_serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )

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

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if request.user.shopping_cart_items.filter(recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в списке покупок'}, status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            return Response({'message': 'Рецепт добавлен в список покупок'}, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            shopping_cart_item = get_object_or_404(ShoppingCart, user=request.user, recipe=recipe)
            shopping_cart_item.delete()
            return Response({'message': 'Рецепт удален из списка покупок'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            if request.user.favorites.filter(recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в избранном'}, status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=request.user, recipe=recipe)
            return Response({'message': 'Рецепт добавлен в избранное'}, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite_item = get_object_or_404(Favorite, user=request.user, recipe=recipe)
            favorite_item.delete()
            return Response({'message': 'Рецепт удален из избранного'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        frontend_url = request.build_absolute_uri(
            reverse('recipes:recipe_detail', kwargs={'pk': recipe.id})
        )
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
            shopping_list.append(f"{name.capitalize()} ({unit}) — {amount}\n")

        # Создаем response с файлом
        response = FileResponse(
            BytesIO(''.join(shopping_list).encode('utf-8')),
            as_attachment=True,
            filename=f'shopping_list_{datetime.now().strftime("%d%m%Y_%H%M")}.txt'
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
