from django.contrib import admin
from .models import Song, Genre, MoodTag, Instrument

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'genre', 'bpm', 'duration', 'play_count', 'license_count', 'is_approved', 'uploaded_at']
    list_filter = ['is_approved', 'genre', 'mood_tags', 'instruments']
    search_fields = ['title', 'artist__username']
    list_editable = ['is_approved']

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