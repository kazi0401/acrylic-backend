from django.contrib import admin
from .models import Song, Genre, MoodTag, Instrument

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'genre', 'bpm', 'duration', 'play_count', 'license_count', 'status', 'uploaded_at']
    list_filter = ['status', 'genre', 'mood_tags', 'instruments']
    search_fields = ['title', 'artist__username']
    list_editable = ['status']

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(MoodTag)
class MoodTagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']