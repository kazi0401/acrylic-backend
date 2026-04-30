from django.db import models
from songs.models import Song
from users.models import ClientProfile
from subscriptions.models import BuyerSubscription

class License(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'active'
        EXPIRED = 'expired'
        REVOKED = 'revoked'

    class LicenseType(models.TextChoices):
        BID2CLEAR = 'bid2clear'
        PRECLEAR = 'preclear'
        ARTISTPROMO = 'artist_promo'

    # Who and what
    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.PROTECT
    )

    # Payment path
    license_type = models.CharField(
        max_length=20,
        choices=LicenseType.choices
    )
    subscription = models.ForeignKey(
        BuyerSubscription,
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    # Stripe reference
    stripe_payment_intent_id = models.CharField(
        max_length=200,
        null=True, blank=True
    )
    price_paid = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    # Terms
    usage_details = models.TextField()
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)