from django.contrib import admin
from .models import LicenseRequest


@admin.register(LicenseRequest)
class LicenseRequestAdmin(admin.ModelAdmin):

    list_display = [
        'id', 'client', 'song', 'request_type', 'status', 'created_at'
    ]

    list_filter = [
        'status', 'request_type'
    ]

    search_fields = [
        'client__username', 'external_song_title', 'external_artist_name'
    ]

    readonly_fields = [
        'client', 'song',
        'external_song_title', 'external_artist_name', 'external_url',
        'request_type', 'usage_details', 'budget',
        'created_at', 'updated_at'
    ]
