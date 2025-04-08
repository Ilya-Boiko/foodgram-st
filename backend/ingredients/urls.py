from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import IngredientViewSet

app_name = 'ingredients'

router = DefaultRouter()
router.register('ingredients', IngredientViewSet, basename='ingredients')

urlpatterns = router.urls 