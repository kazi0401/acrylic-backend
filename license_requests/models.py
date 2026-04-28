from django.db import models
from django.conf import settings

# Create your models here.
class LicenseRequest(models.Model): 

  client = models.ForeignKey(
      settings.AUTH_USER_MODEL, 
      on_delete=models.CASCADE,
      related_name='license_requests'
  )

  song = models.ForeignKey(
      'songs.Song',
      on_delete=models.SET_NULL, 
      null=True,
      blank=True,
      related_name='license_requests'
  )

  # External song information
  external_song_title = models.CharField(max_length=200, null=True, blank=True)
  external_artist_name = models.CharField(max_length=200, null=True, blank=True)
  external_url = models.URLField(null=True, blank=True)


  # Request Type
  class RequestType(models.TextChoices):
    INTERNAL = 'internal', 'Internal'
    EXTERNAL = 'external', 'External'

  request_type = models.CharField(
    max_length = 20,
    choices = RequestType.choices,
    default = RequestType.EXTERNAL
  )

  # Status
  class Status(models.TextChoices):
    SUBMITTED = 'submitted', 'Submitted'
    UNDER_REVIEW = 'under_review', 'Under Review'
    APPROVED = 'approved', 'Approved'
    DENIED = 'denied', 'Denied'
    UNABLE_TO_CLEAR = 'unable_to_clear', 'Unable to Clear'
  
  status = models.CharField(
    max_length = 20, 
    choices = Status.choices, 
    default = Status.SUBMITTED
  )


  usage_details = models.TextField()

  budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

  admin_notes = models.TextField(blank=True, default='')


  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
