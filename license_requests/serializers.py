from rest_framework import serializers
from .models import LicenseRequest


class LicenseRequestSerializer(serializers.ModelSerializer):
    class Meta:
      model = LicenseRequest
      fields = [
          'id', 'client', 'song',
          'external_song_title', 'external_artist_name', 'external_url',
          'request_type', 'status', 
          'usage_details', 'budget',
          'created_at', 'updated_at'
      ]
      read_only_fields = ['client', 'status', 'created_at', 'updated_at']

      def validate(self, data):
        if data.get('request_type') == 'internal' and not data.get('song'):
            raise serializers.ValidationError("Internal requests must include a song.")
        if data.get('request_type') == 'external' and not data.get('external_url'):
            raise serializers.ValidationError("External requests must include a URL.")
        return data

class LicenseRequestAdminSerializer(serializers.ModelSerializer): 
   class Meta: 
      model = LicenseRequest
      fields = ['id', 'status', 'admin_notes']
   
