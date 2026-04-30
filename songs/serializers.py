from rest_framework import serializers
from .models import Song, Genre, MoodTag, Instrument


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']


class MoodTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodTag
        fields = ['id', 'name']


class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ['id', 'name']


class SongSerializer(serializers.ModelSerializer):
    genre = GenreSerializer(read_only=True)
    mood_tags = MoodTagSerializer(many=True, read_only=True)
    instruments = InstrumentSerializer(many=True, read_only=True)

    # Write-only fields for uploading
    genre_id = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        source='genre',
        write_only=True,
        required=False
    )
    mood_tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=MoodTag.objects.all(),
        source='mood_tags',
        write_only=True,
        many=True,
        required=False
    )
    instrument_ids = serializers.PrimaryKeyRelatedField(
        queryset=Instrument.objects.all(),
        source='instruments',
        write_only=True,
        many=True,
        required=False
    )

    class Meta:
        model = Song
        fields = [
            'id', 'title', 'artist', 'duration', 'bpm',
            'full_track', 'preview_clip',
            'spotify_link', 'apple_music_link',
            'genre', 'mood_tags', 'instruments',
            'genre_id', 'mood_tag_ids', 'instrument_ids',
            'play_count', 'license_count',
            'status', 'uploaded_at', 'isrc',
            'track_tier', 'fixed_price',
        ]
        read_only_fields = [
            'artist', 'play_count', 'license_count',
            'status', 'uploaded_at'
        ]


class SongEditSerializer(serializers.ModelSerializer):
    genre = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        required=False
    )
    mood_tags = serializers.PrimaryKeyRelatedField(
        queryset=MoodTag.objects.all(),
        many=True,
        required=False
    )
    instruments = serializers.PrimaryKeyRelatedField(
        queryset=Instrument.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Song
        fields = [
            'title',
            'genre',
            'mood_tags',
            'instruments',
            'track_tier',
            'fixed_price',
        ]

    def validate(self, data):
        # On edits we may only be updating one field at a time,
        # so fall back to the instance value if not provided
        tier = data.get('track_tier', self.instance.track_tier if self.instance else None)
        fixed_price = data.get('fixed_price', self.instance.fixed_price if self.instance else None)

        if tier == Song.TrackTier.PRECLEAR and fixed_price is None:
            raise serializers.ValidationError(
                "PreClear tracks must have a fixed price."
            )
        if tier == Song.TrackTier.ARTIST_PROMO and fixed_price is not None:
            raise serializers.ValidationError(
                "Artist Promo tracks cannot have a price."
            )
        if tier == Song.TrackTier.BID2CLEAR and fixed_price is not None:
            raise serializers.ValidationError(
                "Bid2Clear tracks do not use a fixed price."
            )
        return data