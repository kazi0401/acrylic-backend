from django.test import TestCase

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from decimal import Decimal

from .models import Song, Genre, MoodTag, Instrument

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_audio_file(name='track.mp3'):
    """Return a minimal fake audio file for upload tests."""
    return SimpleUploadedFile(name, b'fake-audio-content', content_type='audio/mpeg')


def make_artist(username='artist1', role='artist'):
    return User.objects.create_user(username=username, password='pass', role=role)


def make_buyer(username='buyer1'):
    return User.objects.create_user(username=username, password='pass', role='client')


def make_song(artist, genre=None, **kwargs):
    """Create a minimal approved song for use in read-path tests."""
    defaults = dict(
        title='Test Song',
        duration=180,
        isrc='USRC17607839',
        full_track=make_audio_file('full.mp3'),
        preview_clip=make_audio_file('preview.mp3'),
        status=Song.Status.APPROVED,
    )
    defaults.update(kwargs)
    if genre:
        defaults['genre'] = genre
    return Song.objects.create(artist=artist, **defaults)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class SongModelTest(TestCase):

    def setUp(self):
        self.artist = make_artist()

    def test_str_returns_title_and_artist(self):
        song = make_song(self.artist, title='My Track')
        self.assertEqual(str(song), 'My Track by artist1')

    def test_default_status_is_draft(self):
        song = Song(
            title='Draft Track',
            artist=self.artist,
            duration=120,
            isrc='GBAYE0601498',
            full_track=make_audio_file(),
            preview_clip=make_audio_file('pre.mp3'),
        )
        self.assertEqual(song.status, Song.Status.DRAFT)

    def test_isrc_must_be_unique(self):
        make_song(self.artist, isrc='USRC17607839')
        artist2 = make_artist(username='artist2')
        with self.assertRaises(Exception):
            make_song(artist2, isrc='USRC17607839')

    def test_isrc_regex_rejects_invalid_format(self):
        from django.core.exceptions import ValidationError
        song = Song(
            title='Bad ISRC',
            artist=self.artist,
            duration=120,
            isrc='not-valid',
            full_track=make_audio_file(),
            preview_clip=make_audio_file('pre.mp3'),
        )
        with self.assertRaises(ValidationError):
            song.full_clean()

    def test_isrc_regex_accepts_valid_format(self):
        from django.core.exceptions import ValidationError
        song = Song(
            title='Good ISRC',
            artist=self.artist,
            duration=120,
            isrc='USRC17607839',
            full_track=make_audio_file(),
            preview_clip=make_audio_file('pre.mp3'),
        )
        try:
            song.full_clean()
        except ValidationError as e:
            if 'isrc' in e.message_dict:
                self.fail(f'Valid ISRC raised ValidationError: {e}')

    def test_bpm_is_optional(self):
        song = make_song(self.artist, isrc='GBAYE0601498', bpm=None)
        self.assertIsNone(song.bpm)

    def test_price_is_optional(self):
        song = make_song(self.artist, isrc='GBAYE0601498', price=None)
        self.assertIsNone(song.price)

    def test_price_stores_decimal(self):
        song = make_song(self.artist, isrc='GBAYE0601498', price=Decimal('49.99'))
        self.assertEqual(song.price, Decimal('49.99'))

    def test_deleting_artist_cascades_to_songs(self):
        make_song(self.artist)
        self.artist.delete()
        self.assertEqual(Song.objects.count(), 0)

    def test_deleting_genre_sets_null(self):
        genre = Genre.objects.create(name='Jazz')
        song = make_song(self.artist, genre=genre, isrc='GBAYE0601498')
        genre.delete()
        song.refresh_from_db()
        self.assertIsNone(song.genre)


# ---------------------------------------------------------------------------
# Song upload view tests  —  POST /api/songs/upload/
# ---------------------------------------------------------------------------

class SongUploadViewTest(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.artist = make_artist()
        self.url = '/api/songs/upload/'

    def _auth(self, user=None):
        self.client.force_authenticate(user=user or self.artist)

    # --- Auth & permission guards ---

    def test_unauthenticated_upload_returns_401(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=False)
    def test_unsigned_contract_returns_403(self, _mock):
        self._auth()
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Successful upload ---

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_valid_upload_returns_201(self, _mock):
        self._auth()
        genre = Genre.objects.create(name='Pop')
        data = {
            'title': 'My Track',
            'duration': 200,
            'isrc': 'USRC17607839',
            'full_track': make_audio_file('full.mp3'),
            'preview_clip': make_audio_file('preview.mp3'),
            'genre_id': genre.pk,
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_upload_sets_artist_to_requesting_user(self, _mock):
        self._auth()
        data = {
            'title': 'My Track',
            'duration': 200,
            'isrc': 'USRC17607839',
            'full_track': make_audio_file('full.mp3'),
            'preview_clip': make_audio_file('preview.mp3'),
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        song = Song.objects.get(pk=response.data['id'])
        self.assertEqual(song.artist, self.artist)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_upload_status_defaults_to_draft(self, _mock):
        self._auth()
        data = {
            'title': 'My Track',
            'duration': 200,
            'isrc': 'USRC17607839',
            'full_track': make_audio_file('full.mp3'),
            'preview_clip': make_audio_file('preview.mp3'),
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        song = Song.objects.get(pk=response.data['id'])
        self.assertEqual(song.status, Song.Status.DRAFT)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_upload_with_mood_tags_and_instruments(self, _mock):
        self._auth()
        mood = MoodTag.objects.create(name='Chill')
        instrument = Instrument.objects.create(name='Guitar')
        data = {
            'title': 'Tagged Track',
            'duration': 180,
            'isrc': 'USRC17607839',
            'full_track': make_audio_file('full.mp3'),
            'preview_clip': make_audio_file('preview.mp3'),
            'mood_tag_ids': [mood.pk],
            'instrument_ids': [instrument.pk],
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        song = Song.objects.get(pk=response.data['id'])
        self.assertIn(mood, song.mood_tags.all())
        self.assertIn(instrument, song.instruments.all())

    # --- Validation failures ---

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_missing_title_returns_400(self, _mock):
        self._auth()
        data = {
            'duration': 200,
            'isrc': 'USRC17607839',
            'full_track': make_audio_file('full.mp3'),
            'preview_clip': make_audio_file('preview.mp3'),
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_missing_isrc_returns_400(self, _mock):
        self._auth()
        data = {
            'title': 'No ISRC',
            'duration': 200,
            'full_track': make_audio_file('full.mp3'),
            'preview_clip': make_audio_file('preview.mp3'),
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('isrc', response.data)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_invalid_isrc_format_returns_400(self, _mock):
        self._auth()
        data = {
            'title': 'Bad ISRC',
            'duration': 200,
            'isrc': 'not-valid!!',
            'full_track': make_audio_file('full.mp3'),
            'preview_clip': make_audio_file('preview.mp3'),
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('isrc', response.data)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_duplicate_isrc_returns_400(self, _mock):
        self._auth()
        make_song(self.artist, isrc='USRC17607839')
        data = {
            'title': 'Duplicate ISRC',
            'duration': 200,
            'isrc': 'USRC17607839',
            'full_track': make_audio_file('full.mp3'),
            'preview_clip': make_audio_file('preview.mp3'),
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('isrc', response.data)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_missing_audio_files_returns_400(self, _mock):
        self._auth()
        data = {
            'title': 'No Files',
            'duration': 200,
            'isrc': 'USRC17607839',
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Song list view tests  —  GET /api/songs/
# ---------------------------------------------------------------------------

class SongListViewTest(APITestCase):

    def setUp(self):
        self.artist = make_artist()
        self.url = '/api/songs/'

    def test_returns_only_approved_songs(self):
        make_song(self.artist, isrc='USRC17607839', status=Song.Status.APPROVED)
        make_song(self.artist, isrc='GBAYE0601498', status=Song.Status.DRAFT)
        make_song(self.artist, isrc='GBAYE0601499', status=Song.Status.PENDING_REVIEW)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_no_auth_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_genre(self):
        jazz = Genre.objects.create(name='Jazz')
        pop = Genre.objects.create(name='Pop')
        make_song(self.artist, genre=jazz, isrc='USRC17607839')
        make_song(self.artist, genre=pop, isrc='GBAYE0601498')
        response = self.client.get(self.url, {'genre': 'jazz'})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['genre']['name'], 'Jazz')

    def test_filter_by_mood(self):
        chill = MoodTag.objects.create(name='Chill')
        song = make_song(self.artist, isrc='USRC17607839')
        song.mood_tags.add(chill)
        make_song(self.artist, isrc='GBAYE0601498')  # no mood
        response = self.client.get(self.url, {'mood': 'chill'})
        self.assertEqual(len(response.data), 1)

    def test_filter_by_bpm_range(self):
        make_song(self.artist, isrc='USRC17607839', bpm=90)
        make_song(self.artist, isrc='GBAYE0601498', bpm=120)
        make_song(self.artist, isrc='GBAYE0601499', bpm=150)
        response = self.client.get(self.url, {'min_bpm': 100, 'max_bpm': 130})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['bpm'], 120)

    def test_sort_by_play_count(self):
        make_song(self.artist, isrc='USRC17607839', play_count=5)
        make_song(self.artist, isrc='GBAYE0601498', play_count=20)
        make_song(self.artist, isrc='GBAYE0601499', play_count=1)
        response = self.client.get(self.url, {'sort_by': '-play_count'})
        counts = [s['play_count'] for s in response.data]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_invalid_sort_field_falls_back_to_default(self):
        make_song(self.artist, isrc='USRC17607839')
        # Should not raise, just ignore the invalid sort param
        response = self.client.get(self.url, {'sort_by': 'malicious_field'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Song detail view tests  —  GET /api/songs/<id>/
# ---------------------------------------------------------------------------

class SongDetailViewTest(APITestCase):

    def setUp(self):
        self.artist = make_artist()

    def test_returns_approved_song(self):
        song = make_song(self.artist)
        response = self.client.get(f'/api/songs/{song.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], song.title)

    def test_returns_404_for_unapproved_song(self):
        song = make_song(self.artist, isrc='USRC17607839', status=Song.Status.DRAFT)
        response = self.client.get(f'/api/songs/{song.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_404_for_nonexistent_song(self):
        response = self.client.get('/api/songs/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_auth_required(self):
        song = make_song(self.artist)
        response = self.client.get(f'/api/songs/{song.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Record play view tests  —  POST /api/songs/<id>/play/
# ---------------------------------------------------------------------------

class RecordPlayViewTest(APITestCase):

    def setUp(self):
        self.artist = make_artist()
        self.buyer = make_buyer()
        self.song = make_song(self.artist)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_increments_play_count(self, _mock):
        self.client.force_authenticate(user=self.buyer)
        before = self.song.play_count
        response = self.client.post(f'/api/songs/{self.song.pk}/play/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.song.refresh_from_db()
        self.assertEqual(self.song.play_count, before + 1)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_returns_updated_play_count(self, _mock):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(f'/api/songs/{self.song.pk}/play/')
        self.assertIn('play_count', response.data)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=False)
    def test_unsigned_contract_returns_403(self, _mock):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(f'/api/songs/{self.song.pk}/play/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_play_on_nonexistent_song_returns_404(self, _mock):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post('/api/songs/99999/play/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('contracts.permissions.HasSignedContract.has_permission', return_value=True)
    def test_play_on_unapproved_song_returns_404(self, _mock):
        self.client.force_authenticate(user=self.buyer)
        draft_song = make_song(self.artist, isrc='GBAYE0601498', status=Song.Status.DRAFT)
        response = self.client.post(f'/api/songs/{draft_song.pk}/play/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Metadata list view tests  —  GET /api/songs/genres|moods|instruments/
# ---------------------------------------------------------------------------

class MetadataListViewTest(APITestCase):

    def test_genre_list(self):
        Genre.objects.create(name='Jazz')
        Genre.objects.create(name='Pop')
        response = self.client.get('/api/songs/genres/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_mood_list(self):
        MoodTag.objects.create(name='Chill')
        response = self.client.get('/api/songs/moods/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_instrument_list(self):
        Instrument.objects.create(name='Guitar')
        response = self.client.get('/api/songs/instruments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_no_auth_required_for_metadata(self):
        for url in ['/api/songs/genres/', '/api/songs/moods/', '/api/songs/instruments/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)