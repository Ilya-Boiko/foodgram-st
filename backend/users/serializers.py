from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
import base64

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return False  # Здесь нужно реализовать логику подписок

class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError("Пароль не может быть пустым")
        validate_password(value)
        return value

    def create(self, validated_data):
        try:
            # Создаем пользователя через create_user
            user = User.objects.create_user(
                email=validated_data['email'],
                username=validated_data['username'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                password=validated_data['password']
            )
            return user
        except Exception as e:
            raise serializers.ValidationError(
                {"error": f"Ошибка при создании пользователя: {str(e)}"}
            )

class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class SetAvatarSerializer(serializers.Serializer):
    avatar = serializers.CharField(required=True)

    def validate_avatar(self, value):
        if not value.startswith('data:image'):
            raise serializers.ValidationError("Неверный формат изображения")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        # Декодирование base64 и сохранение изображения
        try:
            format, imgstr = validated_data['avatar'].split(';base64,')
            ext = format.split('/')[-1]
            data = base64.b64decode(imgstr)
            
            from django.core.files.base import ContentFile
            filename = f'avatar_{user.id}.{ext}'
            user.avatar.save(filename, ContentFile(data), save=True)
        except Exception as e:
            raise serializers.ValidationError("Ошибка при сохранении изображения")
        
        return user 