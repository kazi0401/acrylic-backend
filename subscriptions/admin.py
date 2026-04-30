from django.contrib import admin
from .models import SubscriptionTier, BuyerSubscription


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price_annual', 'includes_artist_promo', 'is_active']
    list_filter = ['is_active', 'includes_artist_promo']
    search_fields = ['name']


@admin.register(BuyerSubscription)
class BuyerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_username', 'tier', 'status', 'current_period_start', 'current_period_end', 'created_at']
    list_filter = ['status', 'tier']
    search_fields = ['profile__user__username']
    readonly_fields = [
        'stripe_customer_id',
        'stripe_subscription_id',
        'current_period_start',
        'current_period_end',
        'created_at'
    ]

    def get_username(self, obj):
        return obj.profile.user.username
    get_username.short_description = 'Buyer'
