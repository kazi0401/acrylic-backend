from django.db import models

class Song(models.Model):
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    audience_size = models.CharField(max_length=10)  # e.g., '<1000' or '1500'
    sports_audience_fit = models.FloatField()  # percentage
    track_virality = models.FloatField()  # percentage
    audio_file = models.FileField(upload_to='songs/audio/', blank=True, null=True)  # path to audio file

    def __str__(self):
        return self.title
