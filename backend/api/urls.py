from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecipeViewSet, UserViewSet, IngredientViewSet

router = DefaultRouter()
router.register('ingredients', IngredientViewSet)
router.register('recipes', RecipeViewSet)
router.register('users', UserViewSet)

urlpatterns = [
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
] 