
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, ArtistProfile, ClientProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return
    # Skip auto-creation during fixture loading — profiles are loaded directly
    if kwargs.get('raw'):
        return
    if instance.role == User.Role.ARTIST:
        ArtistProfile.objects.create(user=instance)
    elif instance.role == User.Role.CLIENT:
        ClientProfile.objects.create(user=instance)