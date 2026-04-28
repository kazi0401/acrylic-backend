
from rest_framework.permissions import BasePermission
from django.conf import settings
from .models import Song

class IsTrackOwner(BasePermission):

    def has_object_permission(self, request, view, object):
        return object.artist == request.user