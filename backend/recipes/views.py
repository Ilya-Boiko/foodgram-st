from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import Recipe
from .serializers import RecipeSerializer, RecipeDetailSerializer

# Create your views here.

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return RecipeDetailSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        
        if request.method == 'POST':
            # Добавление в список покупок
            request.user.shopping_cart.add(recipe)
            return Response({'detail': 'Рецепт добавлен в список покупок'}, 
                          status=status.HTTP_201_CREATED)
        
        # Удаление из списка покупок
        request.user.shopping_cart.remove(recipe)
        return Response(status=status.HTTP_204_NO_CONTENT)
