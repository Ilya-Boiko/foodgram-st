from django.urls import path
from django.shortcuts import redirect

app_name = 'recipes'

def redirect_to_recipe(request, short_link):
    return redirect(f'/api/recipes/{short_link}/')

urlpatterns = [
    path('s/<str:short_link>/', redirect_to_recipe, name='recipe_short_link'),
]
