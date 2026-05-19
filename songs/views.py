from rest_framework import status as drf_status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from django.shortcuts import get_object_or_404

from .models import Song, Genre, MoodTag, Instrument
from .serializers import SongSerializer, GenreSerializer, MoodTagSerializer, InstrumentSerializer, SongEditSerializer

from contracts.permissions import HasSignedContract
from users.permissions import IsArtist
from .permissions import IsTrackOwner


class SongUploadView(APIView):
    # IsArtist added: only artists should be able to upload tracks.
    # Stacked after IsAuthenticated so unauthenticated requests get 401, not 403.
    permission_classes = [IsAuthenticated, IsArtist, HasSignedContract]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = SongSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(artist=request.user)
            return Response(serializer.data, status=drf_status.HTTP_201_CREATED)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


class MyTracksView(generics.ListAPIView):
    """
    GET /api/songs/my-tracks/
    Returns all tracks belonging to the authenticated artist, across all
    statuses (draft, pending_review, approved, rejected, archived).
    Ordered newest-first so the dashboard shows recent uploads at the top.

    Auth: IsAuthenticated + IsArtist + HasSignedContract (rightsholder contract).
    Clients and admins hitting this endpoint get 403.
    """
    permission_classes = [IsAuthenticated, IsArtist, HasSignedContract]
    serializer_class = SongSerializer

    def get_queryset(self):
        return Song.objects.filter(artist=self.request.user).order_by('-uploaded_at')

    # Override to pass request into get_queryset correctly via self.request
    def get_queryset(self):
        return Song.objects.filter(artist=self.request.user).order_by('-uploaded_at')


class SongListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SongSerializer

    def get_queryset(self):
        queryset = Song.objects.filter(status=Song.Status.APPROVED)

        genre = self.request.query_params.get('genre')
        mood = self.request.query_params.get('mood')
        instrument = self.request.query_params.get('instrument')
        min_bpm = self.request.query_params.get('min_bpm')
        max_bpm = self.request.query_params.get('max_bpm')

        if genre:
            queryset = queryset.filter(genre__name__icontains=genre)
        if mood:
            queryset = queryset.filter(mood_tags__name__icontains=mood)
        if instrument:
            queryset = queryset.filter(instruments__name__icontains=instrument)
        if min_bpm:
            queryset = queryset.filter(bpm__gte=min_bpm)
        if max_bpm:
            queryset = queryset.filter(bpm__lte=max_bpm)

        sort_by = self.request.query_params.get('sort_by', '-uploaded_at')
        allowed_sort_fields = [
            'bpm', '-bpm', 'duration', '-duration',
            'uploaded_at', '-uploaded_at',
            'play_count', '-play_count',
        ]
        if sort_by in allowed_sort_fields:
            queryset = queryset.order_by(sort_by)

        return queryset


class SongDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = SongSerializer
    queryset = Song.objects.filter(status=Song.Status.APPROVED)


class SongEditView(APIView):
    permission_classes = [IsAuthenticated, HasSignedContract, IsTrackOwner]
    serializer_class = SongEditSerializer

    def patch(self, request, pk):
        song = get_object_or_404(Song, pk=pk)
        self.check_object_permissions(request, song)

        if song.status not in [Song.Status.DRAFT, Song.Status.REJECTED]:
            return Response(
                {"detail": "This track can no longer be edited."},
                status=drf_status.HTTP_403_FORBIDDEN
            )

        serializer = SongEditSerializer(song, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


class SongArchiveView(APIView):
    """
    POST /api/songs/<id>/archive/
    Soft-deletes a track by setting status to archived.
    Any non-archived song owned by the artist can be archived.
    Requires JWT + signed rightsholder contract + ownership.
    """
    permission_classes = [IsAuthenticated, HasSignedContract, IsTrackOwner]

    def post(self, request, pk):
        song = get_object_or_404(Song, pk=pk)
        self.check_object_permissions(request, song)

        if song.status == Song.Status.ARCHIVED:
            return Response(
                {"detail": "Track is already archived."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        song.status = Song.Status.ARCHIVED
        song.save()
        return Response(
            {"detail": "Track archived.", "status": song.status},
            status=drf_status.HTTP_200_OK
        )


class SongRestoreView(APIView):
    """
    POST /api/songs/<id>/restore/
    Restores an archived track back to draft so the artist can re-edit
    and re-submit it. Only archived tracks can be restored.
    Requires JWT + signed rightsholder contract + ownership.
    """
    permission_classes = [IsAuthenticated, HasSignedContract, IsTrackOwner]

    def post(self, request, pk):
        song = get_object_or_404(Song, pk=pk)
        self.check_object_permissions(request, song)

        if song.status != Song.Status.ARCHIVED:
            return Response(
                {"detail": "Only archived tracks can be restored."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        song.status = Song.Status.DRAFT
        song.save()
        return Response(
            {"detail": "Track restored to draft.", "status": song.status},
            status=drf_status.HTTP_200_OK
        )


class RecordPlayView(APIView):
    permission_classes = [HasSignedContract]

    def post(self, request, pk):
        try:
            song = Song.objects.get(pk=pk, status=Song.Status.APPROVED)
            song.play_count += 1
            song.save()
            return Response({'play_count': song.play_count})
        except Song.DoesNotExist:
            return Response({'error': 'Song not found'}, status=drf_status.HTTP_404_NOT_FOUND)


class GenreListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = GenreSerializer
    queryset = Genre.objects.all()


class MoodTagListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = MoodTagSerializer
    queryset = MoodTag.objects.all()


class InstrumentListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = InstrumentSerializer
    queryset = Instrument.objects.all()