from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'last_name', 'first_name', 'patronymic', 'role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('patronymic', 'position', 'department', 'role')}),
    )