from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Tournament, TournamentMatch, SimpleMatch, TournamentParticipation

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Champs form d'édition du user
    fieldsets = UserAdmin.fieldsets + (
        ('Informations personnalisées', {
            'fields': (
                'display_name',
                'online_status',
                'blocked_users',
                'is_a2f_enabled',
                'is_42_user',
                'intra_id',
                'access_token',
                'refresh_token',
                'token_expires_at',
                'match_played',
                'wins',
            ),
        }),
    )

    # Champs liste des users
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

    list_filter = (
        'is_staff',
        'is_active',
        'is_42_user',
        'online_status',
        'is_a2f_enabled',
    )

    search_fields = (
        'username',
        'email',
        'display_name',
        'intra_id',
    )

    filter_horizontal = ('blocked_users',)

class TournamentParticipationInline(admin.TabularInline):
    model = TournamentParticipation
    extra = 1

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active', 'created_at',)
    inlines = [TournamentParticipationInline]

@admin.register(TournamentMatch)
class TournamentMatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'tournament', 'player1', 'player2', 'winner', 'round_number', 'created_at')
    search_fields = ('tournament__name', 'player1__username', 'player2__username', 'winner__username')
    list_filter = ('round_number', 'created_at',)

@admin.register(SimpleMatch)
class SimpleMatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'player1', 'player2', 'winner', 'created_at')
    search_fields = ('player1__username', 'player2__username', 'winner__username')
    list_filter = ('created_at',)
