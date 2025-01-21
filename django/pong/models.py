from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Pour créer auto un profil lors de la création d'un user.
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# Profile.blocked_users est un ManyToManyFiled vers User
# User a donc un champ blocked_by, ce qui indique "qui m'a bloqué"
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile') # Il existe une instance de Profile pour un User.
    blocked_users = models.ManyToManyField(User, related_name='blocked_by', blank=True) # Un profil peut contenir une liste de users bloqués.

    def __str__(self):
        return f"Profil de {self.user.username}"

