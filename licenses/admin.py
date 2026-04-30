from django.contrib import admin
from .models import License


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'get_username',
        'get_song_title',
        'license_type',
        'status',
        'price_paid',
        'valid_from',
        'valid_until',
        'created_at'
    ]
    list_filter = ['license_type', 'status']
    search_fields = [
        'client__user__username',
        'song__title'
    ]
    readonly_fields = [
        'client',
        'song',
        'license_type',
        'subscription',
        'stripe_payment_intent_id',
        'price_paid',
        'valid_from',
        'created_at'
    ]
    # Only status is editable in admin — for manual revocation if needed

    def get_username(self, obj):
        return obj.client.user.username
    get_username.short_description = 'Buyer'

    def get_song_title(self, obj):
        return obj.song.title
    get_song_title.short_description = 'Song'
