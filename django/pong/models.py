from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    display_name = models.CharField(max_length=50, unique=True, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.jpg')
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
        related_name='friends_list',
        blank=True
    )

    is_a2f_enabled = models.BooleanField(default=True)
    # Champs nécessaires pour l'authentification via 42
    is_42_user = models.BooleanField(default=False)
    intra_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username


class Tournament(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    players = models.ManyToManyField(CustomUser, related_name="tournaments")
    is_active = models.BooleanField(default=True)

class Match(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="matches")
    player1 = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="match_player1")
    player2 = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="match_player2", null=True, blank=True)
    winner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="won_matches")
    round_number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

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

