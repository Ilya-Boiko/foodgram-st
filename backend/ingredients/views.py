from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django.db.models import Q
from .models import Ingredient
from .serializers import IngredientSerializer

# Create your views here.

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        
        if name:
            # Поиск по началу названия (регистронезависимый)
            queryset = queryset.filter(name__istartswith=name)
            
        return queryset.order_by('name')
