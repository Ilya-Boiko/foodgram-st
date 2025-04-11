from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from .serializers import (
    UserSerializer, UserCreateSerializer,
    SetPasswordSerializer, SetAvatarSerializer,
    UserSubscriptionSerializer
)

User = get_user_model()

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

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, id=None):
        user_to_subscribe = get_object_or_404(User, id=id)
        if request.method == 'POST':
            if request.user == user_to_subscribe:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if request.user.subscriptions.filter(id=user_to_subscribe.id).exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.subscriptions.add(user_to_subscribe)
            serializer = self.get_serializer(user_to_subscribe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            if not request.user.subscriptions.filter(id=user_to_subscribe.id).exists():
                return Response(
                    {'error': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.subscriptions.remove(user_to_subscribe)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        subscribed_users = request.user.subscriptions.all()
        page = self.paginate_queryset(subscribed_users)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            response = self.get_paginated_response(serializer.data)
            response.data['results'] = response.data.pop('results')
            return response
        serializer = self.get_serializer(subscribed_users, many=True, context={'request': request})
        return Response({'results': serializer.data})

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_password(self, request):
        serializer = SetPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['put', 'delete'], permission_classes=[IsAuthenticated])
    def set_avatar(self, request):
        if request.method == 'DELETE':
            if request.user.avatar:
                request.user.avatar.delete()
            return Response({"avatar": None}, status=status.HTTP_200_OK)
        
        serializer = SetAvatarSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                serializer.to_representation(user),
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserMeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
