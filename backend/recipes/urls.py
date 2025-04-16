from django.urls import path
from django.shortcuts import redirect

app_name = 'recipes'

def redirect_to_recipe(request, pk):
    return redirect(f'/recipes/{pk}/')

urlpatterns = [
    path('<int:pk>/', redirect_to_recipe, name='recipe_detail'),
]
