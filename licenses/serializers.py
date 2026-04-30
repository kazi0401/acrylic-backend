from rest_framework import serializers
from django.utils import timezone
from .models import License
from songs.models import Song
from subscriptions.models import BuyerSubscription


class LicenseSerializer(serializers.ModelSerializer):
    """
    Used by buyers to view their licenses.
    All billing and internal fields are read only.
    """
    song_title = serializers.CharField(source='song.title', read_only=True)
    song_artist = serializers.CharField(source='song.artist.username', read_only=True)
    tier = serializers.CharField(source='song.track_tier', read_only=True)

    class Meta:
        model = License
        fields = [
            'id',
            'song',
            'song_title',
            'song_artist',
            'tier',
            'license_type',
            'status',
            'price_paid',
            'usage_details',
            'valid_from',
            'valid_until',
            'created_at',
        ]
        read_only_fields = [
            'license_type',
            'status',
            'price_paid',
            'valid_from',
            'created_at',
        ]


class PreClearLicenseSerializer(serializers.ModelSerializer):
    """
    Used by buyers to submit a PreClear license request.
    Buyer provides song and usage details.
    Price, type, and Stripe fields are handled by the view.
    """
    class Meta:
        model = License
        fields = [
            'song',
            'usage_details',
            'valid_until',
        ]

    def validate_song(self, song):
        # Must be approved and in the catalog
        if song.status != 'approved':
            raise serializers.ValidationError(
                "This song is not available for licensing."
            )
        # Must be a PreClear track
        if song.track_tier != 'preclear':
            raise serializers.ValidationError(
                "This song is not a PreClear track."
            )
        # Must have a fixed price set
        if song.fixed_price is None:
            raise serializers.ValidationError(
                "This track does not have a price set."
            )
        return song


class ArtistPromoLicenseSerializer(serializers.ModelSerializer):
    """
    Used by buyers to license an Artist Promo track.
    Requires an active subscription. No charge.
    """
    class Meta:
        model = License
        fields = [
            'song',
            'usage_details',
            'valid_until',
        ]

    def validate_song(self, song):
        # Must be approved and in the catalog
        if song.status != 'approved':
            raise serializers.ValidationError(
                "This song is not available for licensing."
            )
        # Must be an Artist Promo track
        if song.track_tier != 'artist_promo':
            raise serializers.ValidationError(
                "This song is not an Artist Promo track."
            )
        return song