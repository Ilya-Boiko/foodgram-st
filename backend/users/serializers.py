from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
import base64

User = get_user_model()

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password', 'username')  # Добавьте необходимые поля
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj.subscribers.filter(id=request.user.id).exists()

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