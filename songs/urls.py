from django.urls import path
from .views import (
    SongUploadView,
    SongListView,
    SongDetailView,
    SongEditView,
    SongArchiveView,
    SongRestoreView,
    MyTracksView,
    RecordPlayView,
    GenreListView,
    MoodTagListView,
    InstrumentListView,
)

urlpatterns = [
    # Public catalog
    path('', SongListView.as_view(), name='song-list'),
    path('<int:pk>/', SongDetailView.as_view(), name='song-detail'),
    path('<int:pk>/play/', RecordPlayView.as_view(), name='record-play'),

    # Metadata lookups (no auth)
    path('genres/', GenreListView.as_view(), name='genre-list'),
    path('moods/', MoodTagListView.as_view(), name='mood-list'),
    path('instruments/', InstrumentListView.as_view(), name='instrument-list'),

    # Artist track management (auth + rightsholder contract + ownership)
    path('upload/', SongUploadView.as_view(), name='song-upload'),
    path('my-tracks/', MyTracksView.as_view(), name='my-tracks'),
    path('<int:pk>/edit/', SongEditView.as_view(), name='song-edit'),
    path('<int:pk>/archive/', SongArchiveView.as_view(), name='song-archive'),
    path('<int:pk>/restore/', SongRestoreView.as_view(), name='song-restore'),
]