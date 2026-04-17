from django.urls import path
from .views import (
    SongUploadView, SongListView, SongDetailView,
    RecordPlayView, GenreListView, MoodTagListView, InstrumentListView
)

urlpatterns = [
    path('', SongListView.as_view(), name='song-list'),
    path('upload/', SongUploadView.as_view(), name='song-upload'),
    path('<int:pk>/', SongDetailView.as_view(), name='song-detail'),
    path('<int:pk>/play/', RecordPlayView.as_view(), name='record-play'),
    path('genres/', GenreListView.as_view(), name='genre-list'),
    path('moods/', MoodTagListView.as_view(), name='mood-list'),
    path('instruments/', InstrumentListView.as_view(), name='instrument-list'),
]