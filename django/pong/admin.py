from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('display_name', 'avatar', 'online_status')}),
    )
    list_display = ('username', 'email', 'display_name', 'online_status', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'online_status')

print("admin.py loaded")
