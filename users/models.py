from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    
    class Role(models.TextChoices):
        CLIENT = 'client', 'Client'
        ARTIST = 'artist', 'Artist'
        ADMIN = 'admin', 'Admin'
    
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CLIENT
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
    
class ArtistProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artist_profile')
    # ARTIST ATTRIBUTES

    def __str__(self):
        return f"ArtistProfile({self.user.username})"


class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    # CLIENT ATTRIBUTES

    def __str__(self):
        return f"ClientProfile({self.user.username})"