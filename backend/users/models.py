from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def _create_user(self, email, username, first_name, last_name, password, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        if not password:
            raise ValueError('Пароль обязателен')
            
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, username, first_name, last_name, password, **extra_fields)

    def create_superuser(self, email, username, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, username, first_name, last_name, password, **extra_fields)

class User(AbstractUser):
    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name="Адрес электронной почты"
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name="Фамилия"
    )
    avatar = models.ImageField(
        upload_to='users/avatars/',
        null=True,
        blank=True,
        verbose_name="Аватар"
    )
    # Удаляем поле shopping_cart, чтобы устранить циклическую зависимость
    # Позже добавим его через отдельную миграцию

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = UserManager()

    class Meta:
        ordering = ['id']
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email
