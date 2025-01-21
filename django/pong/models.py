from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    display_name = models.CharField(max_length=50, unique=True, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.jpg')
    online_status = models.BooleanField(default=False)

    def __str__(self):
        return self.username
