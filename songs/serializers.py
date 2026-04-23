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
            'is_approved', 'uploaded_at'
        ]
        read_only_fields = ['artist', 'play_count', 'license_count', 'is_approved', 'uploaded_at']