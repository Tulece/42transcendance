from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class CustomUser(AbstractUser):
    display_name = models.CharField(max_length=50, unique=True, null=True, blank=True)
    #avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    avatar_url = models.CharField(default='/media/avatars/default.jpg')
    online_status = models.BooleanField(default=False)

    # Un user peut bloquer d'autres users
    blocked_users = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='blocked_by',
        blank=True
    )

    friends = models.ManyToManyField(
        'self',
        symmetrical=True, # A ami avec B donc B ami avec A
        #related_name='friends_list',
        #related_name='friends_list',
        blank=True
    )

    match_played  = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    loses = models.IntegerField(default=0)

    is_a2f_enabled = models.BooleanField(default=True)
    # Champs nécessaires pour l'authentification via 42
    is_42_user = models.BooleanField(default=False)
    intra_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

# @receiver(post_save, sender=CustomUser)
# def update_avatar_url(sender, instance, created, **kwargs):
#     """Update the avatar_url field when the avatar field is changed."""
#     if instance.avatar:
#         if instance.avatar_url != instance.avatar.url:
#             instance.avatar_url = instance.avatar.url
#             # Use update to avoid triggering this signal again
#             CustomUser.objects.filter(pk=instance.pk).update(avatar_url=instance.avatar.url)

#     def __str__(self):
#         return self.username


class Tournament(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    players = models.ManyToManyField(CustomUser, through='TournamentParticipation', related_name="tournaments")
    is_active = models.BooleanField(default=True)

class BaseMatch(models.Model):
    player1 = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="%(class)s_player1"
    )
    player2 = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="%(class)s_player2", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    game_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        abstract = True

class TournamentMatch(BaseMatch):
    winner = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_won_matches"
    )
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="matches")
    round_number = models.IntegerField()

class SimpleMatch(BaseMatch):
    winner = models.CharField(max_length=10, null=True, blank=True)
    pass

class FriendRequest(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="sent_requests")
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="received_requests")
    status = models.CharField(
        max_length=20,
        choices=[("pending", "En attente"), ("accepted", "Acceptée"), ("declined", "Refusée")],
        default="pending"
    ) # Stocker un status sur la demande
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('sender', 'receiver')  # Empêche de send pls demandes au même user

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username} ({self.status})"

from django.db import models
from .models import Tournament, CustomUser  # ou le chemin correct

class TournamentParticipation(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="participations")
    player = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="tournament_participations")
    tournament_alias = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = [
            ('tournament', 'player'),
            ('tournament', 'tournament_alias'),  # pour forcer l'unicité de l'alias dans le tournoi
        ]

    def get_display_name(self):
        return self.tournament_alias or self.player.username
