from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
import base64
from recipes.models import Recipe

User = get_user_model()

class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

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
        return request.user.subscriptions.filter(id=obj.id).exists()

class UserSubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count',)

    def get_recipes(self, obj):
        request = self.context.get('request')
        if not request:
            return []
        
        limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        
        if limit:
            try:
                limit = int(limit)
                recipes = recipes[:limit]
            except (ValueError, TypeError):
                pass
        
        serializer = RecipeMinifiedSerializer(
            recipes, 
            many=True, 
            context={'request': request}
        )
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

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
    avatar = serializers.CharField(required=False, allow_null=True)

    def validate_avatar(self, value):
        if value and not value.startswith('data:image'):
            raise serializers.ValidationError("Неверный формат изображения")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        avatar_data = validated_data.get('avatar')

        if avatar_data is None:
            # Если данные аватара не предоставлены, оставляем текущий аватар
            return user

        # Если данные аватара пустые, удаляем текущий аватар
        if avatar_data == '':
            if user.avatar:
                user.avatar.delete()
            return user

        # Декодирование base64 и сохранение нового изображения
        try:
            format, imgstr = avatar_data.split(';base64,')
            ext = format.split('/')[-1]
            data = base64.b64decode(imgstr)
            
            from django.core.files.base import ContentFile
            filename = f'avatar_{user.id}.{ext}'
            
            # Удаляем старый аватар перед сохранением нового
            if user.avatar:
                user.avatar.delete()
            
            user.avatar.save(filename, ContentFile(data), save=True)
        except Exception as e:
            raise serializers.ValidationError("Ошибка при сохранении изображения")
        
        return user

    def to_representation(self, instance):
        request = self.context.get('request')
        return {
            'avatar': request.build_absolute_uri(instance.avatar.url) if instance.avatar else None
        } 