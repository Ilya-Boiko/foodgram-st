from django.urls import path
from api.views import RecipeViewSet

app_name = 'recipes'

urlpatterns = [
    path('<int:pk>/', RecipeViewSet.as_view({'get': 'retrieve'}), name='recipe_detail'),
]
