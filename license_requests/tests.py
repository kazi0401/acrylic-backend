from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import LicenseRequest
from songs.models import Song, Genre

User = get_user_model()


class LicenseRequestModelTests(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.genre = Genre.objects.create(name='Jazz')
        self.song = Song.objects.create(
            title='Test Song',
            artist=self.buyer,
            duration=180,
            isrc='USRC17607839',
            genre=self.genre,
            status=Song.Status.APPROVED
        )

    def test_default_status_is_submitted(self):
        lr = LicenseRequest.objects.create(
            client=self.buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='For our Instagram campaign.'
        )
        self.assertEqual(lr.status, LicenseRequest.Status.SUBMITTED)

    def test_external_request_without_song(self):
        lr = LicenseRequest.objects.create(
            client=self.buyer,
            request_type=LicenseRequest.RequestType.EXTERNAL,
            external_song_title='My Song',
            external_artist_name='Some Artist',
            external_url='https://open.spotify.com/track/123',
            usage_details='For our campaign.'
        )
        self.assertIsNone(lr.song)

    def test_str_or_id_is_present(self):
        lr = LicenseRequest.objects.create(
            client=self.buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='Campaign use.'
        )
        self.assertIsNotNone(lr.id)


class LicenseRequestViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.admin = User.objects.create_user(
            username='admin1', password='testpass', role='admin'
        )
        self.genre = Genre.objects.create(name='Jazz')
        self.song = Song.objects.create(
            title='Test Song',
            artist=self.buyer,
            duration=180,
            isrc='USRC17607839',
            genre=self.genre,
            status=Song.Status.APPROVED
        )

        # Give buyer a signed contract
        from contracts.models import Contract
        from django.utils import timezone
        self.contract = Contract.objects.create(
            user=self.buyer,
            contract_type='buyer',
            version='v1.0',
            status='signed',
            signwell_document_id='mock-doc-id',
            expires_at=timezone.now() + timezone.timedelta(days=365)
        )

    def _authenticate_buyer(self):
        self.client_http.force_authenticate(user=self.buyer)

    def _authenticate_admin(self):
        self.client_http.force_authenticate(user=self.admin)

    # --- LicenseRequestView (POST, GET) ---

    def test_submit_internal_request_success(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/license-requests/', {
            'song': self.song.id,
            'request_type': 'internal',
            'usage_details': 'Instagram campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LicenseRequest.objects.count(), 1)

    def test_submit_external_request_success(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/license-requests/', {
            'request_type': 'external',
            'external_song_title': 'Some Song',
            'external_artist_name': 'Some Artist',
            'external_url': 'https://open.spotify.com/track/123',
            'usage_details': 'TikTok campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_submit_internal_request_without_song_fails(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/license-requests/', {
            'request_type': 'internal',
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_external_request_without_url_fails(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/license-requests/', {
            'request_type': 'external',
            'external_song_title': 'Some Song',
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_submit(self):
        response = self.client_http.post('/api/license-requests/', {
            'request_type': 'internal',
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unsigned_contract_cannot_submit(self):
        unsigned_buyer = User.objects.create_user(
            username='unsigned', password='testpass', role='client'
        )
        self.client_http.force_authenticate(user=unsigned_buyer)
        response = self.client_http.post('/api/license-requests/', {
            'request_type': 'internal',
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_buyer_can_list_own_requests(self):
        self._authenticate_buyer()
        LicenseRequest.objects.create(
            client=self.buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='Campaign.'
        )
        response = self.client_http.get('/api/license-requests/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_buyer_cannot_see_other_buyers_requests(self):
        other_buyer = User.objects.create_user(
            username='other', password='testpass', role='client'
        )
        LicenseRequest.objects.create(
            client=other_buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='Other campaign.'
        )
        self._authenticate_buyer()
        response = self.client_http.get('/api/license-requests/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    # --- LicenseRequestDetailView (buyer GET) ---

    def test_buyer_can_retrieve_own_request(self):
        self._authenticate_buyer()
        lr = LicenseRequest.objects.create(
            client=self.buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='Campaign.'
        )
        response = self.client_http.get(f'/api/license-requests/{lr.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buyer_cannot_retrieve_other_buyers_request(self):
        other_buyer = User.objects.create_user(
            username='other', password='testpass', role='client'
        )
        lr = LicenseRequest.objects.create(
            client=other_buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='Campaign.'
        )
        self._authenticate_buyer()
        response = self.client_http.get(f'/api/license-requests/{lr.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- LicenseRequestAdminView (admin PATCH) ---

    def test_admin_can_update_status(self):
        self._authenticate_admin()
        lr = LicenseRequest.objects.create(
            client=self.buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='Campaign.'
        )
        response = self.client_http.patch(f'/api/license-requests/{lr.id}/review/', {
            'status': 'under_review'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lr.refresh_from_db()
        self.assertEqual(lr.status, LicenseRequest.Status.UNDER_REVIEW)

    def test_admin_can_add_notes(self):
        self._authenticate_admin()
        lr = LicenseRequest.objects.create(
            client=self.buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='Campaign.'
        )
        response = self.client_http.patch(f'/api/license-requests/{lr.id}/review/', {
            'admin_notes': 'Contacted rightsholder, awaiting response.'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lr.refresh_from_db()
        self.assertEqual(lr.admin_notes, 'Contacted rightsholder, awaiting response.')

    def test_non_admin_cannot_update_status(self):
        self._authenticate_buyer()
        lr = LicenseRequest.objects.create(
            client=self.buyer,
            song=self.song,
            request_type=LicenseRequest.RequestType.INTERNAL,
            usage_details='Campaign.'
        )
        response = self.client_http.patch(f'/api/license-requests/{lr.id}/review/', {
            'status': 'approved'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_update_nonexistent_request_returns_404(self):
        self._authenticate_admin()
        response = self.client_http.patch('/api/license-requests/999/review/', {
            'status': 'approved'
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
