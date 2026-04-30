from rest_framework import serializers
from .models import SubscriptionTier, BuyerSubscription


class SubscriptionTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionTier
        fields = [
            'id',
            'name',
            'price_annual',
            'includes_artist_promo',
        ]
        # is_active is intentionally excluded — buyers don't
        # need to know about inactive tiers, the view filters
        # them out. It's an internal Acrylic management field.


class BuyerSubscriptionSerializer(serializers.ModelSerializer):
    tier = SubscriptionTierSerializer(read_only=True)
    tier_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionTier.objects.filter(is_active=True),
        source='tier',
        write_only=True
    )

    class Meta:
        model = BuyerSubscription
        fields = [
            'id',
            'tier',
            'tier_id',
            'status',
            'current_period_start',
            'current_period_end',
            'created_at',
        ]
        read_only_fields = [
            'status',
            'current_period_start',
            'current_period_end',
            'created_at',
        ]
        # stripe_customer_id and stripe_subscription_id are
        # intentionally excluded — internal billing fields,
        # never exposed to the client