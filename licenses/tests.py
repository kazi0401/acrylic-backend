from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from .models import License
from songs.models import Song, Genre
from users.models import ClientProfile
from subscriptions.models import SubscriptionTier, BuyerSubscription

User = get_user_model()


class LicenseModelTests(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = self.buyer.client_profile
        self.artist = User.objects.create_user(
            username='artist1', password='testpass', role='artist'
        )
        self.genre = Genre.objects.create(name='Hip-Hop')
        self.preclear_song = Song.objects.create(
            title='PreClear Track',
            artist=self.artist,
            duration=180,
            isrc='USRC17600001',
            genre=self.genre,
            status=Song.Status.APPROVED,
            track_tier=Song.TrackTier.PRECLEAR,
            fixed_price='299.00',
            full_track='songs/full/test.mp3',
            preview_clip='songs/previews/test.mp3'
        )
        self.promo_song = Song.objects.create(
            title='Artist Promo Track',
            artist=self.artist,
            duration=200,
            isrc='USRC17600002',
            genre=self.genre,
            status=Song.Status.APPROVED,
            track_tier=Song.TrackTier.ARTIST_PROMO,
            fixed_price=None,
            full_track='songs/full/test2.mp3',
            preview_clip='songs/previews/test2.mp3'
        )

    def test_default_status_is_active(self):
        license = License.objects.create(
            client=self.profile,
            song=self.preclear_song,
            license_type=License.LicenseType.PRECLEAR,
            price_paid='299.00',
            usage_details='Instagram campaign.',
            valid_from=timezone.now()
        )
        self.assertEqual(license.status, License.Status.ACTIVE)

    def test_artist_promo_license_has_no_price(self):
        tier = SubscriptionTier.objects.create(
            name='Pro',
            price_annual='5000.00',
            includes_artist_promo=True
        )
        sub = BuyerSubscription.objects.create(
            profile=self.profile,
            tier=tier,
            stripe_customer_id='cus_mock_1',
            stripe_subscription_id='sub_mock_1',
            status=BuyerSubscription.Status.ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=365)
        )
        license = License.objects.create(
            client=self.profile,
            song=self.promo_song,
            license_type=License.LicenseType.ARTIST_PROMO,
            subscription=sub,
            price_paid=None,
            usage_details='TikTok campaign.',
            valid_from=timezone.now()
        )
        self.assertIsNone(license.price_paid)

    def test_license_str(self):
        license = License.objects.create(
            client=self.profile,
            song=self.preclear_song,
            license_type=License.LicenseType.PRECLEAR,
            price_paid='299.00',
            usage_details='Campaign.',
            valid_from=timezone.now()
        )
        self.assertIn('buyer1', str(license))
        self.assertIn('PreClear Track', str(license))


class PreClearLicenseViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = self.buyer.client_profile
        self.artist = User.objects.create_user(
            username='artist1', password='testpass', role='artist'
        )
        self.genre = Genre.objects.create(name='Hip-Hop')
        self.song = Song.objects.create(
            title='PreClear Track',
            artist=self.artist,
            duration=180,
            isrc='USRC17600001',
            genre=self.genre,
            status=Song.Status.APPROVED,
            track_tier=Song.TrackTier.PRECLEAR,
            fixed_price='299.00',
            full_track='songs/full/test.mp3',
            preview_clip='songs/previews/test.mp3'
        )
        self.song.refresh_from_db()
        
        self.promo_song = Song.objects.create(
            title='Promo Track',
            artist=self.artist,
            duration=180,
            isrc='USRC17600002',
            genre=self.genre,
            status=Song.Status.APPROVED,
            track_tier=Song.TrackTier.ARTIST_PROMO,
            fixed_price=None,
            full_track='songs/full/test2.mp3',
            preview_clip='songs/previews/test2.mp3'
        )

        from contracts.models import Contract
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

    def test_buyer_can_license_preclear_track(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/licenses/preclear/', {
            'song': self.song.id,
            'usage_details': 'Instagram campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(License.objects.count(), 1)

    def test_license_type_is_preclear(self):
        self._authenticate_buyer()
        self.client_http.post('/api/licenses/preclear/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        license = License.objects.first()
        self.assertEqual(license.license_type, License.LicenseType.PRECLEAR)

    def test_price_paid_matches_song_fixed_price(self):
        self._authenticate_buyer()
        self.client_http.post('/api/licenses/preclear/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        license = License.objects.first()
        self.assertEqual(license.price_paid, self.song.fixed_price)

    def test_cannot_preclear_an_artist_promo_song(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/licenses/preclear/', {
            'song': self.promo_song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_license(self):
        response = self.client_http.post('/api/licenses/preclear/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unsigned_contract_cannot_license(self):
        unsigned_buyer = User.objects.create_user(
            username='unsigned', password='testpass', role='client'
        )
        # Signal creates the profile automatically, no manual create needed
        self.client_http.force_authenticate(user=unsigned_buyer)
        response = self.client_http.post('/api/licenses/preclear/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unapproved_song_cannot_be_licensed(self):
        self._authenticate_buyer()
        draft_song = Song.objects.create(
            title='Draft Track',
            artist=self.artist,
            duration=180,
            isrc='USRC17600003',
            genre=self.genre,
            status=Song.Status.DRAFT,
            track_tier=Song.TrackTier.PRECLEAR,
            fixed_price='199.00',
            full_track='songs/full/test3.mp3',
            preview_clip='songs/previews/test3.mp3'
        )
        response = self.client_http.post('/api/licenses/preclear/', {
            'song': draft_song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ArtistPromoLicenseViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = self.buyer.client_profile
        self.artist = User.objects.create_user(
            username='artist1', password='testpass', role='artist'
        )
        self.genre = Genre.objects.create(name='Hip-Hop')
        self.song = Song.objects.create(
            title='Artist Promo Track',
            artist=self.artist,
            duration=180,
            isrc='USRC17600001',
            genre=self.genre,
            status=Song.Status.APPROVED,
            track_tier=Song.TrackTier.ARTIST_PROMO,
            fixed_price=None,
            full_track='songs/full/test.mp3',
            preview_clip='songs/previews/test.mp3'
        )
        self.preclear_song = Song.objects.create(
            title='PreClear Track',
            artist=self.artist,
            duration=180,
            isrc='USRC17600002',
            genre=self.genre,
            status=Song.Status.APPROVED,
            track_tier=Song.TrackTier.PRECLEAR,
            fixed_price='299.00',
            full_track='songs/full/test2.mp3',
            preview_clip='songs/previews/test2.mp3'
        )
        self.tier = SubscriptionTier.objects.create(
            name='Pro',
            price_annual='5000.00',
            includes_artist_promo=True
        )

        from contracts.models import Contract
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

    def _give_buyer_subscription(self):
        return BuyerSubscription.objects.create(
            profile=self.profile,
            tier=self.tier,
            stripe_customer_id='cus_mock_1',
            stripe_subscription_id='sub_mock_1',
            status=BuyerSubscription.Status.ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=365)
        )

    def test_subscribed_buyer_can_license_promo_track(self):
        self._give_buyer_subscription()
        self._authenticate_buyer()
        response = self.client_http.post('/api/licenses/artist-promo/', {
            'song': self.song.id,
            'usage_details': 'TikTok campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(License.objects.count(), 1)

    def test_artist_promo_license_has_no_price(self):
        self._give_buyer_subscription()
        self._authenticate_buyer()
        self.client_http.post('/api/licenses/artist-promo/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        license = License.objects.first()
        self.assertIsNone(license.price_paid)

    def test_license_linked_to_subscription(self):
        sub = self._give_buyer_subscription()
        self._authenticate_buyer()
        self.client_http.post('/api/licenses/artist-promo/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        license = License.objects.first()
        self.assertEqual(license.subscription, sub)

    def test_unsubscribed_buyer_cannot_license_promo(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/licenses/artist-promo/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_artist_promo_a_preclear_song(self):
        self._give_buyer_subscription()
        self._authenticate_buyer()
        response = self.client_http.post('/api/licenses/artist-promo/', {
            'song': self.preclear_song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_license(self):
        response = self.client_http.post('/api/licenses/artist-promo/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unsigned_contract_cannot_license(self):
        unsigned_buyer = User.objects.create_user(
            username='unsigned', password='testpass', role='client'
        )
        # Signal creates the profile automatically, no manual create needed
        self.client_http.force_authenticate(user=unsigned_buyer)
        response = self.client_http.post('/api/licenses/artist-promo/', {
            'song': self.song.id,
            'usage_details': 'Campaign.'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MyLicensesViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = self.buyer.client_profile
        self.artist = User.objects.create_user(
            username='artist1', password='testpass', role='artist'
        )
        self.genre = Genre.objects.create(name='Hip-Hop')
        self.song = Song.objects.create(
            title='PreClear Track',
            artist=self.artist,
            duration=180,
            isrc='USRC17600001',
            genre=self.genre,
            status=Song.Status.APPROVED,
            track_tier=Song.TrackTier.PRECLEAR,
            fixed_price='299.00',
            full_track='songs/full/test.mp3',
            preview_clip='songs/previews/test.mp3'
        )

        from contracts.models import Contract
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

    def test_buyer_can_list_own_licenses(self):
        License.objects.create(
            client=self.profile,
            song=self.song,
            license_type=License.LicenseType.PRECLEAR,
            price_paid='299.00',
            usage_details='Campaign.',
            valid_from=timezone.now(),
            status=License.Status.ACTIVE
        )
        self._authenticate_buyer()
        response = self.client_http.get('/api/licenses/my-licenses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_buyer_cannot_see_other_buyers_licenses(self):
        other_buyer = User.objects.create_user(
            username='other', password='testpass', role='client'
        )
        # Signal creates the profile automatically
        other_profile = other_buyer.client_profile
        License.objects.create(
            client=other_profile,
            song=self.song,
            license_type=License.LicenseType.PRECLEAR,
            price_paid='299.00',
            usage_details='Campaign.',
            valid_from=timezone.now(),
            status=License.Status.ACTIVE
        )
        self._authenticate_buyer()
        response = self.client_http.get('/api/licenses/my-licenses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_unauthenticated_cannot_list_licenses(self):
        response = self.client_http.get('/api/licenses/my-licenses/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LicenseDetailViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = self.buyer.client_profile
        self.artist = User.objects.create_user(
            username='artist1', password='testpass', role='artist'
        )
        self.genre = Genre.objects.create(name='Hip-Hop')
        self.song = Song.objects.create(
            title='PreClear Track',
            artist=self.artist,
            duration=180,
            isrc='USRC17600001',
            genre=self.genre,
            status=Song.Status.APPROVED,
            track_tier=Song.TrackTier.PRECLEAR,
            fixed_price='299.00',
            full_track='songs/full/test.mp3',
            preview_clip='songs/previews/test.mp3'
        )

        from contracts.models import Contract
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

    def test_buyer_can_retrieve_own_license(self):
        license = License.objects.create(
            client=self.profile,
            song=self.song,
            license_type=License.LicenseType.PRECLEAR,
            price_paid='299.00',
            usage_details='Campaign.',
            valid_from=timezone.now(),
            status=License.Status.ACTIVE
        )
        self._authenticate_buyer()
        response = self.client_http.get(f'/api/licenses/{license.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buyer_cannot_retrieve_other_buyers_license(self):
        other_buyer = User.objects.create_user(
            username='other', password='testpass', role='client'
        )
        # Signal creates the profile automatically
        other_profile = other_buyer.client_profile
        license = License.objects.create(
            client=other_profile,
            song=self.song,
            license_type=License.LicenseType.PRECLEAR,
            price_paid='299.00',
            usage_details='Campaign.',
            valid_from=timezone.now(),
            status=License.Status.ACTIVE
        )
        self._authenticate_buyer()
        response = self.client_http.get(f'/api/licenses/{license.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_license_returns_404(self):
        self._authenticate_buyer()
        response = self.client_http.get('/api/licenses/999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_retrieve_license(self):
        license = License.objects.create(
            client=self.profile,
            song=self.song,
            license_type=License.LicenseType.PRECLEAR,
            price_paid='299.00',
            usage_details='Campaign.',
            valid_from=timezone.now(),
            status=License.Status.ACTIVE
        )
        response = self.client_http.get(f'/api/licenses/{license.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)