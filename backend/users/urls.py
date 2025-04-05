from django.urls import path
from .views import UserViewSet, UserMeView

urlpatterns = [
    path('users/me/', UserMeView.as_view(), name='user-me'),
    path('users/', UserViewSet.as_view({'get': 'list', 'post': 'create'}), name='user-list'),
    path('users/<int:id>/', UserViewSet.as_view({'get': 'retrieve'}), name='user-detail'),
    path('users/set_password/', UserViewSet.as_view({'post': 'set_password'}), name='set-password'),
    path('users/me/avatar/', UserViewSet.as_view({
        'put': 'set_avatar',
        'delete': 'delete_avatar'
    }), name='user-avatar'),
] 