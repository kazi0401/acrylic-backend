from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsArtist(BasePermission):
    """
    Allows access only to users with role == 'artist'.
    Use on any view that should be artist-only (e.g. upload, my-tracks).
    Stack after IsAuthenticated so unauthenticated requests get 401, not 403.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'artist'
        )