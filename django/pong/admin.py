from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Champs à afficher dans le formulaire d'édition d'utilisateur
    fieldsets = UserAdmin.fieldsets + (
        ('Informations personnalisées', {
            'fields': (
                'display_name',
                'avatar',
                'online_status',
                'blocked_users',
                'is_a2f_enabled',
                'is_42_user',
                'intra_id',
                'access_token',
                'refresh_token',
                'token_expires_at',
            ),
        }),
    )

    # Champs affichés dans la liste des utilisateurs
    list_display = (
        'username',
        'email',
        'display_name',
        'online_status',
        'is_42_user',
        'is_a2f_enabled',
        'is_staff',
        'is_active',
        'last_login',
        'date_joined',
    )

    # Filtres disponibles
    list_filter = (
        'is_staff',
        'is_active',
        'is_42_user',
        'online_status',
        'is_a2f_enabled',
    )

    # Recherche par ces champs
    search_fields = (
        'username',
        'email',
        'display_name',
        'intra_id',
    )

    # Gestion des relations ManyToManyField
    filter_horizontal = ('blocked_users',)
