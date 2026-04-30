from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from .models import SubscriptionTier, BuyerSubscription
from users.models import ClientProfile

User = get_user_model()


class SubscriptionTierModelTests(TestCase):

    def test_tier_str(self):
        tier = SubscriptionTier.objects.create(
            name='Pro',
            price_annual='5000.00',
            includes_artist_promo=True
        )
        self.assertIn('Pro', str(tier))
        self.assertIn('5000', str(tier))

    def test_tier_defaults(self):
        tier = SubscriptionTier.objects.create(
            name='Basic',
            price_annual='2500.00'
        )
        self.assertTrue(tier.is_active)
        self.assertFalse(tier.includes_artist_promo)


class BuyerSubscriptionModelTests(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = ClientProfile.objects.create(user=self.buyer)
        self.tier = SubscriptionTier.objects.create(
            name='Pro',
            price_annual='5000.00',
            includes_artist_promo=True
        )

    def test_default_status_is_active(self):
        sub = BuyerSubscription.objects.create(
            profile=self.profile,
            tier=self.tier,
            stripe_customer_id='cus_mock_1',
            stripe_subscription_id='sub_mock_1',
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=365)
        )
        self.assertEqual(sub.status, BuyerSubscription.Status.ACTIVE)

    def test_subscription_str(self):
        sub = BuyerSubscription.objects.create(
            profile=self.profile,
            tier=self.tier,
            stripe_customer_id='cus_mock_1',
            stripe_subscription_id='sub_mock_1',
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=365)
        )
        self.assertIn('buyer1', str(sub))
        self.assertIn('Pro', str(sub))

    def test_multiple_subscriptions_allowed(self):
        # History — same profile can have multiple rows
        BuyerSubscription.objects.create(
            profile=self.profile,
            tier=self.tier,
            stripe_customer_id='cus_mock_1',
            stripe_subscription_id='sub_mock_1',
            status=BuyerSubscription.Status.EXPIRED,
            current_period_start=timezone.now() - timezone.timedelta(days=730),
            current_period_end=timezone.now() - timezone.timedelta(days=365)
        )
        BuyerSubscription.objects.create(
            profile=self.profile,
            tier=self.tier,
            stripe_customer_id='cus_mock_1',
            stripe_subscription_id='sub_mock_2',
            status=BuyerSubscription.Status.ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=365)
        )
        self.assertEqual(
            BuyerSubscription.objects.filter(profile=self.profile).count(), 2
        )


class SubscriptionTierListViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        SubscriptionTier.objects.create(
            name='Pro',
            price_annual='5000.00',
            includes_artist_promo=True,
            is_active=True
        )
        SubscriptionTier.objects.create(
            name='Legacy',
            price_annual='3000.00',
            includes_artist_promo=False,
            is_active=False
            # inactive — should not appear
        )

    def test_lists_only_active_tiers(self):
        response = self.client_http.get('/api/subscriptions/tiers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Pro')

    def test_no_auth_required(self):
        # Unauthenticated users can view tiers
        response = self.client_http.get('/api/subscriptions/tiers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SubscribeViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = ClientProfile.objects.create(user=self.buyer)
        self.artist = User.objects.create_user(
            username='artist1', password='testpass', role='artist'
        )
        self.tier = SubscriptionTier.objects.create(
            name='Pro',
            price_annual='5000.00',
            includes_artist_promo=True,
            is_active=True
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

    def test_buyer_can_subscribe(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/subscriptions/subscribe/', {
            'tier_id': self.tier.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BuyerSubscription.objects.count(), 1)

    def test_subscription_status_is_active(self):
        self._authenticate_buyer()
        self.client_http.post('/api/subscriptions/subscribe/', {
            'tier_id': self.tier.id
        })
        sub = BuyerSubscription.objects.first()
        self.assertEqual(sub.status, BuyerSubscription.Status.ACTIVE)

    def test_cannot_subscribe_twice(self):
        self._authenticate_buyer()
        self.client_http.post('/api/subscriptions/subscribe/', {
            'tier_id': self.tier.id
        })
        response = self.client_http.post('/api/subscriptions/subscribe/', {
            'tier_id': self.tier.id
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_subscribe(self):
        response = self.client_http.post('/api/subscriptions/subscribe/', {
            'tier_id': self.tier.id
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unsigned_contract_cannot_subscribe(self):
        unsigned_buyer = User.objects.create_user(
            username='unsigned', password='testpass', role='client'
        )
        ClientProfile.objects.create(user=unsigned_buyer)
        self.client_http.force_authenticate(user=unsigned_buyer)
        response = self.client_http.post('/api/subscriptions/subscribe/', {
            'tier_id': self.tier.id
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_artist_cannot_subscribe(self):
        self.client_http.force_authenticate(user=self.artist)
        response = self.client_http.post('/api/subscriptions/subscribe/', {
            'tier_id': self.tier.id
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_tier_cannot_be_selected(self):
        self._authenticate_buyer()
        inactive_tier = SubscriptionTier.objects.create(
            name='Legacy',
            price_annual='1000.00',
            is_active=False
        )
        response = self.client_http.post('/api/subscriptions/subscribe/', {
            'tier_id': inactive_tier.id
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MySubscriptionViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = ClientProfile.objects.create(user=self.buyer)
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

    def test_buyer_can_view_active_subscription(self):
        BuyerSubscription.objects.create(
            profile=self.profile,
            tier=self.tier,
            stripe_customer_id='cus_mock_1',
            stripe_subscription_id='sub_mock_1',
            status=BuyerSubscription.Status.ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=365)
        )
        self._authenticate_buyer()
        response = self.client_http.get('/api/subscriptions/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'active')

    def test_no_subscription_returns_404(self):
        self._authenticate_buyer()
        response = self.client_http.get('/api/subscriptions/me/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_view_subscription(self):
        response = self.client_http.get('/api/subscriptions/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CancelSubscriptionViewTests(TestCase):

    def setUp(self):
        self.client_http = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1', password='testpass', role='client'
        )
        self.profile = ClientProfile.objects.create(user=self.buyer)
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

    def test_buyer_can_cancel_subscription(self):
        BuyerSubscription.objects.create(
            profile=self.profile,
            tier=self.tier,
            stripe_customer_id='cus_mock_1',
            stripe_subscription_id='sub_mock_1',
            status=BuyerSubscription.Status.ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=365)
        )
        self._authenticate_buyer()
        response = self.client_http.post('/api/subscriptions/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sub = BuyerSubscription.objects.first()
        sub.refresh_from_db()
        self.assertEqual(sub.status, BuyerSubscription.Status.CANCELLED)

    def test_cancel_without_subscription_returns_404(self):
        self._authenticate_buyer()
        response = self.client_http.post('/api/subscriptions/cancel/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_cancel(self):
        response = self.client_http.post('/api/subscriptions/cancel/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)