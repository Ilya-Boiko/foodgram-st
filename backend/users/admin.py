from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
     list_display = ('username', 'email', 'first_name', 'last_name', 'is_active')
     search_fields = ('email', 'username')
