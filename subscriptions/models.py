from django.db import models
from users.models import ClientProfile


class SubscriptionTier(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price_annual = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Artist Promo access
    includes_artist_promo = models.BooleanField(default=False)
    
    # Acrylic can deactivate a tier without deleting it
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (${self.price_annual}/year)"


class BuyerSubscription(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    profile = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    tier = models.ForeignKey(
        SubscriptionTier,
        on_delete=models.PROTECT
        # PROTECT because deleting a tier that has
        # subscribers attached would be destructive
    )

    # Stripe references
    stripe_customer_id = models.CharField(max_length=200)
    stripe_subscription_id = models.CharField(
        max_length=200,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # Billing period
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.user.username} - {self.tier.name} ({self.status})"

    class Meta:
        ordering = ['-created_at']