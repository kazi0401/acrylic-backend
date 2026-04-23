from django.db import models
from django.conf import settings

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class MoodTag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Instrument(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Song(models.Model):
    # Core info
    title = models.CharField(max_length=255)
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='songs'
    )
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    bpm = models.PositiveIntegerField(null=True, blank=True)

    # Audio files
    full_track = models.FileField(upload_to='songs/full/')
    preview_clip = models.FileField(upload_to='songs/previews/')

    # External links
    spotify_link = models.URLField(null=True, blank=True)
    apple_music_link = models.URLField(null=True, blank=True)

    # Metadata
    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    mood_tags = models.ManyToManyField(MoodTag, blank=True)
    instruments = models.ManyToManyField(Instrument, blank=True)

    # Performance metrics
    play_count = models.PositiveIntegerField(default=0)
    license_count = models.PositiveIntegerField(default=0)

    # Status
    is_approved = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.artist.username}"