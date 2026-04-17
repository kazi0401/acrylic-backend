from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Song, Genre, MoodTag, Instrument
from .serializers import SongSerializer, GenreSerializer, MoodTagSerializer, InstrumentSerializer


class SongUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = SongSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(artist=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SongListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SongSerializer

    def get_queryset(self):
        queryset = Song.objects.filter(is_approved=True)

        # Filtering
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

        # Sorting
        sort_by = self.request.query_params.get('sort_by', '-uploaded_at')
        allowed_sort_fields = ['bpm', '-bpm', 'duration', '-duration', 'uploaded_at', '-uploaded_at', 'play_count', '-play_count']
        if sort_by in allowed_sort_fields:
            queryset = queryset.order_by(sort_by)

        return queryset


class SongDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = SongSerializer
    queryset = Song.objects.filter(is_approved=True)


class RecordPlayView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        try:
            song = Song.objects.get(pk=pk, is_approved=True)
            song.play_count += 1
            song.save()
            return Response({'play_count': song.play_count})
        except Song.DoesNotExist:
            return Response({'error': 'Song not found'}, status=status.HTTP_404_NOT_FOUND)


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